#!/usr/bin/env python3
"""Test the group size configuration"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🔧 Testing Group Size Configuration")
print("=" * 40)

MIN_GROUP_SIZE = int(os.environ.get('MIN_GROUP_SIZE', 3))
MAX_GROUP_SIZE = int(os.environ.get('MAX_GROUP_SIZE', 5))

print(f"MIN_GROUP_SIZE: {MIN_GROUP_SIZE}")
print(f"MAX_GROUP_SIZE: {MAX_GROUP_SIZE}")

if MIN_GROUP_SIZE == 2:
    print("✅ Configuration updated successfully!")
    print("   Groups will now form with just 2 people for testing.")
else:
    print("❌ Configuration not applied correctly.")
    print("   Make sure MIN_GROUP_SIZE=2 is in your .env file.")

print("\n🧪 Testing Import...")
try:
    # Test if the routes can import the config
    import sys
    sys.path.insert(0, 'src')
    from routes.beer_crawl import MIN_GROUP_SIZE as ROUTE_MIN_SIZE
    print(f"Routes MIN_GROUP_SIZE: {ROUTE_MIN_SIZE}")
    
    if ROUTE_MIN_SIZE == 2:
        print("✅ Routes configuration is correct!")
    else:
        print("❌ Routes configuration not updated.")
        
except Exception as e:
    print(f"❌ Error importing routes config: {e}")

print("\n🎯 Test Result:")
if MIN_GROUP_SIZE == 2:
    print("✅ Bot is now configured for testing with 2-person groups!")
else:
    print("❌ Configuration needs to be fixed.")
