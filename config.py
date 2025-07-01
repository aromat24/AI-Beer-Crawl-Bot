import os
from datetime import timedelta

class Config:
    """Base configuration."""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database/app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0,
    }
    
    # Celery Configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
    CELERY_BEAT_SCHEDULE = {
        'daily-cleanup': {
            'task': 'src.tasks.celery_tasks.daily_cleanup',
            'schedule': '0 6 * * *',  # Daily at 6 AM
        },
    }
    
    # WhatsApp Configuration
    WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN')
    WHATSAPP_PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID')
    WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN')
    WHATSAPP_API_VERSION = os.environ.get('WHATSAPP_API_VERSION', 'v17.0')
    
    # API Configuration
    API_BASE_URL = os.environ.get('API_BASE_URL') or 'http://localhost:5000'
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Session Configuration
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/1'
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
    # Application Settings
    MAX_GROUP_SIZE = int(os.environ.get('MAX_GROUP_SIZE', 5))
    MIN_GROUP_SIZE = int(os.environ.get('MIN_GROUP_SIZE', 3))
    BAR_PROGRESSION_INTERVAL = int(os.environ.get('BAR_PROGRESSION_INTERVAL', 3600))  # 1 hour
    GROUP_CLEANUP_TIME = int(os.environ.get('GROUP_CLEANUP_TIME', 6))  # 6 AM

class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'
    
    # Less strict security in development
    SESSION_COOKIE_SECURE = False
    
    # Shorter intervals for testing
    BAR_PROGRESSION_INTERVAL = int(os.environ.get('BAR_PROGRESSION_INTERVAL', 300))  # 5 minutes

class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    DEBUG = True
    
    # Use in-memory database for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Use different Redis database for tests
    CELERY_BROKER_URL = 'redis://localhost:6379/15'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/15'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Faster task execution for tests
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    
    # Very short intervals for testing
    BAR_PROGRESSION_INTERVAL = 60  # 1 minute

class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Database connection pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_timeout': 30,
        'max_overflow': 10,
        'pool_size': 20,
    }
    
    # Enhanced logging
    LOG_LEVEL = 'WARNING'
    
    # Production intervals
    BAR_PROGRESSION_INTERVAL = int(os.environ.get('BAR_PROGRESSION_INTERVAL', 3600))  # 1 hour

class StagingConfig(ProductionConfig):
    """Staging configuration."""
    
    DEBUG = True
    LOG_LEVEL = 'INFO'
    
    # Staging-specific settings
    SQLALCHEMY_ECHO = True  # Log SQL queries in staging

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration class based on environment."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])
