#!/usr/bin/env python3
"""
AI Beer Crawl Bot Quick Start
Simple Python script to start all services
"""
import os
import sys
import time
import subprocess
import signal
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BotStarter:
    def __init__(self):
        self.processes = []
        self.ngrok_url = None
    
    def cleanup(self, signum=None, frame=None):
        """Clean up all processes"""
        print("\n🛑 Stopping bot...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # Kill any remaining processes
        os.system("pkill -f 'celery worker' > /dev/null 2>&1 || true")
        os.system("pkill -f 'python app.py' > /dev/null 2>&1 || true")
        os.system("pkill -f 'python admin_web.py' > /dev/null 2>&1 || true")
        os.system("pkill -f 'ngrok' > /dev/null 2>&1 || true")
        
        print("✅ Bot stopped.")
        sys.exit(0)
    
    def start_redis(self):
        """Start or ensure Redis is running"""
        print("🔴 Checking Redis...")
        
        # First check if Redis is already running
        try:
            result = subprocess.run(["redis-cli", "ping"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ Redis is already running")
                return True
        except:
            pass
        
        # Try to start Redis server
        print("🔄 Starting Redis server...")
        try:
            # Try starting Redis as a service (Ubuntu/Debian)
            result = subprocess.run(["sudo", "service", "redis-server", "start"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                time.sleep(2)
                # Verify it's running
                result = subprocess.run(["redis-cli", "ping"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print("✅ Redis started as service")
                    return True
        except:
            pass
        
        # If service start failed, try running redis-server directly
        try:
            print("🔄 Starting Redis server directly...")
            process = subprocess.Popen(
                ["redis-server", "--daemonize", "yes"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(3)
            
            # Verify it's running
            result = subprocess.run(["redis-cli", "ping"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ Redis started directly")
                return True
        except:
            pass
        
        print("❌ Failed to start Redis. Please install Redis or start it manually.")
        return False
    
    def start_ngrok(self):
        """Start ngrok tunnel"""
        print("🌐 Starting ngrok tunnel...")
        
        # Kill existing ngrok
        os.system("pkill -f ngrok > /dev/null 2>&1 || true")
        time.sleep(2)
        
        # Start ngrok
        process = subprocess.Popen(
            ["ngrok", "http", "5000", "--log", "stdout"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(process)
        
        # Wait for ngrok to start
        print("⏳ Waiting for ngrok to initialize...")
        time.sleep(5)
        
        # Get ngrok URL
        for attempt in range(10):
            try:
                response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
                data = response.json()
                
                for tunnel in data.get('tunnels', []):
                    if tunnel.get('config', {}).get('addr') == 'http://localhost:5000':
                        self.ngrok_url = tunnel['public_url']
                        print(f"✅ Ngrok tunnel created: {self.ngrok_url}")
                        return True
                        
            except:
                pass
            
            print(f"   Retrying in 2 seconds... (attempt {attempt + 1}/10)")
            time.sleep(2)
        
        print("❌ Failed to get ngrok URL")
        return False
    
    def start_celery(self):
        """Start Celery worker"""
        print("🔄 Starting Celery worker...")
        
        # Kill existing celery
        os.system("pkill -f 'celery worker' > /dev/null 2>&1 || true")
        time.sleep(2)
        
        process = subprocess.Popen(
            ["celery", "-A", "src.tasks.celery_tasks.celery", "worker", "--loglevel=info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(process)
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ Celery worker started")
            return True
        else:
            print("❌ Failed to start Celery worker")
            return False
    
    def start_admin_dashboard(self):
        """Start admin web dashboard"""
        print("📊 Starting admin web dashboard...")
        
        # Kill existing admin dashboard
        os.system("pkill -f 'python admin_web.py' > /dev/null 2>&1 || true")
        time.sleep(2)
        
        process = subprocess.Popen(
            ["python", "admin_web.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(process)
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ Admin dashboard started on http://localhost:5002")
            return True
        else:
            print("❌ Failed to start admin dashboard")
            return False
    
    def start_flask(self):
        """Start Flask application"""
        print("🚀 Starting Flask application...")
        
        # Kill existing flask
        os.system("pkill -f 'python app.py' > /dev/null 2>&1 || true")
        time.sleep(2)
        
        process = subprocess.Popen(
            ["python", "app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(process)
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ Flask application started")
            return True
        else:
            print("❌ Failed to start Flask application")
            return False
    
    def update_webhook(self):
        """Update Green API webhook URL"""
        if not self.ngrok_url:
            print("❌ No ngrok URL available")
            return False
        
        print("🔗 Updating Green API webhook URL...")
        
        instance_id = os.environ.get('GREEN_API_INSTANCE_ID')
        token = os.environ.get('GREEN_API_TOKEN')
        base_url = os.environ.get('GREEN_API_URL', 'https://7105.api.greenapi.com')
        
        if not instance_id or not token:
            print("❌ Green API credentials not found")
            return False
        
        webhook_url = f"{self.ngrok_url}/webhook/whatsapp"
        url = f"{base_url}/waInstance{instance_id}/setSettings/{token}"
        
        try:
            response = requests.post(url, json={'webhookUrl': webhook_url}, timeout=10)
            if response.status_code == 200:
                print("✅ Webhook URL updated successfully")
                return True
            else:
                print(f"❌ Failed to update webhook URL: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error updating webhook URL: {e}")
            return False
    
    def start(self):
        """Start all services"""
        print("🍺 Starting AI Beer Crawl Bot...")
        print("==================================")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
        # Start Redis first
        if not self.start_redis():
            return False
        
        # Start services
        if not self.start_ngrok():
            return False
        
        if not self.start_celery():
            return False
        
        if not self.start_flask():
            return False
        
        if not self.start_admin_dashboard():
            print("⚠️ Warning: Failed to start admin dashboard")
        
        if not self.update_webhook():
            print("⚠️ Warning: Failed to update webhook URL. You may need to update it manually.")
        
        # Show status
        print("")
        print("🎉 AI Beer Crawl Bot is now running!")
        print("====================================")
        print(f"📱 WhatsApp Number: {os.environ.get('WHATSAPP_PHONE_NUMBER', '+66955124860')}")
        print(f"🌐 Public Webhook URL: {self.ngrok_url}/webhook/whatsapp")
        print("🔍 Flask App: http://localhost:5000")
        print("📊 Admin Dashboard: http://localhost:5002")
        print("📈 Ngrok Dashboard: http://localhost:4040")
        print("")
        print("🟢 Bot is running! Send 'join' or 'beer crawl' to test.")
        print("   Press Ctrl+C to stop the bot.")
        print("")
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()

if __name__ == "__main__":
    starter = BotStarter()
    starter.start()
