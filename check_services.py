#!/usr/bin/env python3
"""
Check status of all AI Beer Crawl services and test bot functionality
"""
import requests
import subprocess
import json
import os
import time
from datetime import datetime

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

def test_webhook_endpoint(webhook_url):
    """Test the webhook endpoint with a sample message"""
    test_data = {
        "typeWebhook": "incomingMessageReceived",
        "instanceData": {
            "idInstance": 7105273198,
            "wid": "66955124860@c.us"
        },
        "messageData": {
            "typeMessage": "textMessage",
            "textMessageData": {
                "textMessage": "test bot response"
            }
        },
        "senderData": {
            "chatId": "66955124860@c.us",
            "sender": "66955124860@c.us"
        }
    }
    
    try:
        response = requests.post(
            f"{webhook_url}/webhook/whatsapp",
            json=test_data,
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ Webhook test: SUCCESS")
            return True
        else:
            print(f"❌ Webhook test: FAILED ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Webhook test: ERROR ({e})")
        return False

if __name__ == "__main__":
    print("🍺 AI Beer Crawl - Comprehensive Status Check")
    print("=" * 60)
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check web services
    print("🌐 Web Services:")
    flask_ok = check_service('http://localhost:5000/health', 'Flask App')
    admin_ok = check_service('http://localhost:5002/api/stats', 'Admin Dashboard')
    flower_ok = check_service('http://localhost:5555', 'Flower Monitor')
    print()
    
    # Check processes
    print("⚙️ Background Processes:")
    redis_ok = check_process('redis-server')
    celery_ok = check_process('celery.*worker')
    beat_ok = check_process('celery.*beat')
    ngrok_ok = check_process('ngrok')
    print()
    
    # Check ngrok URL and webhook
    print("🌐 Ngrok & Webhook:")
    ngrok_url = get_ngrok_url()
    if ngrok_url:
        print(f"✅ ngrok URL: {ngrok_url}")
        print(f"🔔 Webhook: {ngrok_url}/webhook/whatsapp")
        webhook_ok = test_webhook_endpoint(ngrok_url)
    else:
        print("❌ ngrok URL: NOT AVAILABLE")
        webhook_ok = False
    print()
    
    # Overall status
    all_services = [flask_ok, admin_ok, redis_ok, celery_ok, beat_ok, ngrok_ok, webhook_ok]
    working_services = sum(all_services)
    total_services = len(all_services)
    
    if working_services == total_services:
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print("✅ Your AI Beer Crawl bot is fully functional!")
    else:
        print(f"📊 Service Health: {working_services}/{total_services} services running")
    
    if ngrok_url:
        print(f"\n📱 Bot URL: {ngrok_url}/webhook/whatsapp")
        print("📋 Management: http://localhost:5002")
