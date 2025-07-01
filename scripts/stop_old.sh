#!/bin/bash
# Enhanced Stop Script for AI Beer Crawl App

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}🛑 Stopping AI Beer Crawl Services...${NC}"

# Function to stop process by PID file
stop_by_pid() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}Stopping $service_name (PID: $pid)...${NC}"
            kill "$pid"
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${RED}Force killing $service_name...${NC}"
                kill -9 "$pid"
            fi
            echo -e "${GREEN}✓ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}$service_name was not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}No PID file found for $service_name${NC}"
    fi
}

# Function to stop processes by pattern
stop_by_pattern() {
    local service_name=$1
    local pattern=$2
    
    local pids=$(pgrep -f "$pattern")
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}Stopping $service_name processes...${NC}"
        pkill -f "$pattern"
        sleep 2
        
        # Force kill if still running
        local remaining=$(pgrep -f "$pattern")
        if [ ! -z "$remaining" ]; then
            echo -e "${RED}Force killing $service_name processes...${NC}"
            pkill -9 -f "$pattern"
        fi
        echo -e "${GREEN}✓ $service_name stopped${NC}"
    else
        echo -e "${YELLOW}$service_name was not running${NC}"
    fi
}

# Stop services using PID files
if [ -d "tmp" ]; then
    stop_by_pid "Flask App" "tmp/flask.pid"
    stop_by_pid "Admin Dashboard" "tmp/admin.pid"
    stop_by_pid "Celery Worker" "tmp/celery.pid"
    stop_by_pid "Celery Beat" "tmp/beat.pid"
    stop_by_pid "ngrok Tunnel" "tmp/ngrok.pid"
    stop_by_pid "Flower Monitor" "tmp/flower.pid"
fi

# Stop any remaining processes by pattern
echo -e "\n${BLUE}🧹 Cleaning up remaining processes...${NC}"
stop_by_pattern "Flask App" "python.*app.py"
stop_by_pattern "Admin Dashboard" "python.*admin_web.py"
stop_by_pattern "Celery Worker" "celery.*worker"
stop_by_pattern "Celery Beat" "celery.*beat"
stop_by_pattern "Flower Monitor" "celery.*flower"
stop_by_pattern "ngrok Tunnel" "ngrok.*http"

# Clear Redis queues
echo -e "\n${BLUE}🗑️ Clearing Redis task queues...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${YELLOW}Clearing Celery queues...${NC}"
    redis-cli FLUSHDB 2>/dev/null || echo -e "${RED}Failed to clear Redis DB 0${NC}"
    
    echo -e "${YELLOW}Clearing deduplication cache...${NC}"
    redis-cli -n 1 FLUSHDB 2>/dev/null || echo -e "${RED}Failed to clear Redis DB 1${NC}"
    
    echo -e "${GREEN}✓ Redis queues cleared${NC}"
else
    echo -e "${YELLOW}Redis not running, skipping queue cleanup${NC}"
fi

echo -e "\n${GREEN}✅ All services stopped successfully!${NC}"
echo -e "${YELLOW}To restart all services, run: ./scripts/start.sh${NC}"
