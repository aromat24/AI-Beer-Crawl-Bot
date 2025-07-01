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
            
            # User stats
            cursor.execute("SELECT COUNT(*) as count FROM users")
            stats['total_users'] = cursor.fetchone()[0]
            
            # Beer crawl stats
            cursor.execute("SELECT COUNT(*) as count FROM crawl_groups")
            stats['total_crawls'] = cursor.fetchone()[0]
            
            # Set defaults for other stats
            stats['onboarded_users'] = 0
            stats['active_crawls'] = 0
            stats['completed_crawls'] = 0
            stats['new_users_24h'] = 0
            stats['new_crawls_24h'] = 0
            
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
            SELECT id, username, email, created_at, updated_at
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 100
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'phone_number': row[1],  # Use username as phone_number for compatibility
                'name': row[1],  # Use username as name for compatibility
                'age': 'N/A',
                'gender': 'N/A',
                'location': 'N/A',
                'created_at': row[3],
                'updated_at': row[4]
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
        
        # Clear all data but keep schema - use correct table names
        cursor.execute("DELETE FROM group_members")
        cursor.execute("DELETE FROM crawl_sessions")
        cursor.execute("DELETE FROM crawl_groups")
        cursor.execute("DELETE FROM user_preferences")
        cursor.execute("DELETE FROM users")
        
        conn.commit()
        return jsonify({'message': 'Cleared all database data (users, crawls, associations)'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
