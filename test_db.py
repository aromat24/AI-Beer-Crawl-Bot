#!/usr/bin/env python3
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models import db
from src.models.user import User
from src.models.beer_crawl import UserPreferences, Bar, CrawlGroup, GroupMember, CrawlSession, GroupStatus

print("Testing database connection...")

# Try to import the app
try:
    from app import create_app
    print("✓ App imported successfully")
    
    app = create_app('development')
    print("✓ App created successfully")
    
    with app.app_context():
        print("✓ App context entered")
        
        # Test database connection
        try:
            db.create_all()
            print("✓ Database tables created successfully")
            
            # Test creating a sample bar
            sample_bar = Bar(
                name="Test Bar",
                address="Test Address",
                area="test area",
                latitude=53.4839,
                longitude=-2.2374
            )
            
            db.session.add(sample_bar)
            db.session.commit()
            
            print("✓ Sample bar created successfully")
            
            # Test querying
            bars = Bar.query.all()
            print(f"✓ Found {len(bars)} bars in database")
            
        except Exception as e:
            print(f"✗ Database error: {e}")
            
except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
    
print("Testing complete.")
