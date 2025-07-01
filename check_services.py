#!/usr/bin/env python3
"""
Service Status Check for AI Beer Crawl App
"""
import requests
import redis
import time

def check_services():
    print("🍺 AI BEER CRAWL APP - SERVICE STATUS CHECK")
    print("=" * 50)
    
    # Check main Flask app (port 5000)
    print("\n📱 Main Flask Application (Port 5000)")
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {data.get('status', 'Unknown')}")
            print(f"   🕐 Timestamp: {data.get('timestamp', 'Unknown')}")
            print(f"   📦 Version: {data.get('version', 'Unknown')}")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Check admin dashboard (port 5002)
    print("\n🎛️ Admin Dashboard (Port 5002)")
    try:
        response = requests.get("http://localhost:5002/api/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Connected to database")
            print(f"   👥 Total users: {data.get('total_users', 0)}")
            print(f"   🍻 Total crawls: {data.get('total_crawls', 0)}")
            print(f"   🔗 Redis clients: {data.get('redis_connected_clients', 0)}")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Check Redis
    print("\n🗄️ Redis Database (Port 6379)")
    try:
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        client.ping()
        info = client.info()
        print(f"   ✅ Connected")
        print(f"   💾 Memory used: {info.get('used_memory_human', 'N/A')}")
        print(f"   🔢 Total commands: {info.get('total_commands_processed', 0)}")
        print(f"   👥 Connected clients: {info.get('connected_clients', 0)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Check Celery worker
    print("\n⚙️ Celery Worker Status")
    try:
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        celery_keys = client.keys('celery*')
        if celery_keys:
            print(f"   ✅ Celery queues active")
            print(f"   📋 Queue keys: {len(celery_keys)}")
        else:
            print("   ⚠️ No Celery queues found")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🌐 Access URLs:")
    print("   Main App: http://localhost:5000")
    print("   Admin Dashboard: http://localhost:5002")
    print("   Health Check: http://localhost:5000/health")
    print("   API Docs: http://localhost:5000/api")
    print("=" * 50)

if __name__ == "__main__":
    check_services()
