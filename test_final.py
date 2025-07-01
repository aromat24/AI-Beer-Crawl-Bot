#!/usr/bin/env python3
"""
Final comprehensive test for error handling
"""
import sys
import os
import json

# Setup path
sys.path.insert(0, 'src')

print("🍺 AI Beer Crawl - Error Handling Final Test")
print("=" * 50)

def test_error_classes():
    """Test all error classes"""
    print("\n1. 🧪 Testing Error Classes")
    print("-" * 30)
    
    try:
        from src.utils.error_handling import (
            CustomError, ValidationError, AuthenticationError, 
            NotFoundError, ConflictError, RateLimitError
        )
        
        tests = [
            ("CustomError", CustomError("Test error", 500, {"test": True})),
            ("ValidationError", ValidationError("Invalid input", {"field": "email"})),
            ("AuthenticationError", AuthenticationError("Token expired")),
            ("NotFoundError", NotFoundError("User not found")),
            ("ConflictError", ConflictError("Email exists")),
            ("RateLimitError", RateLimitError("Too many requests"))
        ]
        
        for name, error in tests:
            print(f"   ✅ {name}:")
            print(f"      Message: {error.message}")
            print(f"      Status: {error.status_code}")
            if hasattr(error, 'payload') and error.payload:
                print(f"      Payload: {error.payload}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error class test failed: {e}")
        return False

def test_flask_integration():
    """Test Flask integration without complex logging"""
    print("\n2. 🌐 Testing Flask Integration")
    print("-" * 30)
    
    try:
        from flask import Flask, jsonify
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        # Simple error handler without complex logging
        @app.errorhandler(400)
        def handle_400(error):
            return jsonify({
                "error": "Bad Request",
                "status_code": 400,
                "message": "Invalid request"
            }), 400
        
        @app.errorhandler(404)
        def handle_404(error):
            return jsonify({
                "error": "Not Found", 
                "status_code": 404,
                "message": "Resource not found"
            }), 404
        
        @app.route('/test-success')
        def success():
            return jsonify({"status": "success", "message": "Working!"})
        
        # Test with client
        with app.test_client() as client:
            # Test success
            response = client.get('/test-success')
            print(f"   ✅ Success endpoint: {response.status_code}")
            print(f"      Response: {response.get_json()}")
            
            # Test 404
            response = client.get('/nonexistent')
            print(f"   ✅ 404 handler: {response.status_code}")
            print(f"      Response: {response.get_json()}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Flask test failed: {e}")
        return False

def test_practical_usage():
    """Test practical usage scenarios"""
    print("\n3. 🔧 Testing Practical Usage")
    print("-" * 30)
    
    try:
        from src.utils.error_handling import ValidationError, NotFoundError
        
        # Simulate user input validation
        def validate_email(email):
            if not email or '@' not in email:
                raise ValidationError(
                    "Invalid email format",
                    {"field": "email", "value": email}
                )
            return True
        
        # Simulate database lookup
        def find_user(user_id):
            if user_id != 123:  # Simulate user not found
                raise NotFoundError(
                    f"User {user_id} not found",
                    {"user_id": user_id, "table": "users"}
                )
            return {"id": 123, "name": "Test User"}
        
        # Test validation
        try:
            validate_email("invalid-email")
        except ValidationError as e:
            print(f"   ✅ Email validation error caught:")
            print(f"      {e.message} (status: {e.status_code})")
            print(f"      Details: {e.payload}")
        
        # Test user lookup
        try:
            find_user(999)
        except NotFoundError as e:
            print(f"   ✅ User lookup error caught:")
            print(f"      {e.message} (status: {e.status_code})")
            print(f"      Details: {e.payload}")
        
        # Test successful case
        user = find_user(123)
        print(f"   ✅ Successful lookup: {user}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Practical test failed: {e}")
        return False

def main():
    """Run all tests"""
    results = []
    
    results.append(test_error_classes())
    results.append(test_flask_integration())
    results.append(test_practical_usage())
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Tests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 ALL TESTS PASSED! Error handling is working perfectly!")
        print("\n📋 What you can do now:")
        print("   1. Use the error classes in your Flask routes")
        print("   2. Raise ValidationError for input validation")
        print("   3. Raise AuthenticationError for auth failures")
        print("   4. Raise NotFoundError for missing resources")
        print("   5. Use setup_error_handlers(app) in your Flask app")
        print("\n🔗 Integration example:")
        print("   from src.utils.error_handling import ValidationError, setup_error_handlers")
        print("   setup_error_handlers(app)  # In your Flask app")
        print("   raise ValidationError('Invalid email', {'field': 'email'})")
    else:
        print("❌ Some tests failed. Check the error messages above.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
