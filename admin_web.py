#!/usr/bin/env python3
"""
Web-based Admin Dashboard for AI Beer Crawl Bot
Provides a browser-based interface to monitor and manage the bot.
"""

import os
import sys
import json
import sqlite3
import redis
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

app = Flask(__name__)
app.secret_key = 'admin-dashboard-secret-key-change-in-production'

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
DB_PATH = os.getenv('DATABASE_URL', 'sqlite:///instance/app.db').replace('sqlite:///', '')
if not DB_PATH.startswith('/'):
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_PATH)
ENV_FILE = '.env'

# Debug: Print the actual database path being used
print(f"DEBUG: DB_PATH = {DB_PATH}")
print(f"DEBUG: File exists? {os.path.exists(DB_PATH)}")

def get_redis_client(db=0):
    """Get Redis client for specified database."""
    try:
        client = redis.from_url(REDIS_URL, db=db, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None

def get_db_connection():
    """Get SQLite database connection."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        return None

def load_env_config():
    """Load environment configuration."""
    config = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    return config

@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('admin_dashboard.html')

@app.route('/api/stats')
def api_stats():
    """Get system statistics."""
    stats = {}
    
    # Database stats
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # User stats from user_preferences table
            cursor.execute("SELECT COUNT(*) as count FROM user_preferences")
            stats['total_users'] = cursor.fetchone()[0]
            
            # Since user_preferences represents onboarded users
            stats['onboarded_users'] = stats['total_users']
            
            # Beer crawl stats
            cursor.execute("SELECT COUNT(*) as count FROM crawl_groups")
            stats['total_crawls'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) as count FROM crawl_groups WHERE status = 'ACTIVE'")
            stats['active_crawls'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) as count FROM crawl_groups WHERE status = 'COMPLETED'")
            stats['completed_crawls'] = cursor.fetchone()[0]
            
            # Users in last 24h
            cursor.execute("""
                SELECT COUNT(*) as count FROM user_preferences 
                WHERE datetime(created_at) > datetime('now', '-24 hours')
            """)
            stats['new_users_24h'] = cursor.fetchone()[0]
            
            # Crawls in last 24h
            cursor.execute("""
                SELECT COUNT(*) as count FROM crawl_groups 
                WHERE datetime(created_at) > datetime('now', '-24 hours')
            """)
            stats['new_crawls_24h'] = cursor.fetchone()[0]
            
        except Exception as e:
            stats['db_error'] = str(e)
        finally:
            conn.close()
    else:
        stats['db_error'] = 'Cannot connect to database'
    
    # Redis stats
    redis_client = get_redis_client(0)  # Main Redis DB
    if redis_client:
        try:
            info = redis_client.info()
            stats['redis_connected_clients'] = info.get('connected_clients', 0)
            stats['redis_used_memory'] = info.get('used_memory_human', 'N/A')
            stats['redis_total_commands'] = info.get('total_commands_processed', 0)
        except Exception as e:
            stats['redis_error'] = str(e)
    else:
        stats['redis_error'] = 'Cannot connect to Redis'
    
    # Deduplication stats (Redis DB 1)
    dedup_client = get_redis_client(1)
    if dedup_client:
        try:
            dedup_keys = dedup_client.keys('*')
            stats['dedup_entries'] = len(dedup_keys) if dedup_keys else 0
        except Exception as e:
            stats['dedup_error'] = str(e)
    else:
        stats['dedup_error'] = 'Cannot connect to Redis dedup DB'
    
    # Environment config
    stats['env_config'] = load_env_config()
    
    return jsonify(stats)

@app.route('/api/users')
def api_users():
    """Get users data."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Cannot connect to database'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, whatsapp_number, preferred_area, preferred_group_type, 
                   gender, age_range, created_at, updated_at
            FROM user_preferences 
            ORDER BY created_at DESC 
            LIMIT 100
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'whatsapp_number': row[1],
                'name': row[1],  # Use whatsapp_number as name for display
                'phone_number': row[1],
                'preferred_area': row[2],
                'preferred_group_type': row[3],
                'gender': row[4] or 'N/A',
                'age_range': row[5] or 'N/A',
                'location': row[2],  # Use preferred_area as location
                'onboarding_completed': True,  # If they're in user_preferences, they're onboarded
                'created_at': row[6],
                'updated_at': row[7]
            })
        
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/crawls')
def api_crawls():
    """Get beer crawls data."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Cannot connect to database'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, area, status, max_members, 
                   created_at, updated_at, current_members
            FROM crawl_groups 
            ORDER BY created_at DESC 
            LIMIT 50
        """)
        
        crawls = []
        for row in cursor.fetchall():
            crawls.append({
                'id': row[0],
                'name': row[1],  # Use area as name
                'status': row[2],
                'location': row[1],  # Use area as location
                'max_participants': row[3],
                'created_at': row[4],
                'updated_at': row[5],
                'current_participants': row[6] if row[6] else 0
            })
        
        return jsonify(crawls)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/redis')
def api_redis():
    """Get Redis data."""
    data = {}
    
    # Main Redis DB (Celery)
    redis_client = get_redis_client(0)
    if redis_client:
        try:
            keys = redis_client.keys('*')
            data['main_db'] = {
                'total_keys': len(keys) if keys else 0,
                'keys': keys[:20] if keys else []  # Show first 20 keys
            }
        except Exception as e:
            data['main_db'] = {'error': str(e)}
    
    # Deduplication DB
    dedup_client = get_redis_client(1)
    if dedup_client:
        try:
            keys = dedup_client.keys('*')
            entries = {}
            if keys and len(keys) > 0:
                for key in keys[:10]:  # Show first 10 entries
                    try:
                        ttl = dedup_client.ttl(key)
                        entries[key] = {
                            'value': dedup_client.get(key),
                            'ttl': ttl if ttl > 0 else 'No expiry'
                        }
                    except Exception:
                        entries[key] = {'error': 'Cannot read value'}
            
            data['dedup_db'] = {
                'total_keys': len(keys) if keys else 0,
                'entries': entries
            }
        except Exception as e:
            data['dedup_db'] = {'error': str(e)}
    else:
        data['dedup_db'] = {'error': 'Cannot connect to Redis dedup DB'}
    
    return jsonify(data)

@app.route('/api/logs')
def api_logs():
    """Get recent log entries."""
    log_file = 'logs/app.log'
    if not os.path.exists(log_file):
        return jsonify({'error': 'Log file not found'})
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Get last 50 lines
        recent_lines = lines[-50:] if len(lines) > 50 else lines
        return jsonify({'logs': recent_lines})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/clear_dedup', methods=['POST'])
def api_clear_dedup():
    """Clear deduplication data."""
    dedup_client = get_redis_client(1)
    if not dedup_client:
        return jsonify({'error': 'Cannot connect to Redis dedup DB'}), 500
    
    try:
        keys = dedup_client.keys('*')
        if keys and len(keys) > 0:
            dedup_client.delete(*keys)
            return jsonify({'message': f'Cleared {len(keys)} deduplication entries'})
        else:
            return jsonify({'message': 'No deduplication entries to clear'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_redis', methods=['POST'])
def api_clear_redis():
    """Clear main Redis database (Celery queues)."""
    redis_client = get_redis_client(0)
    if not redis_client:
        return jsonify({'error': 'Cannot connect to Redis'}), 500
    
    try:
        redis_client.flushdb()
        return jsonify({'message': 'Cleared main Redis database (Celery queues)'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_database', methods=['POST'])
def api_clear_database():
    """Clear SQLite database (DANGEROUS - removes all data)."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Cannot connect to database'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Clear all data but keep schema - use correct table names and order
        cursor.execute("DELETE FROM crawl_sessions")
        cursor.execute("DELETE FROM group_members")
        cursor.execute("DELETE FROM crawl_groups")
        cursor.execute("DELETE FROM user_preferences")
        cursor.execute("DELETE FROM users")  # This table is empty anyway
        cursor.execute("DELETE FROM bars")
        
        conn.commit()
        return jsonify({'message': 'Cleared all database data (users, crawls, bars, sessions)'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/bot-settings', methods=['GET'])
def api_get_bot_settings():
    """Get current bot behavior settings."""
    redis_client = get_redis_client(0)
    
    # Default settings
    default_settings = {
        'min_group_size': 2,
        'max_group_size': 5,
        'group_threshold': 3,
        'group_deletion_timer': 24,
        'session_duration': 4,
        'message_cooldown': 30,
        'user_cooldown': 10,
        'rate_limit_window': 300,
        'rate_limit_max': 5,
        'bar_progression_time': 60,
        'wait_between_bars': 15,
        'join_deadline': 30,
        'auto_start_threshold': 4,
        'auto_group_creation': True,
        'smart_matching': True,
        'auto_progression': True,
        'welcome_messages': True,
        'reminder_messages': True,
        'debug_mode': False
    }
    
    if not redis_client:
        return jsonify(default_settings)
    
    try:
        # Get settings from Redis
        stored_settings = redis_client.hgetall('bot_settings')
        
        # Merge with defaults
        settings = default_settings.copy()
        for key, value in stored_settings.items():
            if key in settings:
                if isinstance(settings[key], bool):
                    settings[key] = value.lower() in ('true', '1', 'yes')
                elif isinstance(settings[key], int):
                    settings[key] = int(value)
                else:
                    settings[key] = value
        
        return jsonify(settings)
    except Exception as e:
        return jsonify(default_settings)

@app.route('/api/bot-settings', methods=['POST'])
def api_save_bot_settings():
    """Save bot behavior settings."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    redis_client = get_redis_client(0)
    if not redis_client:
        return jsonify({'error': 'Cannot connect to Redis'}), 500
    
    try:
        # Validate settings
        required_fields = [
            'min_group_size', 'max_group_size', 'group_threshold',
            'message_cooldown', 'user_cooldown', 'rate_limit_window',
            'rate_limit_max', 'bar_progression_time'
        ]
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate ranges
        if data['min_group_size'] >= data['max_group_size']:
            return jsonify({'error': 'Min group size must be less than max group size'}), 400
        
        if data['min_group_size'] < 2:
            return jsonify({'error': 'Min group size must be at least 2'}), 400
        
        if data['max_group_size'] > 20:
            return jsonify({'error': 'Max group size cannot exceed 20'}), 400
        
        # Convert all values to strings for Redis storage
        redis_data = {}
        for key, value in data.items():
            if isinstance(value, bool):
                redis_data[key] = 'true' if value else 'false'
            else:
                redis_data[key] = str(value)
        
        # Save to Redis
        redis_client.hset('bot_settings', mapping=redis_data)
        
        # Also update environment variables file for persistence
        env_updates = {
            'MIN_GROUP_SIZE': str(data['min_group_size']),
            'MAX_GROUP_SIZE': str(data['max_group_size']),
            'MESSAGE_COOLDOWN': str(data['message_cooldown']),
            'USER_COOLDOWN': str(data['user_cooldown']),
            'RATE_LIMIT_WINDOW': str(data['rate_limit_window']),
            'RATE_LIMIT_MAX': str(data['rate_limit_max']),
            'DEBUG_MODE': 'true' if data.get('debug_mode', False) else 'false'
        }
        
        # Update .env file
        try:
            update_env_file(env_updates)
        except Exception as e:
            print(f"Warning: Could not update .env file: {e}")
        
        return jsonify({'message': 'Settings saved successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_env_file(updates):
    """Update .env file with new values."""
    env_file = '.env'
    if not os.path.exists(env_file):
        return
    
    lines = []
    updated_keys = set()
    
    # Read existing file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update existing lines
    for i, line in enumerate(lines):
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0].strip()
            if key in updates:
                lines[i] = f"{key}={updates[key]}\n"
                updated_keys.add(key)
    
    # Add new keys that weren't found
    for key, value in updates.items():
        if key not in updated_keys:
            lines.append(f"{key}={value}\n")
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(lines)

# Bot response management endpoints
@app.route('/api/bot-responses', methods=['GET'])
def api_get_bot_responses():
    """Get all bot responses."""
    try:
        # Import here to avoid circular imports
        sys.path.insert(0, os.path.dirname(__file__))
        from src.utils.bot_responses import bot_response_manager
        
        responses = bot_response_manager.get_all_responses()
        return jsonify({
            'responses': responses,
            'keys': list(responses.keys())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot-responses', methods=['POST'])
def api_save_bot_responses():
    """Save bot responses."""
    data = request.get_json()
    
    if not data or 'responses' not in data:
        return jsonify({'error': 'No responses data provided'}), 400
    
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from src.utils.bot_responses import bot_response_manager
        
        success = bot_response_manager.save_responses(data['responses'])
        
        if success:
            return jsonify({'message': 'Bot responses saved successfully'})
        else:
            return jsonify({'error': 'Failed to save bot responses'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot-responses/reset', methods=['POST'])
def api_reset_bot_responses():
    """Reset bot responses to defaults."""
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from src.utils.bot_responses import bot_response_manager
        
        success = bot_response_manager.reset_to_defaults()
        
        if success:
            return jsonify({'message': 'Bot responses reset to defaults'})
        else:
            return jsonify({'error': 'Failed to reset bot responses'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Celery/Flower monitoring endpoints
@app.route('/api/celery/stats')
def api_celery_stats():
    """Get Celery worker and task statistics."""
    try:
        import requests
        
        # Try to get stats from Flower if it's running
        flower_url = 'http://localhost:5555'
        stats = {
            'flower_available': False,
            'workers': [],
            'tasks': {
                'active': 0,
                'processed': 0,
                'failed': 0,
                'retried': 0
            },
            'queues': {}
        }
        
        try:
            # Check if Flower is running
            response = requests.get(f'{flower_url}/api/workers', timeout=2)
            if response.status_code == 200:
                stats['flower_available'] = True
                workers_data = response.json()
                
                for worker_name, worker_info in workers_data.items():
                    stats['workers'].append({
                        'name': worker_name,
                        'status': 'online' if worker_info.get('status') else 'offline',
                        'active_tasks': len(worker_info.get('active', [])),
                        'processed': worker_info.get('processed', 0),
                        'load_avg': worker_info.get('loadavg', [0, 0, 0])
                    })
            
            # Get task stats
            response = requests.get(f'{flower_url}/api/tasks', timeout=2)
            if response.status_code == 200:
                tasks_data = response.json()
                for task_id, task_info in tasks_data.items():
                    state = task_info.get('state', 'unknown').lower()
                    if state == 'success':
                        stats['tasks']['processed'] += 1
                    elif state == 'failure':
                        stats['tasks']['failed'] += 1
                    elif state == 'retry':
                        stats['tasks']['retried'] += 1
                    elif state in ['pending', 'started']:
                        stats['tasks']['active'] += 1
                        
        except requests.exceptions.RequestException:
            # Flower not available, get basic stats from Redis
            redis_client = get_redis_client(0)
            if redis_client:
                try:
                    # Get basic queue info
                    celery_keys = redis_client.keys('celery*')
                    stats['queues']['celery'] = len(celery_keys) if celery_keys else 0
                    
                    # Try to get some basic worker info
                    worker_keys = redis_client.keys('_kombu.binding.*')
                    stats['redis_queues'] = len(worker_keys) if worker_keys else 0
                except Exception as e:
                    stats['redis_error'] = str(e)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/celery/flower/start', methods=['POST'])
def api_start_flower():
    """Start Flower monitoring."""
    try:
        import subprocess
        
        # Check if Flower is already running
        try:
            import requests
            response = requests.get('http://localhost:5555', timeout=2)
            if response.status_code == 200:
                return jsonify({'message': 'Flower is already running on port 5555'})
        except:
            pass
        
        # Start Flower in background
        cmd = ['celery', '-A', 'src.tasks.celery_tasks.celery', 'flower', '--port=5555']
        process = subprocess.Popen(cmd, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 cwd=os.path.dirname(os.path.abspath(__file__)))
        
        # Give it a moment to start
        import time
        time.sleep(2)
        
        # Check if it started successfully
        try:
            import requests
            response = requests.get('http://localhost:5555', timeout=2)
            if response.status_code == 200:
                return jsonify({
                    'message': 'Flower started successfully',
                    'url': 'http://localhost:5555',
                    'pid': process.pid
                })
        except:
            pass
        
        return jsonify({
            'message': 'Flower start command sent, check http://localhost:5555 in a few seconds',
            'url': 'http://localhost:5555'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/database')
def api_debug_database():
    """Debug endpoint to inspect database schema."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Cannot connect to database'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        result = {
            'database_path': DB_PATH,
            'tables': []
        }
        
        for table in tables:
            table_name = table[0]
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get sample data
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_data = cursor.fetchall()
            
            result['tables'].append({
                'name': table_name,
                'columns': [{'name': col[1], 'type': col[2], 'nullable': not col[3]} for col in columns],
                'row_count': row_count,
                'sample_data': sample_data
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0', 
        port=int(os.environ.get('ADMIN_PORT', 5002)), 
        debug=os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    )
