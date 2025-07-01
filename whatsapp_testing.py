#!/usr/bin/env python3
"""
WhatsApp Testing Setup with ngrok
Comprehensive testing environment for WhatsApp webhook integration
"""
import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

def start_services():
    """Start Redis, Flask app, and Celery worker"""
    print("🚀 Starting services...")
    
    # Check if Redis is running
    try:
        subprocess.run(['redis-cli', 'ping'], check=True, capture_output=True)
        print("✅ Redis is already running")
    except subprocess.CalledProcessError:
        print("❌ Redis is not running. Starting Redis...")
        subprocess.Popen(['redis-server', '--daemonize', 'yes'])
        time.sleep(2)
    
    # Start Celery worker in background
    print("🔄 Starting Celery worker...")
    celery_process = subprocess.Popen([
        'celery', '-A', 'src.tasks.celery_tasks.celery', 
        'worker', '--loglevel=info', '--concurrency=2'
    ], cwd=project_root)
    
    return celery_process

def create_test_app():
    """Create Flask app with enhanced logging for WhatsApp testing"""
    from flask import Flask, request, jsonify
    from src.utils.error_handling import setup_error_handlers, configure_logging
    
    app = Flask(__name__)
    app.config['DEBUG'] = True
    
    # Setup error handling
    configure_logging(app)
    setup_error_handlers(app)
    
    # WhatsApp configuration (using test values for now)
    app.config['WHATSAPP_TOKEN'] = os.environ.get('WHATSAPP_TOKEN', 'test_token')
    app.config['WHATSAPP_PHONE_ID'] = os.environ.get('WHATSAPP_PHONE_ID', 'test_phone_id')
    app.config['WHATSAPP_VERIFY_TOKEN'] = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'test_verify_token')
    
    @app.route('/')
    def home():
        """Home page with testing information"""
        ngrok_url = get_ngrok_url()
        return f"""
        <html>
        <head><title>WhatsApp Testing Dashboard</title></head>
        <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
            <h1>🍺 WhatsApp Testing Dashboard</h1>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 10px 0;">
                <h2>📡 Webhook URLs</h2>
                <p><strong>Ngrok URL:</strong> <code>{ngrok_url}</code></p>
                <p><strong>Webhook URL:</strong> <code>{ngrok_url}/webhook/whatsapp</code></p>
                <p><strong>Health Check:</strong> <a href="/health">{ngrok_url}/health</a></p>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 10px 0;">
                <h2>🧪 Test Endpoints</h2>
                <ul>
                    <li><a href="/webhook/test">Test Webhook Processing</a></li>
                    <li><a href="/webhook/simulate">Simulate WhatsApp Message</a></li>
                    <li><a href="/api/beer-crawl/bars">List Bars</a></li>
                    <li><a href="/api/beer-crawl/groups">List Groups</a></li>
                </ul>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 10px 0;">
                <h2>📋 WhatsApp Setup Instructions</h2>
                <ol>
                    <li>Go to <a href="https://developers.facebook.com/apps" target="_blank">Facebook Developers</a></li>
                    <li>Create a WhatsApp Business app</li>
                    <li>Get your Phone Number ID and Token</li>
                    <li>Set webhook URL to: <code>{ngrok_url}/webhook/whatsapp</code></li>
                    <li>Set verify token: <code>test_verify_token</code></li>
                    <li>Subscribe to messages</li>
                </ol>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 10px 0;">
                <h2>📱 Test Messages</h2>
                <p>Send these messages to test the bot:</p>
                <ul>
                    <li><code>join</code> - Join a beer crawl</li>
                    <li><code>beer crawl</code> - Start beer crawl process</li>
                    <li><code>I want to join a beer crawl</code> - Full request</li>
                    <li><code>yes</code> - Confirm group participation</li>
                </ul>
            </div>
        </body>
        </html>
        """
    
    @app.route('/webhook/whatsapp', methods=['GET'])
    def whatsapp_webhook_verify():
        """Verify WhatsApp webhook"""
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        mode = request.args.get('hub.mode')
        
        print(f"📞 Webhook verification request:")
        print(f"   Mode: {mode}")
        print(f"   Verify Token: {verify_token}")
        print(f"   Challenge: {challenge}")
        
        if mode == 'subscribe' and verify_token == app.config['WHATSAPP_VERIFY_TOKEN']:
            print("✅ Webhook verification successful!")
            return challenge
        else:
            print("❌ Webhook verification failed!")
            return 'Invalid verification token', 403
    
    @app.route('/webhook/whatsapp', methods=['POST'])
    def whatsapp_webhook():
        """Handle incoming WhatsApp messages with enhanced logging"""
        try:
            data = request.get_json()
            
            print("📨 Received WhatsApp webhook:")
            print(json.dumps(data, indent=2))
            
            # Log headers for debugging
            print("📋 Request headers:")
            for header, value in request.headers.items():
                print(f"   {header}: {value}")
            
            # Process the message
            if 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message in change['value']['messages']:
                                    print(f"🔄 Processing message: {message}")
                                    
                                    # Import and process message
                                    from src.tasks.celery_tasks import process_whatsapp_message
                                    process_whatsapp_message.delay(message)
            
            return jsonify({'status': 'received'}), 200
        
        except Exception as e:
            print(f"❌ Webhook error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/webhook/test')
    def test_webhook():
        """Test webhook processing manually"""
        test_message = {
            "from": "+1234567890",
            "type": "text",
            "text": {"body": "join beer crawl"},
            "timestamp": str(int(time.time()))
        }
        
        print("🧪 Testing webhook with simulated message:")
        print(json.dumps(test_message, indent=2))
        
        try:
            from src.tasks.celery_tasks import process_whatsapp_message
            result = process_whatsapp_message.delay(test_message)
            
            return jsonify({
                "status": "success",
                "message": "Test message processed",
                "task_id": result.id,
                "test_data": test_message
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500
    
    @app.route('/webhook/simulate')
    def simulate_message():
        """Simulate different WhatsApp messages"""
        message_type = request.args.get('type', 'join')
        
        test_messages = {
            'join': {
                "from": "+1234567890",
                "type": "text", 
                "text": {"body": "I want to join a beer crawl"},
                "timestamp": str(int(time.time()))
            },
            'yes': {
                "from": "+1234567890",
                "type": "text",
                "text": {"body": "yes"},
                "timestamp": str(int(time.time()))
            },
            'alternative': {
                "from": "+1234567890", 
                "type": "text",
                "text": {"body": "find another group"},
                "timestamp": str(int(time.time()))
            }
        }
        
        test_message = test_messages.get(message_type, test_messages['join'])
        
        try:
            from src.tasks.celery_tasks import process_whatsapp_message
            result = process_whatsapp_message.delay(test_message)
            
            return jsonify({
                "status": "success",
                "message_type": message_type,
                "processed_message": test_message,
                "task_id": result.id
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500
    
    @app.route('/health')
    def health_check():
        """Enhanced health check"""
        try:
            # Check database
            from src.models import db
            db.session.execute(db.text('SELECT 1'))
            db_status = True
        except Exception:
            db_status = False
        
        # Check Redis/Celery
        try:
            from src.tasks.celery_tasks import celery
            celery.control.inspect().ping()
            celery_status = True
        except Exception:
            celery_status = False
        
        # Check ngrok
        ngrok_url = get_ngrok_url()
        
        return jsonify({
            "status": "healthy" if db_status and celery_status else "degraded",
            "database": "connected" if db_status else "disconnected", 
            "celery": "connected" if celery_status else "disconnected",
            "ngrok_url": ngrok_url,
            "webhook_url": f"{ngrok_url}/webhook/whatsapp",
            "timestamp": time.time()
        })
    
    @app.route('/webhook/green-api-test', methods=['POST'])
    def green_api_test_webhook():
        """Test endpoint for Green API webhooks"""
        data = request.get_json()
        
        app.logger.info("Green API webhook received", extra={
            'webhook_data': data,
            'headers': dict(request.headers)
        })
        
        # Process Green API webhook
        from src.integrations.green_api import process_green_api_webhook
        processed = process_green_api_webhook(data)
        
        if processed:
            app.logger.info("Green API message processed", extra={
                'processed_message': processed
            })
            
            # Trigger Celery task
            from src.tasks.celery_tasks import process_whatsapp_message
            task = process_whatsapp_message.delay(processed)
            
            return jsonify({
                'status': 'success',
                'processed_message': processed,
                'task_id': task.id
            })
        
        return jsonify({'status': 'no_message_processed'})
    
    @app.route('/test/green-api')
    def test_green_api_connection():
        """Test Green API connection and status"""
        from src.integrations.green_api import green_api_client
        
        # Test connection
        state = green_api_client.get_state_instance()
        settings = green_api_client.get_account_settings()
        
        return jsonify({
            'configured': green_api_client.configured,
            'instance_id': green_api_client.instance_id,
            'phone_number': green_api_client.phone_number,
            'base_url': green_api_client.base_url,
            'instance_state': state,
            'account_settings': settings
        })
    
    @app.route('/test/green-api/send', methods=['POST'])
    def test_green_api_send():
        """Test sending message via Green API"""
        data = request.get_json() or {}
        phone = data.get('phone', '+66955124860')  # Default to your number
        message = data.get('message', '🧪 Test message from Green API integration!')
        
        from src.integrations.green_api import green_api_client
        result = green_api_client.send_message(phone, message)
        
        return jsonify({
            'phone': phone,
            'message': message,
            'result': result
        })
    
    # Import and register existing blueprints
    try:
        from src.routes.user import user_bp
        from src.routes.beer_crawl import beer_crawl_bp
        app.register_blueprint(user_bp, url_prefix='/api/users')
        app.register_blueprint(beer_crawl_bp, url_prefix='/api/beer-crawl')
    except ImportError as e:
        print(f"Warning: Could not import blueprints: {e}")
    
    return app

def get_ngrok_url():
    """Get current ngrok URL"""
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        tunnels = response.json()['tunnels']
        for tunnel in tunnels:
            if tunnel['config']['addr'] == 'http://localhost:5000':
                return tunnel['public_url']
    except Exception:
        pass
    return "http://localhost:5000"

def start_ngrok():
    """Start ngrok tunnel"""
    print("🌐 Starting ngrok tunnel...")
    
    # Check if ngrok is already running
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
        tunnels = response.json()['tunnels']
        for tunnel in tunnels:
            if tunnel['config']['addr'] == 'http://localhost:5000':
                print(f"✅ Ngrok already running: {tunnel['public_url']}")
                return tunnel['public_url']
    except Exception:
        pass
    
    # Start ngrok
    ngrok_process = subprocess.Popen([
        'ngrok', 'http', '5000', '--log=stdout'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for ngrok to start
    time.sleep(3)
    
    # Get the public URL
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        tunnels = response.json()['tunnels']
        for tunnel in tunnels:
            if tunnel['config']['addr'] == 'http://localhost:5000':
                public_url = tunnel['public_url']
                print(f"✅ Ngrok tunnel started: {public_url}")
                return public_url
    except Exception as e:
        print(f"❌ Failed to get ngrok URL: {e}")
        return None
    
    return None

def main():
    """Main function to set up WhatsApp testing environment"""
    print("🍺 AI Beer Crawl - WhatsApp Testing Setup")
    print("=" * 50)
    
    # Start services
    celery_process = start_services()
    
    # Start ngrok
    ngrok_url = start_ngrok()
    
    if ngrok_url:
        print(f"\n✅ Setup completed!")
        print(f"🌐 Public URL: {ngrok_url}")
        print(f"📡 Webhook URL: {ngrok_url}/webhook/whatsapp")
        print(f"🔧 Dashboard: {ngrok_url}")
        print(f"📋 Health Check: {ngrok_url}/health")
        
        print(f"\n📋 WhatsApp Configuration:")
        print(f"   Webhook URL: {ngrok_url}/webhook/whatsapp")
        print(f"   Verify Token: test_verify_token")
        
        print(f"\n🧪 Test Commands:")
        print(f"   curl {ngrok_url}/health")
        print(f"   curl {ngrok_url}/webhook/test")
        print(f"   curl {ngrok_url}/webhook/simulate?type=join")
    
    # Create and run the app
    app = create_test_app()
    
    try:
        print(f"\n🚀 Starting Flask app on http://localhost:5000")
        print(f"📱 Visit {ngrok_url} for the testing dashboard")
        print(f"🔍 Press Ctrl+C to stop all services\n")
        
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping services...")
        
        # Kill Celery worker
        if celery_process:
            celery_process.terminate()
        
        # Kill ngrok
        subprocess.run(['pkill', '-f', 'ngrok'], capture_output=True)
        
        print(f"✅ All services stopped!")

if __name__ == "__main__":
    main()
