"""
Prometheus metrics and monitoring integration for AI Beer Crawl App
"""
import time
import psutil
from functools import wraps
from flask import request, g
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry
from prometheus_client.multiprocess import MultiProcessCollector

# Create custom registry for multiprocess mode
registry = CollectorRegistry()
MultiProcessCollector(registry)

# Define metrics
request_count = Counter(
    'flask_request_count_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

request_duration = Histogram(
    'flask_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

active_users = Gauge(
    'flask_active_users',
    'Number of active users',
    registry=registry
)

celery_task_count = Counter(
    'celery_task_total',
    'Total number of Celery tasks',
    ['task_name', 'status'],
    registry=registry
)

celery_task_duration = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name'],
    registry=registry
)

whatsapp_messages = Counter(
    'whatsapp_messages_total',
    'Total WhatsApp messages processed',
    ['message_type', 'status'],
    registry=registry
)

beer_crawl_groups = Gauge(
    'beer_crawl_active_groups',
    'Number of active beer crawl groups',
    registry=registry
)

database_connections = Gauge(
    'flask_database_pool_connections_active',
    'Number of active database connections',
    registry=registry
)

system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=registry
)

system_memory_usage = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage',
    registry=registry
)

def track_request_metrics(f):
    """Decorator to track request metrics"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        g.start_time = start_time
        
        try:
            response = f(*args, **kwargs)
            status_code = response.status_code if hasattr(response, 'status_code') else 200
        except Exception as e:
            status_code = 500
            raise e
        finally:
            # Record metrics
            duration = time.time() - start_time
            endpoint = request.endpoint or 'unknown'
            method = request.method
            
            request_count.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        
        return response
    return decorated_function

def track_celery_task(task_name):
    """Decorator to track Celery task metrics"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            
            try:
                result = f(*args, **kwargs)
                return result
            except Exception as e:
                status = 'failed'
                raise e
            finally:
                duration = time.time() - start_time
                celery_task_count.labels(
                    task_name=task_name,
                    status=status
                ).inc()
                celery_task_duration.labels(
                    task_name=task_name
                ).observe(duration)
        
        return decorated_function
    return decorator

def track_whatsapp_message(message_type, status='success'):
    """Track WhatsApp message metrics"""
    whatsapp_messages.labels(
        message_type=message_type,
        status=status
    ).inc()

def update_system_metrics():
    """Update system-level metrics"""
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    system_cpu_usage.set(cpu_percent)
    
    # Memory usage
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    system_memory_usage.set(memory_percent)

def update_app_metrics(app):
    """Update application-specific metrics"""
    with app.app_context():
        from src.models.user import User
        from src.models.beer_crawl import CrawlGroup
        
        # Count active users (users with recent activity)
        # This would need to be implemented based on your user activity tracking
        active_user_count = User.query.count()  # Simplified
        active_users.set(active_user_count)
        
        # Count active groups
        active_group_count = CrawlGroup.query.filter_by(status='active').count()
        beer_crawl_groups.set(active_group_count)

def init_metrics(app):
    """Initialize metrics collection for Flask app"""
    
    @app.route('/metrics')
    def metrics():
        """Prometheus metrics endpoint"""
        # Update metrics before serving
        update_system_metrics()
        update_app_metrics(app)
        
        return generate_latest(registry), 200, {'Content-Type': CONTENT_TYPE_LATEST}
    
    @app.before_request
    def before_request():
        """Track request start time"""
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        """Track request completion"""
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            endpoint = request.endpoint or 'unknown'
            method = request.method
            status_code = response.status_code
            
            request_count.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        
        return response

# Export metrics for use in other modules
__all__ = [
    'track_request_metrics',
    'track_celery_task', 
    'track_whatsapp_message',
    'init_metrics',
    'registry'
]
