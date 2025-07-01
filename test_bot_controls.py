#!/usr/bin/env python3
"""
Test script for bot behavior controls API
"""

import requests
import json
import time

BASE_URL = 'http://localhost:5002'

def test_get_settings():
    """Test getting current bot settings"""
    print("🔍 Testing GET /api/bot-settings")
    try:
        response = requests.get(f'{BASE_URL}/api/bot-settings')
        if response.status_code == 200:
            settings = response.json()
            print(f"✅ GET settings successful!")
            print(f"📊 Current settings: {json.dumps(settings, indent=2)}")
            return settings
        else:
            print(f"❌ GET failed with status {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ GET error: {e}")
        return None

def test_save_settings():
    """Test saving bot settings"""
    print("\n💾 Testing POST /api/bot-settings")
    
    test_settings = {
        "min_group_size": 2,
        "max_group_size": 6,
        "group_threshold": 3,
        "group_deletion_timer": 24,
        "session_duration": 4,
        "message_cooldown": 30,
        "user_cooldown": 10,
        "rate_limit_window": 300,
        "rate_limit_max": 5,
        "bar_progression_time": 60,
        "wait_between_bars": 15,
        "join_deadline": 30,
        "auto_start_threshold": 4,
        "auto_group_creation": True,
        "smart_matching": True,
        "auto_progression": True,
        "welcome_messages": True,
        "reminder_messages": True,
        "debug_mode": False
    }
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/bot-settings',
            json=test_settings,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ POST settings successful!")
            print(f"📝 Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ POST failed with status {response.status_code}")
            print(f"📝 Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ POST error: {e}")
        return False

def test_dashboard_access():
    """Test dashboard page access"""
    print("\n🌐 Testing dashboard page access")
    try:
        response = requests.get(f'{BASE_URL}/', timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard page accessible!")
            return True
        else:
            print(f"❌ Dashboard access failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard access error: {e}")
        return False

def main():
    print("🤖 AI Beer Crawl Bot Controls Test")
    print("=" * 40)
    
    # Test dashboard access
    dashboard_ok = test_dashboard_access()
    
    # Test getting settings
    settings = test_get_settings()
    
    # Test saving settings
    save_ok = test_save_settings()
    
    # Final verification - get settings again
    if save_ok:
        print("\n🔄 Verifying settings were saved...")
        time.sleep(1)
        new_settings = test_get_settings()
    
    print("\n📋 Test Summary:")
    print(f"  Dashboard Access: {'✅' if dashboard_ok else '❌'}")
    print(f"  GET Settings: {'✅' if settings else '❌'}")
    print(f"  POST Settings: {'✅' if save_ok else '❌'}")
    
    if dashboard_ok and settings and save_ok:
        print("\n🎉 All bot control tests PASSED!")
        print("🌐 Dashboard: http://localhost:5002")
        return True
    else:
        print("\n❌ Some tests FAILED!")
        return False

if __name__ == '__main__':
    main()
