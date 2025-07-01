#!/usr/bin/env python3
"""Test deduplication functionality"""
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project path
sys.path.insert(0, 'src')

try:
    from tasks.celery_tasks import (
        is_duplicate_message, 
        clear_user_deduplication,
        get_user_message_count,
        increment_user_message_count
    )
    
    print("🧪 Testing Deduplication Logic")
    print("=" * 50)
    
    test_user = "+66955124860"
    test_message = "join"
    test_type = "text"
    
    # Clear any existing data
    cleared = clear_user_deduplication(test_user)
    print(f"🧹 Cleared {cleared} existing keys")
    
    # Test 1: First message should be allowed
    print(f"\n📝 Test 1: First message")
    is_dup = is_duplicate_message(test_user, test_message, test_type)
    print(f"   Is duplicate: {is_dup} (should be False)")
    
    # Test 2: Immediate duplicate should be blocked
    print(f"\n📝 Test 2: Immediate duplicate")
    is_dup = is_duplicate_message(test_user, test_message, test_type)
    print(f"   Is duplicate: {is_dup} (should be True)")
    
    # Test 3: Different message should be blocked by user cooldown
    print(f"\n📝 Test 3: Different message during cooldown")
    is_dup = is_duplicate_message(test_user, "beer crawl", test_type)
    print(f"   Is duplicate: {is_dup} (should be True - user cooldown)")
    
    # Test 4: Rate limiting
    print(f"\n📝 Test 4: Rate limiting")
    for i in range(7):
        count = increment_user_message_count(test_user, 60)  # 1 minute window
        print(f"   Message {i+1}: count = {count}")
        if count > 5:
            print(f"   ⚠️ Rate limit exceeded!")
    
    print(f"\n✅ Deduplication tests completed!")
    print(f"   Message cooldown: {os.environ.get('MESSAGE_COOLDOWN', 30)}s")
    print(f"   User cooldown: {os.environ.get('USER_COOLDOWN', 10)}s") 
    print(f"   Rate limit: {os.environ.get('RATE_LIMIT_MAX', 5)} msgs/{os.environ.get('RATE_LIMIT_WINDOW', 300)}s")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure the Celery worker dependencies are installed")
except Exception as e:
    print(f"❌ Test error: {e}")
    import traceback
    traceback.print_exc()
