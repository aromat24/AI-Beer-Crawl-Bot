#!/bin/bash
# Enhanced Stop Script for AI Beer Crawl App with locked ports

# Load port configuration
source "$(dirname "$0")/ports.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}🛑 Stopping AI Beer Crawl Services...${NC}"

# Function to stop service by PID file
stop_service_by_pid() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}Stopping $service_name (PID: $pid)...${NC}"
            kill "$pid"
            sleep 2
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${YELLOW}Force stopping $service_name...${NC}"
                kill -9 "$pid" 2>/dev/null
            fi
            
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${RED}✗ Failed to stop $service_name${NC}"
            else
                echo -e "${GREEN}✓ $service_name stopped${NC}"
            fi
        else
            echo -e "${YELLOW}$service_name was not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}No PID file found for $service_name${NC}"
    fi
}

# Function to stop service by port
stop_service_by_port() {
    local service_name=$1
    local port=$2
    
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}Stopping $service_name on port $port (PID: $pid)...${NC}"
        kill "$pid" 2>/dev/null
        sleep 2
        
        # Force kill if still running
        pid=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$pid" ]; then
            echo -e "${YELLOW}Force stopping $service_name on port $port...${NC}"
            kill -9 "$pid" 2>/dev/null
        fi
        
        # Check if port is now free
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
            echo -e "${RED}✗ Port $port still in use${NC}"
        else
            echo -e "${GREEN}✓ Port $port is now free${NC}"
        fi
    else
        echo -e "${YELLOW}No process found on port $port${NC}"
    fi
}

# Stop services by PID files first
stop_service_by_pid "Flask App" "tmp/flask.pid"
stop_service_by_pid "Admin Dashboard" "tmp/admin.pid"
stop_service_by_pid "Celery Worker" "tmp/celery.pid"
stop_service_by_pid "Celery Beat" "tmp/beat.pid"
stop_service_by_pid "ngrok Tunnel" "tmp/ngrok.pid"
stop_service_by_pid "Flower Monitor" "tmp/flower.pid"

# Clean up any remaining processes on locked ports
echo -e "${BLUE}🧹 Cleaning up remaining processes...${NC}"
stop_service_by_port "Flask App" $FLASK_PORT
stop_service_by_port "Admin Dashboard" $ADMIN_PORT
stop_service_by_port "Flower Monitor" $FLOWER_PORT
stop_service_by_port "ngrok Web Interface" $NGROK_WEB_PORT

# Clean up by process patterns
echo -e "${BLUE}🧹 Cleaning up remaining processes by pattern...${NC}"

cleanup_processes() {
    local pattern=$1
    local service_name=$2
    
    local pids=$(pgrep -f "$pattern" 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}Stopping $service_name processes...${NC}"
        pkill -f "$pattern" 2>/dev/null
        sleep 2
        
        # Force kill if still running
        pids=$(pgrep -f "$pattern" 2>/dev/null)
        if [ ! -z "$pids" ]; then
            echo -e "${YELLOW}Force stopping $service_name processes...${NC}"
            pkill -9 -f "$pattern" 2>/dev/null
        fi
        
        # Check if processes are gone
        pids=$(pgrep -f "$pattern" 2>/dev/null)
        if [ -z "$pids" ]; then
            echo -e "${GREEN}✓ $service_name processes stopped${NC}"
        else
            echo -e "${RED}✗ Some $service_name processes still running${NC}"
        fi
    else
        echo -e "${YELLOW}$service_name was not running${NC}"
    fi
}

cleanup_processes "python.*app.py" "Flask App"
cleanup_processes "python.*admin_web.py" "Admin Dashboard"
cleanup_processes "celery.*worker" "Celery Worker"
cleanup_processes "celery.*beat" "Celery Beat"
cleanup_processes "celery.*flower" "Flower Monitor"
cleanup_processes "ngrok.*http" "ngrok Tunnel"

# Clear Redis task queues but keep Redis running
echo -e "${BLUE}🗑️ Clearing Redis task queues...${NC}"
echo -e "${YELLOW}Clearing Celery queues...${NC}"
redis-cli -p $REDIS_PORT -n $REDIS_CELERY_DB FLUSHDB > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Celery queues cleared${NC}"
else
    echo -e "${YELLOW}⚠️ Could not clear Celery queues${NC}"
fi

echo -e "${YELLOW}Clearing deduplication cache...${NC}"
redis-cli -p $REDIS_PORT -n $REDIS_DEDUP_DB FLUSHDB > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Deduplication cache cleared${NC}"
else
    echo -e "${YELLOW}⚠️ Could not clear deduplication cache${NC}"
fi

# Clean up temporary files
echo -e "${BLUE}🗂️ Cleaning up temporary files...${NC}"
rm -f tmp/*.pid
rm -f celerybeat-schedule
echo -e "${GREEN}✓ Temporary files cleaned${NC}"

# Final port check
echo -e "${BLUE}🔍 Final port check...${NC}"
check_final_port() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        echo -e "${RED}⚠️ Port $port ($service_name) still in use${NC}"
        return 1
    else
        echo -e "${GREEN}✓ Port $port ($service_name) is free${NC}"
        return 0
    fi
}

ALL_PORTS_FREE=true
check_final_port $FLASK_PORT "Flask" || ALL_PORTS_FREE=false
check_final_port $ADMIN_PORT "Admin" || ALL_PORTS_FREE=false
check_final_port $FLOWER_PORT "Flower" || ALL_PORTS_FREE=false
check_final_port $NGROK_WEB_PORT "ngrok Web" || ALL_PORTS_FREE=false

# Redis should stay running
if redis-cli -p $REDIS_PORT ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is still running on port $REDIS_PORT (as expected)${NC}"
else
    echo -e "${YELLOW}⚠️ Redis is not running on port $REDIS_PORT${NC}"
fi

echo ""
if [ "$ALL_PORTS_FREE" = true ]; then
    echo -e "${GREEN}✅ All services stopped successfully!${NC}"
    echo -e "${GREEN}🔓 All service ports are now free and available for restart${NC}"
else
    echo -e "${YELLOW}⚠️ Some ports may still be in use. You may need to wait or restart manually.${NC}"
fi

echo -e "${BLUE}📊 Port Status Summary:${NC}"
echo -e "  Flask Port $FLASK_PORT: $(lsof -Pi :$FLASK_PORT -sTCP:LISTEN -t >/dev/null && echo -e "${RED}IN USE${NC}" || echo -e "${GREEN}FREE${NC}")"
echo -e "  Admin Port $ADMIN_PORT: $(lsof -Pi :$ADMIN_PORT -sTCP:LISTEN -t >/dev/null && echo -e "${RED}IN USE${NC}" || echo -e "${GREEN}FREE${NC}")"
echo -e "  Flower Port $FLOWER_PORT: $(lsof -Pi :$FLOWER_PORT -sTCP:LISTEN -t >/dev/null && echo -e "${RED}IN USE${NC}" || echo -e "${GREEN}FREE${NC}")"
echo -e "  Redis Port $REDIS_PORT: $(lsof -Pi :$REDIS_PORT -sTCP:LISTEN -t >/dev/null && echo -e "${GREEN}RUNNING${NC}" || echo -e "${YELLOW}STOPPED${NC}")"
echo -e "  ngrok Web Port $NGROK_WEB_PORT: $(lsof -Pi :$NGROK_WEB_PORT -sTCP:LISTEN -t >/dev/null && echo -e "${RED}IN USE${NC}" || echo -e "${GREEN}FREE${NC}")"

echo ""
echo -e "${GREEN}To restart all services, run: ./scripts/start.sh${NC}"
