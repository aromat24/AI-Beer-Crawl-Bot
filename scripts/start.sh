#!/bin/bash
# Enhanced Start Script for AI Beer Crawl App with ngrok tunneling

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🍺 Starting AI Beer Crawl Services...${NC}"

# Create tmp directory for PIDs
mkdir -p tmp

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}⏳ Waiting for $service_name to be ready...${NC}"
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $service_name is ready${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    echo -e "${RED}✗ $service_name failed to start after $max_attempts seconds${NC}"
    return 1
}

# 1. Check and start Redis
echo -e "${BLUE}🔴 Checking Redis...${NC}"
if ! pgrep -x "redis-server" > /dev/null; then
    echo -e "${YELLOW}Starting Redis server...${NC}"
    redis-server --daemonize yes
    sleep 2
fi

if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}✗ Redis failed to start${NC}"
    exit 1
fi

# 2. Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development
export PYTHONPATH=/workspaces/Beer_Crawl:$PYTHONPATH

# Check for .env file and create if missing
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << EOF
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production

# Database
DATABASE_URL=sqlite:///database/app.db

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Green API Configuration (UPDATE THESE VALUES)
GREEN_API_INSTANCE_ID=7105273198
GREEN_API_TOKEN=b8ed3b46b6c046e0a87997ccbfffe38eb7932e1730b747848d
GREEN_API_URL=https://7105.api.greenapi.com
WHATSAPP_PHONE_NUMBER=+66955124860

# WhatsApp Configuration
WHATSAPP_VERIFY_TOKEN=test_verify_token_12345

# Webhook Configuration
WEBHOOK_URL=will_be_updated_by_ngrok
EOF
    echo -e "${GREEN}✓ Created .env file with default values${NC}"
    echo -e "${YELLOW}⚠️  Please update Green API credentials in .env file${NC}"
fi

# 3. Kill any existing services
echo -e "${BLUE}🧹 Cleaning up existing services...${NC}"
pkill -f "python.*app.py" 2>/dev/null
pkill -f "python.*admin_web.py" 2>/dev/null
pkill -f "celery.*worker" 2>/dev/null
pkill -f "celery.*beat" 2>/dev/null
pkill -f "ngrok.*http" 2>/dev/null
sleep 2

# 4. Start Flask application
echo -e "${BLUE}🐍 Starting Flask application...${NC}"
nohup python3 app.py > logs/flask.log 2>&1 &
FLASK_PID=$!
echo $FLASK_PID > tmp/flask.pid

if wait_for_service "http://localhost:5000/health" "Flask App"; then
    echo -e "${GREEN}✓ Flask application is running (PID: $FLASK_PID)${NC}"
else
    echo -e "${RED}✗ Flask application failed to start${NC}"
    kill $FLASK_PID 2>/dev/null
    exit 1
fi

# 5. Start Admin Dashboard
echo -e "${BLUE}📊 Starting Admin Web Dashboard...${NC}"
nohup python3 admin_web.py > logs/admin.log 2>&1 &
ADMIN_PID=$!
echo $ADMIN_PID > tmp/admin.pid

if wait_for_service "http://localhost:5002/api/stats" "Admin Dashboard"; then
    echo -e "${GREEN}✓ Admin Dashboard is running (PID: $ADMIN_PID)${NC}"
else
    echo -e "${RED}✗ Admin Dashboard failed to start${NC}"
    kill $ADMIN_PID 2>/dev/null
fi

# 6. Start ngrok tunnel
echo -e "${BLUE}🌐 Starting ngrok tunnel...${NC}"
nohup ngrok http 5000 --log stdout > logs/ngrok.log 2>&1 &
NGROK_PID=$!
echo $NGROK_PID > tmp/ngrok.pid

# Wait for ngrok to establish tunnel
sleep 5

# Get ngrok public URL
NGROK_URL=""
for i in {1..10}; do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[a-zA-Z0-9.-]*\.ngrok\.io' | head -1)
    if [ ! -z "$NGROK_URL" ]; then
        break
    fi
    sleep 1
done

if [ ! -z "$NGROK_URL" ]; then
    echo -e "${GREEN}✓ ngrok tunnel established: $NGROK_URL${NC}"
    
    # Update webhook URL in environment
    sed -i "s|WEBHOOK_URL=.*|WEBHOOK_URL=${NGROK_URL}|" .env
    
    # Create webhook update script
    cat > update_webhook.py << 'EOF'
#!/usr/bin/env python3
"""
Update Green API webhook URL with current ngrok tunnel
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def update_webhook():
    instance_id = os.getenv('GREEN_API_INSTANCE_ID')
    token = os.getenv('GREEN_API_TOKEN')
    webhook_url = os.getenv('WEBHOOK_URL')
    
    if not all([instance_id, token, webhook_url]):
        print("❌ Missing required environment variables")
        return False
    
    api_url = f"https://7105.api.greenapi.com/waInstance{instance_id}/setSettings/{token}"
    
    settings = {
        "webhookUrl": f"{webhook_url}/webhook/whatsapp",
        "webhookUrlToken": os.getenv('WHATSAPP_VERIFY_TOKEN', 'test_verify_token_12345'),
        "getSettings": True,
        "sendMessages": True,
        "receiveNotifications": True
    }
    
    try:
        response = requests.post(api_url, json=settings)
        if response.status_code == 200:
            print(f"✅ Webhook updated successfully: {webhook_url}/webhook/whatsapp")
            return True
        else:
            print(f"❌ Failed to update webhook: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error updating webhook: {e}")
        return False

if __name__ == "__main__":
    update_webhook()
EOF
    
    # Run webhook update
    echo -e "${YELLOW}🔄 Updating Green API webhook...${NC}"
    python3 update_webhook.py
    
else
    echo -e "${RED}✗ Failed to get ngrok URL${NC}"
    kill $NGROK_PID 2>/dev/null
fi

# 7. Start Celery worker
echo -e "${BLUE}⚙️ Starting Celery worker...${NC}"
nohup celery -A src.tasks.celery_tasks.celery worker --loglevel=info --concurrency=2 > logs/celery.log 2>&1 &
CELERY_PID=$!
echo $CELERY_PID > tmp/celery.pid
sleep 2

# 8. Start Celery beat scheduler
echo -e "${BLUE}⏰ Starting Celery beat scheduler...${NC}"
nohup celery -A src.tasks.celery_tasks.celery beat --loglevel=info > logs/beat.log 2>&1 &
BEAT_PID=$!
echo $BEAT_PID > tmp/beat.pid
sleep 2

# 9. Start Flower monitoring (optional)
echo -e "${BLUE}🌸 Starting Flower monitoring...${NC}"
nohup celery -A src.tasks.celery_tasks.celery flower --port=5555 > logs/flower.log 2>&1 &
FLOWER_PID=$!
echo $FLOWER_PID > tmp/flower.pid

# 10. Final status check
echo -e "\n${GREEN}🎉 All services started successfully!${NC}"
echo -e "${YELLOW}=== Service Status ===${NC}"
echo -e "  🐍 Flask App: http://localhost:5000 (PID: $FLASK_PID)"
echo -e "  📊 Admin Dashboard: http://localhost:5002 (PID: $ADMIN_PID)"
echo -e "  🌐 Public URL: $NGROK_URL"
echo -e "  🔔 Webhook: $NGROK_URL/webhook/whatsapp"
echo -e "  ⚙️ Celery Worker: PID $CELERY_PID"
echo -e "  ⏰ Celery Beat: PID $BEAT_PID"
echo -e "  🌸 Flower Monitor: http://localhost:5555 (PID: $FLOWER_PID)"
echo -e "  🔴 Redis: $(pgrep -x redis-server)"

echo -e "\n${YELLOW}=== Important URLs ===${NC}"
echo -e "  Health Check: http://localhost:5000/health"
echo -e "  Admin Dashboard: http://localhost:5002"
echo -e "  Flower Monitoring: http://localhost:5555"
echo -e "  ngrok Web Interface: http://localhost:4040"

echo -e "\n${YELLOW}=== Logs ===${NC}"
echo -e "  Flask: tail -f logs/flask.log"
echo -e "  Admin: tail -f logs/admin.log"
echo -e "  Celery: tail -f logs/celery.log"
echo -e "  ngrok: tail -f logs/ngrok.log"

echo -e "\n${YELLOW}⚠️  To stop all services, run: ./scripts/stop.sh${NC}"

# Create service status check script
cat > check_services.py << 'EOF'
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
EOF

chmod +x check_services.py
chmod +x update_webhook.py

echo -e "\n${GREEN}✨ Setup complete! Use ./check_services.py to monitor services.${NC}"
