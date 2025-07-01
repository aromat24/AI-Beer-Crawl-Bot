import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.beer_crawl import beer_crawl_bp
from src.models.beer_crawl import UserPreferences, Bar, CrawlGroup, GroupMember, CrawlSession

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app)

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(beer_crawl_bp, url_prefix='/api/beer-crawl')

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()
    
    # Add sample bars if none exist
    if Bar.query.count() == 0:
        sample_bars = [
            Bar(name="The Crown Pub", address="123 High St, Manchester", area="northern quarter", 
                latitude=53.4839, longitude=-2.2374, owner_contact="crown@example.com"),
            Bar(name="Craft Beer Co", address="456 Market St, Manchester", area="northern quarter", 
                latitude=53.4848, longitude=-2.2426, owner_contact="craft@example.com"),
            Bar(name="The Local Tavern", address="789 King St, Manchester", area="city centre", 
                latitude=53.4794, longitude=-2.2453, owner_contact="local@example.com"),
            Bar(name="Brewery Tap", address="321 Oxford Rd, Manchester", area="city centre", 
                latitude=53.4722, longitude=-2.2324, owner_contact="brewery@example.com"),
            Bar(name="Sports Bar & Grill", address="654 Deansgate, Manchester", area="deansgate", 
                latitude=53.4755, longitude=-2.2507, owner_contact="sports@example.com")
        ]
        
        for bar in sample_bars:
            db.session.add(bar)
        
        db.session.commit()
        print("Sample bars added to database")

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
