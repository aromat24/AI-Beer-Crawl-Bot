#!/usr/bin/env python3
"""
AI Beer Crawl Bot Admin Dashboard
View all databases, data sources, and system status
"""
import os
import sys
import sqlite3
import redis
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AdminDashboard:
    def __init__(self):
        self.databases = {}
        self.redis_clients = {}
        
    def connect_databases(self):
        """Connect to all databases"""
        # SQLite databases
        db_paths = [
            '/workspaces/Beer_Crawl/database/app.db',
            '/workspaces/Beer_Crawl/instance/app.db',
            '/workspaces/Beer_Crawl/app.db'
        ]
        
        for path in db_paths:
            if os.path.exists(path):
                try:
                    conn = sqlite3.connect(path)
                    self.databases[path] = conn
                    print(f"✅ Connected to SQLite: {path}")
                except Exception as e:
                    print(f"❌ Error connecting to {path}: {e}")
        
        # Redis connections
        try:
            # Main Redis (Celery queue)
            self.redis_clients['celery'] = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_clients['celery'].ping()
            print("✅ Connected to Redis DB 0 (Celery)")
        except Exception as e:
            print(f"❌ Error connecting to Redis DB 0: {e}")
        
        try:
            # Deduplication Redis
            self.redis_clients['dedupe'] = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
            self.redis_clients['dedupe'].ping()
            print("✅ Connected to Redis DB 1 (Deduplication)")
        except Exception as e:
            print(f"❌ Error connecting to Redis DB 1: {e}")
    
    def show_sqlite_data(self):
        """Show data from SQLite databases"""
        print("\n📊 SQLITE DATABASES")
        print("=" * 60)
        
        for db_path, conn in self.databases.items():
            print(f"\n📁 Database: {db_path}")
            print("-" * 40)
            
            try:
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                for (table_name,) in tables:
                    if table_name == 'sqlite_sequence':
                        continue
                        
                    print(f"\n🔍 Table: {table_name}")
                    
                    # Get table info
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    col_names = [col[1] for col in columns]
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    
                    print(f"   Columns: {', '.join(col_names)}")
                    print(f"   Rows: {count}")
                    
                    # Show recent data (limit 3)
                    if count > 0:
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                        rows = cursor.fetchall()
                        
                        for i, row in enumerate(rows):
                            print(f"   Row {i+1}: {dict(zip(col_names, row))}")
                        
                        if count > 3:
                            print(f"   ... and {count-3} more rows")
                            
            except Exception as e:
                print(f"❌ Error reading database: {e}")
    
    def show_redis_data(self):
        """Show data from Redis"""
        print("\n📊 REDIS DATABASES")
        print("=" * 60)
        
        for db_name, client in self.redis_clients.items():
            print(f"\n🔍 Redis DB: {db_name}")
            print("-" * 30)
            
            try:
                # Get database info
                info = client.info()
                db_size = info.get('db0', {}).get('keys', 0) if db_name == 'celery' else info.get('db1', {}).get('keys', 0)
                
                print(f"   Keys: {db_size}")
                print(f"   Memory: {info.get('used_memory_human', 'N/A')}")
                
                # Show some keys by pattern
                patterns = {
                    'celery': ['celery*', '_kombu*'],
                    'dedupe': ['msg_dedupe:*', 'user_cooldown:*', 'msg_count:*']
                }
                
                for pattern in patterns.get(db_name, []):
                    keys = list(client.scan_iter(match=pattern, count=5))
                    if keys:
                        print(f"   Pattern '{pattern}': {len(keys)} keys")
                        for key in keys[:3]:
                            try:
                                value = client.get(key)
                                ttl = client.ttl(key)
                                print(f"     {key}: {value} (TTL: {ttl}s)")
                            except:
                                print(f"     {key}: <complex data>")
                
            except Exception as e:
                print(f"❌ Error reading Redis: {e}")
    
    def show_api_endpoints(self):
        """Show available API endpoints"""
        print("\n🌐 API ENDPOINTS")
        print("=" * 60)
        
        endpoints = [
            ("Main App", "http://localhost:5000"),
            ("Health Check", "http://localhost:5000/health"),
            ("WhatsApp Webhook", "http://localhost:5000/webhook/whatsapp"),
            ("Ngrok Dashboard", "http://localhost:4040"),
            ("Webhook Debugger", "http://localhost:5001"),
            ("User Signup", "POST http://localhost:5000/api/beer-crawl/signup"),
            ("Find Group", "POST http://localhost:5000/api/beer-crawl/find-group"),
            ("List Groups", "GET http://localhost:5000/api/beer-crawl/groups"),
            ("Start Group", "POST http://localhost:5000/api/beer-crawl/groups/{id}/start"),
        ]
        
        for name, url in endpoints:
            print(f"📌 {name}: {url}")
    
    def show_log_files(self):
        """Show log file locations"""
        print("\n📄 LOG FILES")
        print("=" * 60)
        
        log_files = [
            '/workspaces/Beer_Crawl/logs/app.log',
            '/workspaces/Beer_Crawl/celery.log',
            '/workspaces/Beer_Crawl/flask.log', 
            '/workspaces/Beer_Crawl/ngrok.log'
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                size = os.path.getsize(log_file)
                mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                print(f"📄 {log_file}")
                print(f"   Size: {size} bytes, Modified: {mtime}")
                
                # Show last few lines
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            print(f"   Last line: {lines[-1].strip()}")
                except:
                    print("   Could not read file")
            else:
                print(f"📄 {log_file} (not found)")
    
    def show_environment(self):
        """Show environment configuration"""
        print("\n⚙️ ENVIRONMENT CONFIGURATION")
        print("=" * 60)
        
        env_vars = [
            'GREEN_API_INSTANCE_ID', 'GREEN_API_TOKEN', 'WHATSAPP_PHONE_NUMBER',
            'MIN_GROUP_SIZE', 'MAX_GROUP_SIZE',
            'MESSAGE_COOLDOWN', 'USER_COOLDOWN', 'RATE_LIMIT_MAX',
            'CELERY_BROKER_URL', 'DATABASE_URL'
        ]
        
        for var in env_vars:
            value = os.environ.get(var, 'NOT SET')
            # Hide sensitive tokens
            if 'TOKEN' in var and value != 'NOT SET':
                value = value[:8] + '...' + value[-4:]
            print(f"🔧 {var}: {value}")
    
    def interactive_menu(self):
        """Interactive menu for exploring data"""
        while True:
            print("\n🎛️ ADMIN DASHBOARD MENU")
            print("=" * 40)
            print("1. 📊 View SQLite Data")
            print("2. 🔄 View Redis Data") 
            print("3. 🌐 View API Endpoints")
            print("4. 📄 View Log Files")
            print("5. ⚙️ View Environment")
            print("6. 🧹 Clear Deduplication Data")
            print("7. 🔄 Refresh All Data")
            print("0. ❌ Exit")
            
            choice = input("\nEnter choice (0-7): ").strip()
            
            if choice == '1':
                self.show_sqlite_data()
            elif choice == '2':
                self.show_redis_data()
            elif choice == '3':
                self.show_api_endpoints()
            elif choice == '4':
                self.show_log_files()
            elif choice == '5':
                self.show_environment()
            elif choice == '6':
                self.clear_deduplication()
            elif choice == '7':
                self.connect_databases()
            elif choice == '0':
                break
            else:
                print("❌ Invalid choice")
            
            input("\nPress Enter to continue...")
    
    def clear_deduplication(self):
        """Clear deduplication data"""
        try:
            if 'dedupe' in self.redis_clients:
                client = self.redis_clients['dedupe']
                keys = list(client.scan_iter())
                if keys:
                    client.delete(*keys)
                    print(f"🧹 Cleared {len(keys)} deduplication keys")
                else:
                    print("ℹ️ No deduplication keys to clear")
            else:
                print("❌ No deduplication Redis connection")
        except Exception as e:
            print(f"❌ Error clearing deduplication: {e}")
    
    def run_full_report(self):
        """Run full dashboard report"""
        print("🎛️ AI BEER CRAWL BOT - ADMIN DASHBOARD")
        print("=" * 80)
        
        self.connect_databases()
        self.show_environment()
        self.show_api_endpoints()
        self.show_sqlite_data()
        self.show_redis_data()
        self.show_log_files()
        
        print("\n🎯 QUICK ACTIONS")
        print("=" * 40)
        print("To clear deduplication: python admin_dashboard.py --clear-dedupe")
        print("To interactive mode: python admin_dashboard.py --interactive")

def main():
    dashboard = AdminDashboard()
    
    if len(sys.argv) > 1:
        if '--clear-dedupe' in sys.argv:
            dashboard.connect_databases()
            dashboard.clear_deduplication()
        elif '--interactive' in sys.argv:
            dashboard.connect_databases()
            dashboard.interactive_menu()
        else:
            print("Usage: python admin_dashboard.py [--clear-dedupe] [--interactive]")
    else:
        dashboard.run_full_report()

if __name__ == "__main__":
    main()
