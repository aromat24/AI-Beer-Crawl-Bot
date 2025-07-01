"""
Production configuration management with secrets and validation
"""
import os
import secrets
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str
    pool_size: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False

@dataclass
class RedisConfig:
    """Redis configuration"""
    url: str
    socket_timeout: int = 30
    socket_connect_timeout: int = 30
    connection_pool_kwargs: Optional[Dict[str, Any]] = None

@dataclass
class CeleryConfig:
    """Celery configuration"""
    broker_url: str
    result_backend: str
    task_serializer: str = 'json'
    accept_content: list = None
    result_serializer: str = 'json'
    timezone: str = 'UTC'
    enable_utc: bool = True
    task_routes: Optional[Dict[str, str]] = None
    beat_schedule: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.accept_content is None:
            self.accept_content = ['json']

@dataclass
class WhatsAppConfig:
    """WhatsApp API configuration"""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    phone_number_id: Optional[str] = None
    business_account_id: Optional[str] = None

@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str
    jwt_secret_key: Optional[str] = None
    jwt_access_token_expires: int = 3600  # 1 hour
    password_salt_rounds: int = 12
    rate_limit_per_minute: int = 60
    max_content_length: int = 16 * 1024 * 1024  # 16MB

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    prometheus_enabled: bool = True
    metrics_endpoint: str = '/metrics'
    health_endpoint: str = '/health'
    log_level: str = 'INFO'
    structured_logging: bool = True
    sentry_dsn: Optional[str] = None

class ProductionConfig:
    """Production configuration with validation and secrets management"""
    
    def __init__(self):
        self._validate_environment()
        self._load_secrets()
        
        # Core Flask settings
        self.SECRET_KEY = self._get_secret_key()
        self.FLASK_ENV = os.getenv('FLASK_ENV', 'production')
        self.DEBUG = self._get_bool('DEBUG', False)
        self.TESTING = self._get_bool('TESTING', False)
        
        # Database configuration
        self.database = self._get_database_config()
        
        # Redis configuration
        self.redis = self._get_redis_config()
        
        # Celery configuration
        self.celery = self._get_celery_config()
        
        # WhatsApp configuration
        self.whatsapp = self._get_whatsapp_config()
        
        # Security configuration
        self.security = self._get_security_config()
        
        # Monitoring configuration
        self.monitoring = self._get_monitoring_config()
        
        # Additional Flask-SQLAlchemy settings
        self.SQLALCHEMY_DATABASE_URI = self.database.url
        self.SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': self.database.pool_size,
            'pool_timeout': self.database.pool_timeout,
            'pool_recycle': self.database.pool_recycle,
            'echo': self.database.echo
        }
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        
        # Additional Celery settings
        self.CELERY_BROKER_URL = self.celery.broker_url
        self.CELERY_RESULT_BACKEND = self.celery.result_backend
        
        # Application-specific settings
        self.MAX_CONTENT_LENGTH = self.security.max_content_length
        self.JSONIFY_PRETTYPRINT_REGULAR = not self.DEBUG
    
    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = [
            'SECRET_KEY',
            'DATABASE_URL',
            'REDIS_URL',
            'CELERY_BROKER_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def _load_secrets(self):
        """Load secrets from files or environment variables"""
        secrets_dir = Path('/run/secrets')
        
        # Load secrets from Docker secrets if available
        if secrets_dir.exists():
            for secret_file in secrets_dir.glob('*'):
                env_name = secret_file.name.upper()
                if not os.getenv(env_name):
                    try:
                        os.environ[env_name] = secret_file.read_text().strip()
                    except Exception as e:
                        print(f"Warning: Could not load secret {secret_file.name}: {e}")
    
    def _get_secret_key(self) -> str:
        """Get or generate secret key"""
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key:
            secret_key = secrets.token_urlsafe(32)
            print("Warning: SECRET_KEY not set, using generated key (not suitable for production)")
        return secret_key
    
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean value from environment"""
        value = os.getenv(key, '').lower()
        return value in ('true', '1', 'yes', 'on') if value else default
    
    def _get_int(self, key: str, default: int) -> int:
        """Get integer value from environment"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def _get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return DatabaseConfig(
            url=os.getenv('DATABASE_URL', 'sqlite:///app.db'),
            pool_size=self._get_int('DB_POOL_SIZE', 10),
            pool_timeout=self._get_int('DB_POOL_TIMEOUT', 30),
            pool_recycle=self._get_int('DB_POOL_RECYCLE', 3600),
            echo=self._get_bool('DB_ECHO', False)
        )
    
    def _get_redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        return RedisConfig(
            url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            socket_timeout=self._get_int('REDIS_SOCKET_TIMEOUT', 30),
            socket_connect_timeout=self._get_int('REDIS_SOCKET_CONNECT_TIMEOUT', 30)
        )
    
    def _get_celery_config(self) -> CeleryConfig:
        """Get Celery configuration"""
        return CeleryConfig(
            broker_url=os.getenv('CELERY_BROKER_URL', self.redis.url),
            result_backend=os.getenv('CELERY_RESULT_BACKEND', self.redis.url),
            task_serializer=os.getenv('CELERY_TASK_SERIALIZER', 'json'),
            result_serializer=os.getenv('CELERY_RESULT_SERIALIZER', 'json'),
            timezone=os.getenv('CELERY_TIMEZONE', 'UTC'),
            enable_utc=self._get_bool('CELERY_ENABLE_UTC', True)
        )
    
    def _get_whatsapp_config(self) -> WhatsAppConfig:
        """Get WhatsApp configuration"""
        return WhatsAppConfig(
            api_key=os.getenv('WHATSAPP_API_KEY'),
            api_secret=os.getenv('WHATSAPP_API_SECRET'),
            account_sid=os.getenv('WHATSAPP_ACCOUNT_SID'),
            auth_token=os.getenv('WHATSAPP_AUTH_TOKEN'),
            webhook_verify_token=os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN'),
            phone_number_id=os.getenv('WHATSAPP_PHONE_NUMBER_ID'),
            business_account_id=os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
        )
    
    def _get_security_config(self) -> SecurityConfig:
        """Get security configuration"""
        return SecurityConfig(
            secret_key=self.SECRET_KEY,
            jwt_secret_key=os.getenv('JWT_SECRET_KEY', self.SECRET_KEY),
            jwt_access_token_expires=self._get_int('JWT_ACCESS_TOKEN_EXPIRES', 3600),
            password_salt_rounds=self._get_int('PASSWORD_SALT_ROUNDS', 12),
            rate_limit_per_minute=self._get_int('RATE_LIMIT_PER_MINUTE', 60),
            max_content_length=self._get_int('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        )
    
    def _get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration"""
        return MonitoringConfig(
            prometheus_enabled=self._get_bool('PROMETHEUS_ENABLED', True),
            metrics_endpoint=os.getenv('METRICS_ENDPOINT', '/metrics'),
            health_endpoint=os.getenv('HEALTH_ENDPOINT', '/health'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            structured_logging=self._get_bool('STRUCTURED_LOGGING', True),
            sentry_dsn=os.getenv('SENTRY_DSN')
        )
    
    def get_celery_config_dict(self) -> Dict[str, Any]:
        """Get Celery configuration as dictionary"""
        return {
            'broker_url': self.celery.broker_url,
            'result_backend': self.celery.result_backend,
            'task_serializer': self.celery.task_serializer,
            'accept_content': self.celery.accept_content,
            'result_serializer': self.celery.result_serializer,
            'timezone': self.celery.timezone,
            'enable_utc': self.celery.enable_utc,
            'task_routes': self.celery.task_routes or {},
            'beat_schedule': self.celery.beat_schedule or {},
            'worker_prefetch_multiplier': 1,
            'task_acks_late': True,
            'worker_disable_rate_limits': False,
            'task_compression': 'gzip',
            'result_compression': 'gzip',
            'task_serializer': 'json',
            'result_serializer': 'json',
            'accept_content': ['json'],
            'result_expires': 3600,
            'task_track_started': True,
            'task_time_limit': 300,
            'task_soft_time_limit': 240,
            'worker_max_tasks_per_child': 1000,
            'worker_max_memory_per_child': 200000,  # 200MB
        }
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate configuration and return status"""
        checks = {
            'secret_key_set': bool(self.SECRET_KEY and len(self.SECRET_KEY) >= 32),
            'database_configured': bool(self.database.url),
            'redis_configured': bool(self.redis.url),
            'celery_configured': bool(self.celery.broker_url and self.celery.result_backend),
            'whatsapp_configured': bool(self.whatsapp.api_key and self.whatsapp.webhook_verify_token),
            'monitoring_enabled': self.monitoring.prometheus_enabled
        }
        
        return checks
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get application health status"""
        config_checks = self.validate_config()
        
        return {
            'status': 'healthy' if all(config_checks.values()) else 'degraded',
            'timestamp': os.path.getmtime(__file__),
            'version': os.getenv('APP_VERSION', 'development'),
            'environment': self.FLASK_ENV,
            'configuration': config_checks
        }

# Export configuration classes
__all__ = [
    'ProductionConfig',
    'DatabaseConfig', 
    'RedisConfig',
    'CeleryConfig',
    'WhatsAppConfig',
    'SecurityConfig',
    'MonitoringConfig'
]
