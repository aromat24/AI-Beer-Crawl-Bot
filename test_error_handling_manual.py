#!/usr/bin/env python3
"""
Manual test script for error handling functionality
Run this to test the error handling system interactively
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

# Import Flask and our error handling
from flask import Flask, jsonify, request
from src.utils.error_handling import (
    CustomError, ValidationError, AuthenticationError, NotFoundError,
    configure_logging, setup_error_handlers, setup_request_logging,
    log_user_action, log_celery_task, log_whatsapp_interaction
)

def create_test_app():
    """Create a test Flask app with error handling"""
    app = Flask(__name__)
    app.config['DEBUG'] = True
    app.config['TESTING'] = True
    
    # Setup error handling
    configure_logging(app)
    setup_error_handlers(app)
    setup_request_logging(app)
    
    # Test routes that trigger different errors
    @app.route('/test/validation-error')
    def test_validation_error():
        """Test ValidationError"""
        raise ValidationError("Invalid email format", {"field": "email", "value": "invalid-email"})
    
    @app.route('/test/auth-error')
    def test_auth_error():
        """Test AuthenticationError"""
        raise AuthenticationError("JWT token expired")
    
    @app.route('/test/not-found-error')
    def test_not_found_error():
        """Test NotFoundError"""
        raise NotFoundError("User with ID 123 not found")
    
    @app.route('/test/custom-error')
    def test_custom_error():
        """Test custom error with payload"""
        raise CustomError("Something went wrong", 422, {
            "error_code": "CUSTOM_ERROR",
            "details": "This is a custom error with additional context"
        })
    
    @app.route('/test/500-error')
    def test_500_error():
        """Test unhandled exception"""
        # This will trigger the 500 error handler
        result = 1 / 0  # ZeroDivisionError
        return jsonify({"result": result})
    
    @app.route('/test/success')
    def test_success():
        """Test successful request"""
        return jsonify({
            "message": "Success! Error handling is working.",
            "status": "ok"
        })
    
    @app.route('/test/logging')
    def test_logging():
        """Test utility logging functions"""
        # Test user action logging
        log_user_action("user123", "test_action", {"test": True})
        
        # Test celery task logging
        log_celery_task("test_task", "task_123", "success", {"result": "completed"})
        
        # Test WhatsApp interaction logging
        log_whatsapp_interaction("+1234567890", "text", "sent", {"message": "Hello World"})
        
        return jsonify({
            "message": "Logging functions tested - check console output",
            "logged_events": ["user_action", "celery_task", "whatsapp_interaction"]
        })
    
    return app

def run_manual_tests():
    """Run manual tests"""
    print("🧪 Starting Error Handling Tests")
    print("=" * 50)
    
    app = create_test_app()
    
    print("\n✅ Test app created with error handling configured")
    print("\nAvailable test endpoints:")
    print("- http://localhost:5001/test/validation-error")
    print("- http://localhost:5001/test/auth-error") 
    print("- http://localhost:5001/test/not-found-error")
    print("- http://localhost:5001/test/custom-error")
    print("- http://localhost:5001/test/500-error")
    print("- http://localhost:5001/test/success")
    print("- http://localhost:5001/test/logging")
    
    print("\n🚀 Starting test server on http://localhost:5001")
    print("Visit the URLs above to test different error scenarios")
    print("Press Ctrl+C to stop\n")
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=True)
    except KeyboardInterrupt:
        print("\n\n✅ Test server stopped")

def run_unit_tests():
    """Run unit tests for error classes"""
    print("🧪 Running Unit Tests for Error Classes")
    print("=" * 50)
    
    # Test 1: CustomError base class
    print("\n1. Testing CustomError base class...")
    try:
        error = CustomError("Test error", 500, {"detail": "test"})
        assert error.message == "Test error"
        assert error.status_code == 500
        assert error.payload == {"detail": "test"}
        print("   ✅ CustomError: PASSED")
    except Exception as e:
        print(f"   ❌ CustomError: FAILED - {e}")
    
    # Test 2: ValidationError
    print("\n2. Testing ValidationError...")
    try:
        error = ValidationError("Invalid input", {"field": "email"})
        assert error.message == "Invalid input"
        assert error.status_code == 400
        assert error.payload == {"field": "email"}
        print("   ✅ ValidationError: PASSED")
    except Exception as e:
        print(f"   ❌ ValidationError: FAILED - {e}")
    
    # Test 3: AuthenticationError
    print("\n3. Testing AuthenticationError...")
    try:
        error = AuthenticationError()
        assert error.message == "Authentication required"
        assert error.status_code == 401
        
        error2 = AuthenticationError("Token expired")
        assert error2.message == "Token expired"
        print("   ✅ AuthenticationError: PASSED")
    except Exception as e:
        print(f"   ❌ AuthenticationError: FAILED - {e}")
    
    # Test 4: NotFoundError
    print("\n4. Testing NotFoundError...")
    try:
        error = NotFoundError("User not found")
        assert error.message == "User not found"
        assert error.status_code == 404
        print("   ✅ NotFoundError: PASSED")
    except Exception as e:
        print(f"   ❌ NotFoundError: FAILED - {e}")
    
    # Test 5: Logging functions
    print("\n5. Testing logging functions...")
    try:
        log_user_action("test_user", "test_action", {"test": True})
        log_celery_task("test_task", "task_123", "success")
        log_whatsapp_interaction("+1234567890", "text", "sent")
        print("   ✅ Logging functions: PASSED")
    except Exception as e:
        print(f"   ❌ Logging functions: FAILED - {e}")
    
    print("\n" + "=" * 50)
    print("✅ Unit tests completed!")

def main():
    """Main function"""
    print("AI Beer Crawl - Error Handling Test Suite")
    print("=" * 50)
    print("\nChoose test mode:")
    print("1. Run unit tests (quick)")
    print("2. Start interactive test server")
    print("3. Run both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        run_unit_tests()
    elif choice == "2":
        run_manual_tests()
    elif choice == "3":
        run_unit_tests()
        print("\n" + "=" * 50)
        input("Press Enter to start interactive test server...")
        run_manual_tests()
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()
