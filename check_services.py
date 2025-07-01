#!/usr/bin/env python3
"""
Check status of all AI Beer Crawl services
"""
import requests
import subprocess
import json
import os

def check_service(url, name):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name}: RUNNING")
            return True
        else:
            print(f"❌ {name}: ERROR ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ {name}: OFFLINE ({e})")
        return False

def check_process(name):
    try:
        result = subprocess.run(['pgrep', '-f', name], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"✅ {name}: RUNNING ({len(pids)} processes)")
            return True
        else:
            print(f"❌ {name}: NOT RUNNING")
            return False
    except Exception as e:
        print(f"❌ {name}: ERROR ({e})")
        return False

def get_ngrok_url():
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        if response.status_code == 200:
            data = response.json()
            for tunnel in data.get('tunnels', []):
                if tunnel.get('proto') == 'https':
                    return tunnel.get('public_url')
    except:
        pass
    return None

if __name__ == "__main__":
    print("🍺 AI Beer Crawl - Service Status Check\n")
    
    # Check web services
    check_service('http://localhost:5000/health', 'Flask App')
    check_service('http://localhost:5002/api/stats', 'Admin Dashboard')
    check_service('http://localhost:5555', 'Flower Monitor')
    
    # Check processes
    check_process('redis-server')
    check_process('celery.*worker')
    check_process('celery.*beat')
    check_process('ngrok')
    
    # Check ngrok URL
    ngrok_url = get_ngrok_url()
    if ngrok_url:
        print(f"🌐 ngrok URL: {ngrok_url}")
        print(f"🔔 Webhook: {ngrok_url}/webhook/whatsapp")
    else:
        print("❌ ngrok URL: NOT AVAILABLE")
    
    print("\n📊 Redis Status:")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis: CONNECTED")
        
        # Check Redis databases
        for db in [0, 1, 2]:
            r_db = redis.Redis(host='localhost', port=6379, db=db, decode_responses=True)
            keys = len(r_db.keys('*'))
            print(f"  📊 DB {db}: {keys} keys")
    except Exception as e:
        print(f"❌ Redis: ERROR ({e})")
