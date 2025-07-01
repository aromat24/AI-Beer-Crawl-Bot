#!/usr/bin/env python3
"""
Beer Crawl Bot Dashboard - Complete Data Overview
Shows all databases, Redis queues, configuration, and provides management tools.
"""

import os
import sys
import sqlite3
import redis
from datetime import datetime
from pathlib import Path
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BeerCrawlDashboard:
    def __init__(self):
        self.workspace_root = '/workspaces/Beer_Crawl'
        self.databases = {}
        self.redis_connections = {}
        self.setup_connections()
    
    def setup_connections(self):
        """Setup connections to all data sources"""
        # Find all SQLite databases
        db_paths = [
            '/workspaces/Beer_Crawl/instance/app.db',
            '/workspaces/Beer_Crawl/database/app.db'
        ]
        
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    self.databases[db_path] = conn
                    print(f"✅ Connected to SQLite: {db_path}")
                except Exception as e:
                    print(f"❌ Failed to connect to {db_path}: {e}")
        
        # Setup Redis connections
        try:
            # Celery/Queue Redis (db=0)
            self.redis_connections['celery'] = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_connections['celery'].ping()
            print("✅ Connected to Redis (Celery - db=0)")
        except Exception as e:
            print(f"❌ Failed to connect to Redis Celery: {e}")
        
        try:
            # Deduplication Redis (db=1)
            self.redis_connections['dedup'] = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
            self.redis_connections['dedup'].ping()
            print("✅ Connected to Redis (Deduplication - db=1)")
        except Exception as e:
            print(f"❌ Failed to connect to Redis Deduplication: {e}")
    
    def show_config(self):
        """Show current configuration"""
        print("\n" + "="*80)
        print("📋 CONFIGURATION")
        print("="*80)
        
        # Environment variables
        env_vars = [
            'FLASK_DEBUG', 'SECRET_KEY', 'DATABASE_URL', 'GREEN_API_INSTANCE_ID',
            'GREEN_API_TOKEN', 'WEBHOOK_URL', 'MIN_GROUP_SIZE', 'MAX_GROUP_SIZE',
            'DEDUP_WINDOW_MINUTES', 'RATE_LIMIT_MESSAGES', 'RATE_LIMIT_WINDOW_MINUTES'
        ]
        
        print("\n🔧 Environment Variables:")
        for var in env_vars:
            value = os.getenv(var, 'Not Set')
            if 'TOKEN' in var or 'SECRET' in var:
                value = f"{value[:10]}..." if value != 'Not Set' and len(value) > 10 else value
            print(f"  {var}: {value}")
        
        # Database paths
        print(f"\n📁 Database Paths:")
        for db_path in self.databases.keys():
            size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
            modified = datetime.fromtimestamp(os.path.getmtime(db_path)).strftime('%Y-%m-%d %H:%M:%S') if os.path.exists(db_path) else 'N/A'
            print(f"  {db_path} ({size} bytes, modified: {modified})")
    
    def show_sqlite_data(self):
        """Show data from all SQLite databases"""
        print("\n" + "="*80)
        print("🗄️  SQLITE DATABASES")
        print("="*80)
        
        for db_path, conn in self.databases.items():
            print(f"\n📊 Database: {db_path}")
            print("-" * 60)
            
            try:
                # Get all tables
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                print(f"Tables: {[table['name'] for table in tables]}")
                
                for table in tables:
                    table_name = table['name']
                    if table_name.startswith('sqlite_'):
                        continue
                    
                    print(f"\n🏷️  Table: {table_name}")
                    
                    # Count rows
                    count = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()
                    print(f"   Row count: {count['count']}")
                    
                    # Show schema
                    schema = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                    print(f"   Columns: {[col['name'] for col in schema]}")
                    
                    # Show sample data (first 3 rows)
                    if count['count'] > 0:
                        rows = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
                        print(f"   Sample data:")
                        for i, row in enumerate(rows, 1):
                            row_dict = dict(row)
                            # Truncate long values
                            for key, value in row_dict.items():
                                if isinstance(value, str) and len(value) > 50:
                                    row_dict[key] = value[:47] + "..."
                            print(f"     Row {i}: {row_dict}")
                        
                        if count['count'] > 3:
                            print(f"     ... and {count['count'] - 3} more rows")
            
            except Exception as e:
                print(f"   ❌ Error reading database: {e}")
    
    def show_redis_data(self):
        """Show data from Redis databases"""
        print("\n" + "="*80)
        print("🔴 REDIS DATA")
        print("="*80)
        
        for name, redis_conn in self.redis_connections.items():
            print(f"\n📊 Redis Database: {name}")
            print("-" * 60)
            
            try:
                # Get info
                info = redis_conn.info()
                db_info = info.get('db0', {}) if name == 'celery' else info.get('db1', {})
                print(f"   Keys: {db_info.get('keys', 0)}")
                print(f"   Expires: {db_info.get('expires', 0)}")
                
                # Get all keys
                keys = redis_conn.keys('*')
                print(f"   All keys: {keys[:10]}{'...' if len(keys) > 10 else ''}")
                
                # Show sample data for each key type
                for key in keys[:5]:  # Show first 5 keys
                    key_type = redis_conn.type(key)
                    ttl = redis_conn.ttl(key)
                    ttl_str = f"TTL: {ttl}s" if ttl > 0 else "No expiry" if ttl == -1 else "Expired"
                    
                    print(f"   🔑 {key} ({key_type}, {ttl_str})")
                    
                    try:
                        if key_type == 'string':
                            value = redis_conn.get(key)
                            if len(str(value)) > 100:
                                value = str(value)[:97] + "..."
                            print(f"      Value: {value}")
                        elif key_type == 'hash':
                            hash_data = redis_conn.hgetall(key)
                            print(f"      Hash fields: {list(hash_data.keys())}")
                        elif key_type == 'list':
                            length = redis_conn.llen(key)
                            print(f"      List length: {length}")
                            if length > 0:
                                sample = redis_conn.lrange(key, 0, 2)
                                print(f"      Sample items: {sample}")
                        elif key_type == 'set':
                            members = redis_conn.smembers(key)
                            print(f"      Set members: {list(members)[:5]}")
                        elif key_type == 'zset':
                            count = redis_conn.zcard(key)
                            print(f"      Sorted set size: {count}")
                    except Exception as e:
                        print(f"      ❌ Error reading key: {e}")
                
                if len(keys) > 5:
                    print(f"   ... and {len(keys) - 5} more keys")
            
            except Exception as e:
                print(f"   ❌ Error reading Redis: {e}")
    
    def show_system_status(self):
        """Show system status"""
        print("\n" + "="*80)
        print("⚙️  SYSTEM STATUS")
        print("="*80)
        
        # Check services
        services = {
            'Flask App': self.check_service('flask', 5000),
            'Celery Worker': self.check_celery_worker(),
            'Redis Server': self.check_service('redis', 6379),
            'Ngrok Tunnel': self.check_ngrok()
        }
        
        for service, status in services.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {service}")
        
        # Show URLs
        print(f"\n🌐 URLs:")
        webhook_url = os.getenv('WEBHOOK_URL', 'Not configured')
        print(f"   Webhook URL: {webhook_url}")
        print(f"   Local Flask: http://localhost:5000")
        print(f"   Dashboard endpoint: http://localhost:5000/dashboard")
    
    def check_service(self, service, port):
        """Check if a service is running on a port"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def check_celery_worker(self):
        """Check if Celery worker is running"""
        try:
            if 'celery' in self.redis_connections:
                # Check for active workers by looking at Celery inspect
                import subprocess
                result = subprocess.run(['celery', '-A', 'src.tasks.celery_tasks', 'inspect', 'active'], 
                                      capture_output=True, text=True, timeout=5)
                return 'OK' in result.stdout
        except:
            pass
        return False
    
    def check_ngrok(self):
        """Check if ngrok tunnel is active"""
        try:
            import requests
            response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
            tunnels = response.json().get('tunnels', [])
            return len(tunnels) > 0
        except:
            return False
    
    def clear_dedup_data(self):
        """Clear deduplication data"""
        if 'dedup' not in self.redis_connections:
            print("❌ Deduplication Redis not available")
            return
        
        try:
            redis_conn = self.redis_connections['dedup']
            keys = redis_conn.keys('*')
            if keys:
                deleted = redis_conn.delete(*keys)
                print(f"✅ Cleared {deleted} deduplication keys")
            else:
                print("ℹ️  No deduplication data to clear")
        except Exception as e:
            print(f"❌ Error clearing deduplication data: {e}")
    
    def clear_celery_queues(self):
        """Clear Celery queues"""
        if 'celery' not in self.redis_connections:
            print("❌ Celery Redis not available")
            return
        
        try:
            redis_conn = self.redis_connections['celery']
            keys = redis_conn.keys('*')
            if keys:
                deleted = redis_conn.delete(*keys)
                print(f"✅ Cleared {deleted} Celery queue items")
            else:
                print("ℹ️  No Celery queue data to clear")
        except Exception as e:
            print(f"❌ Error clearing Celery queues: {e}")
    
    def reset_database(self, db_path):
        """Reset a specific database"""
        if db_path not in self.databases:
            print(f"❌ Database {db_path} not connected")
            return
        
        try:
            conn = self.databases[db_path]
            
            # Get all tables
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            
            for table in tables:
                table_name = table['name']
                if not table_name.startswith('sqlite_'):
                    conn.execute(f"DELETE FROM {table_name}")
            
            conn.commit()
            print(f"✅ Reset database {db_path}")
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
    
    def show_management_menu(self):
        """Show management options"""
        print("\n" + "="*80)
        print("🛠️  MANAGEMENT OPTIONS")
        print("="*80)
        print("1. Clear deduplication data")
        print("2. Clear Celery queues")
        print("3. Reset main database (instance/app.db)")
        print("4. Reset secondary database (database/app.db)")
        print("5. Show this dashboard again")
        print("6. Exit")
        
        while True:
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                self.clear_dedup_data()
                break
            elif choice == '2':
                self.clear_celery_queues()
                break
            elif choice == '3':
                confirm = input("Are you sure you want to reset the main database? (yes/no): ")
                if confirm.lower() == 'yes':
                    self.reset_database('/workspaces/Beer_Crawl/instance/app.db')
                break
            elif choice == '4':
                confirm = input("Are you sure you want to reset the secondary database? (yes/no): ")
                if confirm.lower() == 'yes':
                    self.reset_database('/workspaces/Beer_Crawl/database/app.db')
                break
            elif choice == '5':
                self.run_dashboard()
                break
            elif choice == '6':
                break
            else:
                print("Invalid choice. Please enter 1-6.")
    
    def run_dashboard(self):
        """Run the complete dashboard"""
        print("🍺 Beer Crawl Bot Dashboard")
        print("Generated at:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.show_config()
        self.show_sqlite_data()
        self.show_redis_data()
        self.show_system_status()
        self.show_management_menu()
    
    def close_connections(self):
        """Close all database connections"""
        for conn in self.databases.values():
            conn.close()

def main():
    dashboard = BeerCrawlDashboard()
    try:
        dashboard.run_dashboard()
    finally:
        dashboard.close_connections()

if __name__ == "__main__":
    main()
