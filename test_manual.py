#!/usr/bin/env python3
"""
Manual test commands for error handling
"""
import sys
import os
import requests
import json

sys.path.insert(0, 'src')

print("🧪 Manual Error Handling Tests")
print("=" * 40)

# Test without server first
print("\n1. Testing error classes directly...")

try:
    from src.utils.error_handling import (
        CustomError, ValidationError, AuthenticationError, NotFoundError
    )
    
    # Test ValidationError
    try:
        raise ValidationError("Invalid email", {"field": "email"})
    except ValidationError as e:
        print(f"   ✅ ValidationError: {e.message} (status: {e.status_code})")
        print(f"      Payload: {e.payload}")
    
    # Test AuthenticationError
    try:
        raise AuthenticationError("Token expired")
    except AuthenticationError as e:
        print(f"   ✅ AuthenticationError: {e.message} (status: {e.status_code})")
    
    # Test NotFoundError
    try:
        raise NotFoundError("User not found", {"user_id": 123})
    except NotFoundError as e:
        print(f"   ✅ NotFoundError: {e.message} (status: {e.status_code})")
        print(f"      Payload: {e.payload}")
    
    print("   ✅ All error classes working correctly!")
    
except Exception as e:
    print(f"   ❌ Error class test failed: {e}")

# Test Flask error handlers
print("\n2. Testing Flask error handlers...")

try:
    from flask import Flask
    from src.utils.error_handling import setup_error_handlers
    
    app = Flask(__name__)
    setup_error_handlers(app)
    
    @app.route('/test-validation')
    def test_validation():
        raise ValidationError("Test validation error", {"test": True})
    
    @app.route('/test-auth')
    def test_auth():
        raise AuthenticationError("Test auth error")
    
    with app.test_client() as client:
        # Test validation error handler
        response = client.get('/test-validation')
        data = response.get_json()
        
        print(f"   ✅ ValidationError handler:")
        print(f"      Status: {response.status_code}")
        print(f"      Response: {json.dumps(data, indent=6)}")
        
        # Test auth error handler
        response = client.get('/test-auth')
        data = response.get_json()
        
        print(f"   ✅ AuthenticationError handler:")
        print(f"      Status: {response.status_code}")
        print(f"      Response: {json.dumps(data, indent=6)}")
        
        # Test 404 handler
        response = client.get('/nonexistent-route')
        data = response.get_json()
        
        print(f"   ✅ 404 Error handler:")
        print(f"      Status: {response.status_code}")
        print(f"      Response: {json.dumps(data, indent=6)}")
    
    print("   ✅ Flask error handlers working correctly!")
    
except Exception as e:
    print(f"   ❌ Flask test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 40)
print("🎉 Manual error handling tests completed!")
print("\nTo test with a real server:")
print("1. Run: python test_error_server.py")
print("2. Visit: http://localhost:5001")
print("3. Test API endpoints with curl or browser")
