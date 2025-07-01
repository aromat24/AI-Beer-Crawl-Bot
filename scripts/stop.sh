#!/bin/bash
# Stop all services for AI Beer Crawl App

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping AI Beer Crawl Services...${NC}"

# Stop Flask app
if [ -f tmp/flask.pid ]; then
    FLASK_PID=$(cat tmp/flask.pid)
    if kill $FLASK_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Flask application stopped${NC}"
    else
        echo -e "${YELLOW}Flask process not running or already stopped${NC}"
    fi
    rm -f tmp/flask.pid
fi

# Stop Admin Dashboard
if [ -f tmp/admin.pid ]; then
    ADMIN_PID=$(cat tmp/admin.pid)
    if kill $ADMIN_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Admin Dashboard stopped${NC}"
    else
        echo -e "${YELLOW}Admin Dashboard not running or already stopped${NC}"
    fi
    rm -f tmp/admin.pid
fi

# Stop Celery worker
if [ -f tmp/celery.pid ]; then
    CELERY_PID=$(cat tmp/celery.pid)
    if kill $CELERY_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Celery worker stopped${NC}"
    else
        echo -e "${YELLOW}Celery worker not running or already stopped${NC}"
    fi
    rm -f tmp/celery.pid
fi

# Stop Celery beat
if [ -f tmp/beat.pid ]; then
    BEAT_PID=$(cat tmp/beat.pid)
    if kill $BEAT_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Celery beat stopped${NC}"
    else
        echo -e "${YELLOW}Celery beat not running or already stopped${NC}"
    fi
    rm -f tmp/beat.pid
fi

# Kill any remaining celery processes
pkill -f "celery worker" 2>/dev/null && echo -e "${GREEN}✓ Stopped remaining Celery workers${NC}"
pkill -f "celery beat" 2>/dev/null && echo -e "${GREEN}✓ Stopped remaining Celery beat processes${NC}"

# Kill any remaining Flask processes
pkill -f "python.*app.py" 2>/dev/null && echo -e "${GREEN}✓ Stopped remaining Flask app processes${NC}"
pkill -f "python.*admin_web.py" 2>/dev/null && echo -e "${GREEN}✓ Stopped remaining Admin web processes${NC}"

# Additional cleanup - kill by port if needed
echo -e "${YELLOW}Checking for processes on required ports...${NC}"

# Check port 5000 (Flask app)
FLASK_PORT_PID=$(lsof -ti:5000 2>/dev/null)
if [ ! -z "$FLASK_PORT_PID" ]; then
    kill -9 $FLASK_PORT_PID 2>/dev/null && echo -e "${GREEN}✓ Killed process on port 5000${NC}"
fi

# Check port 5002 (Admin dashboard)
ADMIN_PORT_PID=$(lsof -ti:5002 2>/dev/null)
if [ ! -z "$ADMIN_PORT_PID" ]; then
    kill -9 $ADMIN_PORT_PID 2>/dev/null && echo -e "${GREEN}✓ Killed process on port 5002${NC}"
fi

# Wait a moment for processes to clean up
sleep 2

# Final verification
echo -e "${YELLOW}Verifying all services stopped...${NC}"
if lsof -ti:5000 >/dev/null 2>&1; then
    echo -e "${RED}✗ Warning: Something still running on port 5000${NC}"
else
    echo -e "${GREEN}✓ Port 5000 is free${NC}"
fi

if lsof -ti:5002 >/dev/null 2>&1; then
    echo -e "${RED}✗ Warning: Something still running on port 5002${NC}"
else
    echo -e "${GREEN}✓ Port 5002 is free${NC}"
fi

# Optionally stop Redis (uncomment if you want to stop Redis too)
# pkill -x redis-server && echo -e "${GREEN}✓ Redis stopped${NC}"

echo -e "${GREEN}All services stopped successfully!${NC}"
