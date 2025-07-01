import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.models import db
from src.models.user import User
from src.models.beer_crawl import UserPreferences, Bar, CrawlGroup, GroupMember, CrawlSession, GroupStatus
from src.routes.user import user_bp
from src.routes.beer_crawl import beer_crawl_bp

# Import Celery tasks at top level
from src.tasks.celery_tasks import process_whatsapp_message, celery as celery_app
from src.integrations.green_api import process_green_api_webhook

def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration
    if config_name == 'testing':
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    else:
        database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'app.db')
        # Ensure database directory exists
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
            'DATABASE_URL', 
            f"sqlite:///{database_path}"
        )
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Celery configuration
    app.config['CELERY_BROKER_URL'] = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    app.config['CELERY_RESULT_BACKEND'] = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # Configure Celery with Flask app context
    celery_app.conf.update(app.config)
    
    class ContextTask(celery_app.Task):
        """Make celery tasks work with Flask app context"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery_app.Task = ContextTask
    
    # WhatsApp configuration
    app.config['WHATSAPP_TOKEN'] = os.environ.get('WHATSAPP_TOKEN')
    app.config['WHATSAPP_PHONE_ID'] = os.environ.get('WHATSAPP_PHONE_ID')
    app.config['WHATSAPP_VERIFY_TOKEN'] = os.environ.get('WHATSAPP_VERIFY_TOKEN')
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Enable CORS
    CORS(app, origins=os.environ.get('CORS_ORIGINS', '*').split(','))
    
    # Register blueprints
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(beer_crawl_bp, url_prefix='/api/beer-crawl')
    
    # WhatsApp webhook endpoints
    @app.route('/webhook/whatsapp', methods=['POST'])
    def whatsapp_webhook():
        """Handle incoming WhatsApp messages from Green API or Facebook"""
        try:
            data = request.get_json()
            print(f"📥 Webhook received data: {data}")
            
            # Check if this is a Green API webhook
            if 'typeWebhook' in data:
                # Green API webhook format
                processed_message = process_green_api_webhook(data)
                if processed_message:
                    print(f"✅ Queuing Celery task for message: {processed_message}")
                    task = process_whatsapp_message.delay(processed_message)
                    print(f"📋 Task queued with ID: {task.id}")
                return jsonify({'status': 'received'}), 200
            
            # Facebook WhatsApp Business API webhook format
            elif 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message in change['value']['messages']:
                                    # Process message asynchronously
                                    task = process_whatsapp_message.delay(message)
                                    print(f"📋 Task queued with ID: {task.id}")
            
            return jsonify({'status': 'received'}), 200
        
        except Exception as e:
            print(f"Webhook error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/webhook/whatsapp', methods=['GET'])
    def whatsapp_webhook_verify():
        """Verify WhatsApp webhook"""
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if verify_token == app.config['WHATSAPP_VERIFY_TOKEN']:
            return challenge or '', 200
        return 'Invalid verification token', 403
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring"""
        try:
            # Check database connection
            db.session.execute(db.text('SELECT 1'))
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    # Static file serving
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "index.html not found", 404
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

def init_database(app):
    """Initialize database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Add sample bars if none exist
        if Bar.query.count() == 0:
            sample_bars = [
                Bar(
                    name="The Crown Pub", 
                    address="123 High St, Manchester", 
                    area="northern quarter",
                    latitude=53.4839, 
                    longitude=-2.2374, 
                    owner_contact="crown@example.com",
                    capacity=60
                ),
                Bar(
                    name="Craft Beer Co", 
                    address="456 Market St, Manchester", 
                    area="northern quarter",
                    latitude=53.4848, 
                    longitude=-2.2426, 
                    owner_contact="craft@example.com",
                    capacity=40
                ),
                Bar(
                    name="The Local Tavern", 
                    address="789 King St, Manchester", 
                    area="city centre",
                    latitude=53.4794, 
                    longitude=-2.2453, 
                    owner_contact="local@example.com",
                    capacity=80
                ),
                Bar(
                    name="Brewery Tap", 
                    address="321 Oxford Rd, Manchester", 
                    area="city centre",
                    latitude=53.4722, 
                    longitude=-2.2324, 
                    owner_contact="brewery@example.com",
                    capacity=50
                ),
                Bar(
                    name="Sports Bar & Grill", 
                    address="654 Deansgate, Manchester", 
                    area="deansgate",
                    latitude=53.4755, 
                    longitude=-2.2507, 
                    owner_contact="sports@example.com",
                    capacity=100
                ),
                Bar(
                    name="The Manchester Arms", 
                    address="111 Portland St, Manchester", 
                    area="city centre",
                    latitude=53.4808, 
                    longitude=-2.2426, 
                    owner_contact="arms@example.com",
                    capacity=45
                ),
                Bar(
                    name="Ancoats Ale House", 
                    address="22 Pollard St, Manchester", 
                    area="ancoats",
                    latitude=53.4856, 
                    longitude=-2.2364, 
                    owner_contact="ancoats@example.com",
                    capacity=35
                ),
                Bar(
                    name="Spinningfields Lounge", 
                    address="1 Spinningfields, Manchester", 
                    area="spinningfields",
                    latitude=53.4781, 
                    longitude=-2.2489, 
                    owner_contact="spinning@example.com",
                    capacity=70
                )
            ]
            
            for bar in sample_bars:
                db.session.add(bar)
            
            db.session.commit()
            print(f"Added {len(sample_bars)} sample bars to database")

# Create the app instance
app = create_app()

if __name__ == '__main__':
    # Initialize database
    init_database(app)
    
    print("AI Beer Crawl App - Flask Application with Celery Integration")
    print("=" * 60)
    print("Main application starting on http://0.0.0.0:5000")
    print("Health check available at: http://0.0.0.0:5000/health")
    print("API documentation available at: http://0.0.0.0:5000/api")
    print("")
    print("To start Celery worker (in another terminal):")
    print("celery -A src.tasks.celery_tasks.celery worker --loglevel=info")
    print("")
    print("To start Celery beat scheduler (in another terminal):")
    print("celery -A src.tasks.celery_tasks.celery beat --loglevel=info")
    print("")
    print("To run database migrations:")
    print("flask db init")
    print("flask db migrate -m 'Initial migration'") 
    print("flask db upgrade")
    print("=" * 60)
    
    # Run the application
    app.run(
        host='0.0.0.0', 
        port=int(os.environ.get('PORT', 5000)), 
        debug=os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    )
