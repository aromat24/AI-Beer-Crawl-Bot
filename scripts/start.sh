#!/bin/bash
# Enhanced Start Script for AI Beer Crawl App with locked ports

# Load port configuration
source "$(dirname "$0")/ports.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🍺 Starting AI Beer Crawl Services...${NC}"

# Create necessary directories
mkdir -p tmp logs

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local service_name=$2
    
    if check_port $port; then
        echo -e "${YELLOW}🔄 Port $port is in use by existing $service_name, killing process...${NC}"
        local pid=$(lsof -ti:$port)
        if [ ! -z "$pid" ]; then
            kill -9 $pid 2>/dev/null
            sleep 2
            echo -e "${GREEN}✓ Cleared port $port${NC}"
        fi
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

# Function to get ngrok tunnel URL
get_ngrok_url() {
    local max_attempts=15
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local ngrok_url=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url // empty' 2>/dev/null)
        if [ ! -z "$ngrok_url" ] && [ "$ngrok_url" != "null" ]; then
            echo "$ngrok_url"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    return 1
}

# Function to update Green API webhook
update_green_api_webhook() {
    local ngrok_url=$1
    echo -e "${BLUE}📡 Updating Green API webhook with new ngrok URL: ${ngrok_url}${NC}"
    
    if python3 update_webhook.py "$ngrok_url/webhook/whatsapp"; then
        echo -e "${GREEN}✅ Green API webhook updated successfully to: ${ngrok_url}/webhook/whatsapp${NC}"
    else
        echo -e "${RED}✗ Failed to update Green API webhook${NC}"
    fi
}

# Set environment variables
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
CELERY_BROKER_URL=redis://localhost:$REDIS_PORT/$REDIS_CELERY_DB
CELERY_RESULT_BACKEND=redis://localhost:$REDIS_PORT/$REDIS_CELERY_DB

# Green API Configuration (UPDATE THESE VALUES)
GREEN_API_INSTANCE_ID=7105273198
GREEN_API_TOKEN=b8ed3b46b6c046e0a87997ccbfffe38eb7932e1730b747848d
GREEN_API_URL=https://7105.api.greenapi.com
WHATSAPP_PHONE_NUMBER=+66955124860

# WhatsApp Configuration
WHATSAPP_VERIFY_TOKEN=test_verify_token_12345

# Webhook Configuration
WEBHOOK_URL=will_be_updated_by_ngrok

# API Base URL
API_BASE_URL=http://localhost:$FLASK_PORT
EOF
    echo -e "${GREEN}✓ Created .env file with default values${NC}"
    echo -e "${YELLOW}⚠️  Please update Green API credentials in .env file${NC}"
fi

# Hardlock ports for future use
export FLASK_PORT=5000
export ADMIN_PORT=5002
export FLOWER_PORT=5555
export REDIS_PORT=6379
export NGROK_WEB_PORT=4040

# Ensure ports are locked
if check_port $FLASK_PORT || check_port $ADMIN_PORT || check_port $FLOWER_PORT || check_port $NGROK_WEB_PORT; then
    echo -e "${RED}❌ One or more locked ports are already in use. Please free them before starting services.${NC}"
    exit 1
fi

# 1. Check and start Redis on locked port
echo -e "${BLUE}🔴 Checking Redis...${NC}"
if ! pgrep -x "redis-server" > /dev/null; then
    echo -e "${YELLOW}Starting Redis server on port $REDIS_PORT...${NC}"
    redis-server --port $REDIS_PORT --daemonize yes
    sleep 2
fi

if redis-cli -p $REDIS_PORT ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running on port $REDIS_PORT${NC}"
else
    echo -e "${RED}✗ Redis failed to start${NC}"
    exit 1
fi

# 2. Clean up existing services and lock ports
echo -e "${BLUE}🧹 Cleaning up existing services...${NC}"
kill_port $FLASK_PORT "Flask"
kill_port $ADMIN_PORT "Admin Dashboard"
kill_port $FLOWER_PORT "Flower"
kill_port $NGROK_WEB_PORT "ngrok Web Interface"

# Additional cleanup
pkill -f "python.*app.py" 2>/dev/null
pkill -f "python.*admin_web.py" 2>/dev/null
pkill -f "celery.*worker" 2>/dev/null
pkill -f "celery.*beat" 2>/dev/null
pkill -f "flower.*" 2>/dev/null
pkill -f "ngrok.*http" 2>/dev/null
sleep 2

# 3. Start Flask application on locked port
echo -e "${BLUE}🐍 Starting Flask application...${NC}"
if check_port $FLASK_PORT; then
    echo -e "${RED}❌ Port $FLASK_PORT still in use for Flask${NC}"
    exit 1
fi

export PORT=$FLASK_PORT
nohup python app.py > logs/flask.log 2>&1 &
FLASK_PID=$!
echo $FLASK_PID > tmp/flask.pid

wait_for_service "$FLASK_HEALTH_URL" "Flask App"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Flask application is running (PID: $FLASK_PID, Port: $FLASK_PORT)${NC}"
else
    echo -e "${RED}✗ Flask application failed to start${NC}"
    exit 1
fi

# 4. Start Admin Web Dashboard on locked port
echo -e "${BLUE}📊 Starting Admin Web Dashboard...${NC}"
if check_port $ADMIN_PORT; then
    echo -e "${RED}❌ Port $ADMIN_PORT still in use for Admin Dashboard${NC}"
    exit 1
fi

export ADMIN_PORT=$ADMIN_PORT
nohup python admin_web.py > logs/admin.log 2>&1 &
ADMIN_PID=$!
echo $ADMIN_PID > tmp/admin.pid

wait_for_service "$ADMIN_HEALTH_URL" "Admin Dashboard"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Admin Dashboard is running (PID: $ADMIN_PID, Port: $ADMIN_PORT)${NC}"
else
    echo -e "${RED}✗ Admin Dashboard failed to start${NC}"
    exit 1
fi

# 5. Start ngrok tunnel on locked ports
echo -e "${BLUE}🌐 Starting ngrok tunnel...${NC}"
if check_port $NGROK_WEB_PORT; then
    echo -e "${RED}❌ Port $NGROK_WEB_PORT still in use for ngrok${NC}"
    exit 1
fi

# Set ngrok auth token
export NGROK_AUTHTOKEN="2zDlJZrkjxxw6LnIvdrSJzHVMn4_4f2Uy3sTKyRsRbgZRAPQs"

# Start ngrok tunnel with auth token
nohup ngrok http $FLASK_PORT --authtoken=$NGROK_AUTHTOKEN > logs/ngrok.log 2>&1 &
NGROK_PID=$!
echo $NGROK_PID > tmp/ngrok.pid
sleep 5

# Get ngrok URL
NGROK_URL=$(get_ngrok_url)
if [ $? -eq 0 ] && [ ! -z "$NGROK_URL" ]; then
    echo -e "${GREEN}✓ ngrok tunnel is running (PID: $NGROK_PID)${NC}"
    echo -e "${GREEN}🌐 Public URL: $NGROK_URL${NC}"
    
    # Update webhook URL
    update_green_api_webhook "$NGROK_URL"
else
    echo -e "${RED}✗ Failed to get ngrok URL${NC}"
    NGROK_URL="NOT AVAILABLE"
fi

# 6. Start Celery worker on specific Redis DB
echo -e "${BLUE}⚙️ Starting Celery worker...${NC}"
nohup celery -A src.tasks.celery_tasks.celery worker --loglevel=info --concurrency=3 > logs/celery.log 2>&1 &
CELERY_PID=$!
echo $CELERY_PID > tmp/celery.pid
sleep 3

# 7. Start Celery beat scheduler
echo -e "${BLUE}⏰ Starting Celery beat scheduler...${NC}"
nohup celery -A src.tasks.celery_tasks.celery beat --loglevel=info > logs/celery_beat.log 2>&1 &
BEAT_PID=$!
echo $BEAT_PID > tmp/beat.pid
sleep 2

# 8. Start Flower monitoring on locked port
echo -e "${BLUE}🌸 Starting Flower monitoring...${NC}"
if check_port $FLOWER_PORT; then
    echo -e "${RED}❌ Port $FLOWER_PORT still in use for Flower${NC}"
    exit 1
fi

nohup celery -A src.tasks.celery_tasks.celery flower --port=$FLOWER_PORT > logs/flower.log 2>&1 &
FLOWER_PID=$!
echo $FLOWER_PID > tmp/flower.pid
sleep 3

echo ""
echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo -e "${GREEN}=== Service Status ===${NC}"
echo -e "  🐍 Flask App: http://localhost:$FLASK_PORT (PID: $FLASK_PID)"
echo -e "  📊 Admin Dashboard: http://localhost:$ADMIN_PORT (PID: $ADMIN_PID)"
echo -e "  🌐 Public URL: $NGROK_URL"
echo -e "  🔔 Webhook: $NGROK_URL/webhook/whatsapp"
echo -e "  ⚙️ Celery Worker: PID $CELERY_PID"
echo -e "  ⏰ Celery Beat: PID $BEAT_PID"
echo -e "  🌸 Flower Monitor: http://localhost:$FLOWER_PORT (PID: $FLOWER_PID)"
echo -e "  🔴 Redis: $REDIS_PORT"

echo ""
echo -e "${GREEN}=== Important URLs ===${NC}"
echo -e "  Health Check: http://localhost:$FLASK_PORT/health"
echo -e "  Admin Dashboard: http://localhost:$ADMIN_PORT"
echo -e "  Flower Monitoring: http://localhost:$FLOWER_PORT"
echo -e "  ngrok Web Interface: http://localhost:$NGROK_WEB_PORT"

echo ""
echo -e "${GREEN}=== Port Configuration ===${NC}"
echo -e "  Flask: $FLASK_PORT (locked)"
echo -e "  Admin: $ADMIN_PORT (locked)"
echo -e "  Flower: $FLOWER_PORT (locked)"
echo -e "  Redis: $REDIS_PORT (locked)"
echo -e "  ngrok Web: $NGROK_WEB_PORT (locked)"

echo ""
echo -e "${GREEN}=== Logs ===${NC}"
echo -e "  Flask: tail -f logs/flask.log"
echo -e "  Admin: tail -f logs/admin.log"
echo -e "  Celery: tail -f logs/celery.log"
echo -e "  ngrok: tail -f logs/ngrok.log"
echo -e "  Flower: tail -f logs/flower.log"

echo ""
echo -e "${YELLOW}⚠️  To stop all services, run: ./scripts/stop.sh${NC}"
echo ""
echo -e "${GREEN}✨ Setup complete! Use ./check_services.py to monitor services.${NC}"
