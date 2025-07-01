"""
Comprehensive tests for error handling and logging functionality
"""
import pytest
import json
import logging
from unittest.mock import patch, MagicMock
from flask import Flask, g
from datetime import datetime

# Import our error handling modules
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils.error_handling import (
    CustomError, ValidationError, AuthenticationError, AuthorizationError,
    NotFoundError, ConflictError, RateLimitError, ServiceUnavailableError,
    configure_logging, setup_error_handlers, setup_request_logging,
    log_user_action, log_celery_task, log_whatsapp_interaction
)

class TestCustomExceptions:
    """Test custom exception classes"""
    
    def test_custom_error_base_class(self):
        """Test CustomError base class"""
        error = CustomError("Test error", 500, {"detail": "test"})
        assert error.message == "Test error"
        assert error.status_code == 500
        assert error.payload == {"detail": "test"}
    
    def test_validation_error(self):
        """Test ValidationError with 400 status code"""
        error = ValidationError("Invalid input", {"field": "email"})
        assert error.message == "Invalid input"
        assert error.status_code == 400
        assert error.payload == {"field": "email"}
    
    def test_authentication_error(self):
        """Test AuthenticationError with default message"""
        error = AuthenticationError()
        assert error.message == "Authentication required"
        assert error.status_code == 401
        
        # Test with custom message
        error = AuthenticationError("Token expired")
        assert error.message == "Token expired"
    
    def test_authorization_error(self):
        """Test AuthorizationError"""
        error = AuthorizationError("Insufficient permissions")
        assert error.message == "Insufficient permissions"
        assert error.status_code == 403
    
    def test_not_found_error(self):
        """Test NotFoundError"""
        error = NotFoundError("User not found")
        assert error.message == "User not found"
        assert error.status_code == 404
    
    def test_conflict_error(self):
        """Test ConflictError"""
        error = ConflictError("Email already exists")
        assert error.message == "Email already exists"
        assert error.status_code == 409
    
    def test_rate_limit_error(self):
        """Test RateLimitError"""
        error = RateLimitError()
        assert error.message == "Rate limit exceeded"
        assert error.status_code == 429
    
    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError"""
        error = ServiceUnavailableError("Database maintenance")
        assert error.message == "Database maintenance"
        assert error.status_code == 503

class TestFlaskErrorHandlers:
    """Test Flask error handlers integration"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app with error handlers"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        # Setup error handlers
        setup_error_handlers(app)
        
        # Add test routes that trigger errors
        @app.route('/test-validation-error')
        def test_validation_error():
            raise ValidationError("Invalid email format", {"field": "email"})
        
        @app.route('/test-auth-error')
        def test_auth_error():
            raise AuthenticationError("Token expired")
        
        @app.route('/test-not-found-error')
        def test_not_found_error():
            raise NotFoundError("User not found")
        
        @app.route('/test-500-error')
        def test_500_error():
            raise Exception("Unexpected error")
        
        return app
    
    def test_validation_error_handler(self, app):
        """Test ValidationError handler returns proper JSON response"""
        with app.test_client() as client:
            response = client.get('/test-validation-error')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['error'] == "Invalid email format"
            assert data['status_code'] == 400
            assert 'timestamp' in data
            assert data['details'] == {"field": "email"}
    
    def test_authentication_error_handler(self, app):
        """Test AuthenticationError handler"""
        with app.test_client() as client:
            response = client.get('/test-auth-error')
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data['error'] == "Token expired"
            assert data['status_code'] == 401
    
    def test_not_found_error_handler(self, app):
        """Test NotFoundError handler"""
        with app.test_client() as client:
            response = client.get('/test-not-found-error')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['error'] == "User not found"
            assert data['status_code'] == 404
    
    def test_500_error_handler(self, app):
        """Test internal server error handler"""
        with app.test_client() as client:
            response = client.get('/test-500-error')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] == "Internal server error"
            assert data['status_code'] == 500
            assert 'error_id' in data
    
    def test_404_route_not_found(self, app):
        """Test 404 handler for non-existent routes"""
        with app.test_client() as client:
            response = client.get('/non-existent-route')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['error'] == "Not found"
            assert data['message'] == "The requested resource was not found"

class TestLoggingConfiguration:
    """Test logging configuration"""
    
    def test_configure_logging_development(self):
        """Test logging configuration for development"""
        app = Flask(__name__)
        app.config['DEBUG'] = True
        
        configure_logging(app)
        
        assert app.logger.level == logging.DEBUG
    
    def test_configure_logging_production(self):
        """Test logging configuration for production"""
        app = Flask(__name__)
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        
        configure_logging(app)
        
        assert app.logger.level == logging.INFO
    
    def test_configure_logging_testing(self):
        """Test logging configuration for testing"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        configure_logging(app)
        
        assert app.logger.level == logging.WARNING

class TestRequestLogging:
    """Test request logging functionality"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app with request logging"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        setup_request_logging(app)
        
        @app.route('/test-endpoint')
        def test_endpoint():
            return {"message": "success"}, 200
        
        return app
    
    def test_request_logging_middleware(self, app):
        """Test that requests are logged properly"""
        with app.test_client() as client:
            with app.app_context():
                # Capture logs
                with patch.object(app.logger, 'info') as mock_info:
                    response = client.get('/test-endpoint')
                    
                    assert response.status_code == 200
                    
                    # Check that logging was called
                    assert mock_info.call_count >= 2  # Before and after request
                    
                    # Check log content
                    call_args = [call[1] for call in mock_info.call_args_list]
                    assert any('Request received' in str(args) for args in call_args)
                    assert any('Request processed' in str(args) for args in call_args)

class TestUtilityLoggingFunctions:
    """Test utility logging functions"""
    
    @patch('src.utils.error_handling.structlog.get_logger')
    def test_log_user_action(self, mock_get_logger):
        """Test log_user_action function"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        log_user_action("user123", "login", {"ip": "192.168.1.1"})
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == 'User action'
        assert call_args[1]['user_id'] == "user123"
        assert call_args[1]['action'] == "login"
        assert call_args[1]['details'] == {"ip": "192.168.1.1"}
    
    @patch('src.utils.error_handling.structlog.get_logger')
    def test_log_celery_task(self, mock_get_logger):
        """Test log_celery_task function"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        log_celery_task("send_email", "task123", "success", {"email": "test@example.com"})
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == 'Celery task'
        assert call_args[1]['task_name'] == "send_email"
        assert call_args[1]['task_id'] == "task123"
        assert call_args[1]['status'] == "success"
    
    @patch('src.utils.error_handling.structlog.get_logger')
    def test_log_whatsapp_interaction(self, mock_get_logger):
        """Test log_whatsapp_interaction function"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        log_whatsapp_interaction("+1234567890", "text", "sent", {"message": "Hello"})
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == 'WhatsApp interaction'
        assert call_args[1]['phone_number'] == "+1234567890"
        assert call_args[1]['message_type'] == "text"
        assert call_args[1]['status'] == "sent"

if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])
