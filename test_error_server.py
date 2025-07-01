#!/usr/bin/env python3
"""
Flask test server to demonstrate error handling
"""
import sys
import os
sys.path.insert(0, 'src')

from flask import Flask, jsonify, request
from src.utils.error_handling import (
    CustomError, ValidationError, AuthenticationError, NotFoundError,
    setup_error_handlers, configure_logging
)

def create_test_app():
    """Create test Flask app"""
    app = Flask(__name__)
    app.config['DEBUG'] = True
    
    # Setup error handling
    configure_logging(app)
    setup_error_handlers(app)
    
    @app.route('/')
    def home():
        """Home page with test links"""
        return """
        <html>
        <head><title>Error Handling Test</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>🧪 Error Handling Test Server</h1>
            <h2>Test different error scenarios:</h2>
            <ul>
                <li><a href="/test/success">✅ Success Response</a></li>
                <li><a href="/test/validation-error">❌ Validation Error (400)</a></li>
                <li><a href="/test/auth-error">🔒 Authentication Error (401)</a></li>
                <li><a href="/test/not-found-error">🔍 Not Found Error (404)</a></li>
                <li><a href="/test/server-error">💥 Server Error (500)</a></li>
                <li><a href="/nonexistent">🚫 Real 404 (route doesn't exist)</a></li>
            </ul>
            <h2>API Testing:</h2>
            <p>Use curl to test:</p>
            <pre>
curl http://localhost:5001/test/validation-error
curl http://localhost:5001/test/auth-error
curl http://localhost:5001/test/not-found-error
curl http://localhost:5001/test/server-error
            </pre>
        </body>
        </html>
        """
    
    @app.route('/test/success')
    def test_success():
        """Successful response"""
        return jsonify({
            "status": "success",
            "message": "Everything is working correctly!",
            "data": {
                "timestamp": "2024-01-01T00:00:00Z",
                "server": "error-handling-test"
            }
        })
    
    @app.route('/test/validation-error')
    def test_validation_error():
        """Test ValidationError"""
        raise ValidationError(
            "Invalid email format", 
            {
                "field": "email",
                "value": "invalid-email",
                "expected_format": "user@domain.com"
            }
        )
    
    @app.route('/test/auth-error')
    def test_auth_error():
        """Test AuthenticationError"""
        raise AuthenticationError("JWT token has expired")
    
    @app.route('/test/not-found-error')
    def test_not_found_error():
        """Test NotFoundError"""
        raise NotFoundError(
            "User with ID 12345 not found",
            {"user_id": 12345, "searched_in": ["database", "cache"]}
        )
    
    @app.route('/test/server-error')
    def test_server_error():
        """Test unhandled exception (500 error)"""
        # This will cause a ZeroDivisionError
        result = 1 / 0
        return jsonify({"result": result})
    
    @app.route('/test/custom-error')
    def test_custom_error():
        """Test custom error with specific status code"""
        raise CustomError(
            "Business rule violation", 
            422,
            {
                "error_code": "BUSINESS_RULE_ERROR",
                "rule": "Cannot delete user with active orders",
                "user_id": 123,
                "active_orders": 5
            }
        )
    
    return app

if __name__ == '__main__':
    print("🚀 Starting Error Handling Test Server")
    print("=" * 50)
    
    app = create_test_app()
    
    print("✅ Error handlers configured")
    print("✅ Test routes created")
    print("\n🌐 Server starting at: http://localhost:5001")
    print("📖 Visit the home page for test links")
    print("🔧 Use Ctrl+C to stop the server\n")
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Error handling tests completed!")
