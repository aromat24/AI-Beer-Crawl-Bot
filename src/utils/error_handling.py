"""
Centralized error handling and logging for AI Beer Crawl App
"""
import logging
import sys
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, g
from functools import wraps
import structlog

# Configure structured logging
try:
    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer(),
            structlog.processors.TimeStamper(fmt="ISO"),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
except Exception:
    # Fallback if structlog configuration fails
    pass

class CustomError(Exception):
    """Base custom exception class"""
    def __init__(self, message, status_code=500, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

class ValidationError(CustomError):
    """Validation error exception"""
    def __init__(self, message, payload=None):
        super().__init__(message, 400, payload)

class AuthenticationError(CustomError):
    """Authentication error exception"""
    def __init__(self, message="Authentication required", payload=None):
        super().__init__(message, 401, payload)

class AuthorizationError(CustomError):
    """Authorization error exception"""
    def __init__(self, message="Access denied", payload=None):
        super().__init__(message, 403, payload)

class NotFoundError(CustomError):
    """Not found error exception"""
    def __init__(self, message="Resource not found", payload=None):
        super().__init__(message, 404, payload)

class ConflictError(CustomError):
    """Conflict error exception"""
    def __init__(self, message="Resource conflict", payload=None):
        super().__init__(message, 409, payload)

class RateLimitError(CustomError):
    """Rate limit error exception"""
    def __init__(self, message="Rate limit exceeded", payload=None):
        super().__init__(message, 429, payload)

class ServiceUnavailableError(CustomError):
    """Service unavailable error exception"""
    def __init__(self, message="Service temporarily unavailable", payload=None):
        super().__init__(message, 503, payload)

def configure_logging(app: Flask):
    """Configure application logging"""
    
    # Set logging level based on environment
    if app.config.get('DEBUG'):
        log_level = logging.DEBUG
    elif app.config.get('TESTING'):
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/app.log') if not app.config.get('TESTING') else logging.NullHandler()
        ]
    )
    
    # Configure specific loggers
    loggers = [
        'sqlalchemy.engine',
        'celery',
        'requests.packages.urllib3',
        'urllib3.connectionpool'
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
    
    # Create application logger
    app.logger.setLevel(log_level)
    app.logger.info('Logging configured', extra={
        'level': log_level,
        'environment': app.config.get('FLASK_ENV', 'development')
    })

def setup_error_handlers(app: Flask):
    """Setup global error handlers"""
    
    @app.errorhandler(CustomError)
    def handle_custom_error(error):
        """Handle custom application errors"""
        response = {
            'error': error.message,
            'status_code': error.status_code,
            'timestamp': datetime.utcnow().isoformat()
        }
        if error.payload:
            response['details'] = error.payload
        
        app.logger.error(
            'Custom error occurred',
            extra={
                'error_type': type(error).__name__,
                'error_message': error.message,
                'status_code': error.status_code,
                'payload': error.payload,
                'request_id': getattr(g, 'request_id', None)
            }
        )
        
        return jsonify(response), error.status_code
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle bad request errors"""
        app.logger.warning(
            'Bad request',
            extra={
                'error': str(error),
                'request_id': getattr(g, 'request_id', None)
            }
        )
        return jsonify({
            'error': 'Bad request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request format',
            'status_code': 400,
            'timestamp': datetime.utcnow().isoformat()
        }), 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle not found errors"""
        app.logger.info(
            'Resource not found',
            extra={
                'path': request.path,
                'method': request.method,
                'request_id': getattr(g, 'request_id', None)
            }
        )
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found',
            'status_code': 404,
            'timestamp': datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle method not allowed errors"""
        app.logger.warning(
            'Method not allowed',
            extra={
                'path': request.path,
                'method': request.method,
                'allowed_methods': error.description if hasattr(error, 'description') else None,
                'request_id': getattr(g, 'request_id', None)
            }
        )
        return jsonify({
            'error': 'Method not allowed',
            'message': f'Method {request.method} not allowed for this endpoint',
            'status_code': 405,
            'timestamp': datetime.utcnow().isoformat()
        }), 405
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle internal server errors"""
        error_id = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        
        app.logger.error(
            'Internal server error',
            extra={
                'error_id': error_id,
                'error': str(error),
                'traceback': traceback.format_exc(),
                'request_id': getattr(g, 'request_id', None)
            }
        )
        
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'error_id': error_id,
            'status_code': 500,
            'timestamp': datetime.utcnow().isoformat()
        }), 500

def log_request_response(f):
    """Decorator to log request and response details"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Generate request ID
        request_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        g.request_id = request_id
        
        # Log request
        current_app = f.__globals__.get('current_app')
        if current_app:
            current_app.logger.info(
                'Request started',
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent'),
                    'content_type': request.content_type
                }
            )
        
        try:
            # Execute the function
            start_time = datetime.utcnow()
            response = f(*args, **kwargs)
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Log response
            if current_app:
                status_code = response.status_code if hasattr(response, 'status_code') else 200
                current_app.logger.info(
                    'Request completed',
                    extra={
                        'request_id': request_id,
                        'status_code': status_code,
                        'duration_seconds': duration,
                        'response_size': len(response.data) if hasattr(response, 'data') else 0
                    }
                )
            
            return response
            
        except Exception as e:
            # Log error
            if current_app:
                current_app.logger.error(
                    'Request failed',
                    extra={
                        'request_id': request_id,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'traceback': traceback.format_exc()
                    }
                )
            raise
    
    return decorated_function

def setup_request_logging(app: Flask):
    """Setup request/response logging middleware"""
    
    @app.before_request
    def log_request_info():
        """Log incoming request information"""
        request_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        g.request_id = request_id
        g.start_time = datetime.utcnow()
        
        app.logger.info(
            'Request received',
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'args': dict(request.args),
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }
        )
    
    @app.after_request
    def log_response_info(response):
        """Log response information"""
        if hasattr(g, 'start_time'):
            duration = (datetime.utcnow() - g.start_time).total_seconds()
            
            app.logger.info(
                'Request processed',
                extra={
                    'request_id': getattr(g, 'request_id', None),
                    'status_code': response.status_code,
                    'duration_seconds': duration,
                    'content_length': response.content_length
                }
            )
        
        return response

# Utility functions for consistent logging
def log_user_action(user_id, action, details=None):
    """Log user actions for audit trail"""
    logger = structlog.get_logger()
    logger.info(
        'User action',
        user_id=user_id,
        action=action,
        details=details,
        timestamp=datetime.utcnow().isoformat()
    )

def log_celery_task(task_name, task_id, status, details=None):
    """Log Celery task execution"""
    logger = structlog.get_logger()
    logger.info(
        'Celery task',
        task_name=task_name,
        task_id=task_id,
        status=status,
        details=details,
        timestamp=datetime.utcnow().isoformat()
    )

def log_whatsapp_interaction(phone_number, message_type, status, details=None):
    """Log WhatsApp interactions"""
    logger = structlog.get_logger()
    logger.info(
        'WhatsApp interaction',
        phone_number=phone_number,
        message_type=message_type,
        status=status,
        details=details,
        timestamp=datetime.utcnow().isoformat()
    )

# Export functions and classes
__all__ = [
    'CustomError', 'ValidationError', 'AuthenticationError', 'AuthorizationError',
    'NotFoundError', 'ConflictError', 'RateLimitError', 'ServiceUnavailableError',
    'configure_logging', 'setup_error_handlers', 'setup_request_logging',
    'log_request_response', 'log_user_action', 'log_celery_task', 'log_whatsapp_interaction'
]
