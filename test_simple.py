#!/usr/bin/env python3
"""
Ultra-simple test for error handling
"""
import sys
import os

# Add paths
sys.path.insert(0, 'src')
sys.path.insert(0, '.')

print("🧪 AI Beer Crawl - Error Handling Test")
print("=" * 40)

# Test 1: Import test
print("\n1. Testing imports...")
try:
    from src.utils.error_handling import CustomError, ValidationError
    print("   ✅ Import successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Test 2: Create error objects
print("\n2. Testing error creation...")
try:
    error1 = CustomError("Test error", 500)
    print(f"   ✅ CustomError created: '{error1.message}' (status: {error1.status_code})")
    
    error2 = ValidationError("Invalid data", {"field": "email"})
    print(f"   ✅ ValidationError created: '{error2.message}' (status: {error2.status_code})")
    
except Exception as e:
    print(f"   ❌ Error creation failed: {e}")
    exit(1)

# Test 3: Test Flask integration (simple)
print("\n3. Testing Flask integration...")
try:
    from flask import Flask
    from src.utils.error_handling import setup_error_handlers
    
    app = Flask(__name__)
    setup_error_handlers(app)
    print("   ✅ Flask error handlers set up successfully")
    
except Exception as e:
    print(f"   ❌ Flask integration failed: {e}")

# Test 4: Test logging functions
print("\n4. Testing logging functions...")
try:
    from src.utils.error_handling import log_user_action
    
    print("   Testing log_user_action...")
    log_user_action("test_user", "test_action", {"test": True})
    print("   ✅ Logging function executed (check above for JSON output)")
    
except Exception as e:
    print(f"   ❌ Logging test failed: {e}")

print("\n" + "=" * 40)
print("🎉 Basic error handling test completed!")
print("\nTo test more thoroughly:")
print("1. Run Flask test server: python test_error_handling_manual.py")
print("2. Test API endpoints with curl")
print("3. Check logs for structured output")
