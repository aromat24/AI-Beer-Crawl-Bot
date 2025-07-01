#!/bin/bash
# Start all services for AI Beer Crawl App

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting AI Beer Crawl Services...${NC}"

# Check if Redis is running
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

# Set environment
export FLASK_APP=app.py
export PYTHONPATH=/workspaces/Beer_Crawl:$PYTHONPATH

echo -e "${YELLOW}Starting Flask application...${NC}"
python3 app.py &
FLASK_PID=$!

sleep 3

# Test if Flask is running
if curl -s http://localhost:5000/health > /dev/null; then
    echo -e "${GREEN}✓ Flask application is running (PID: $FLASK_PID)${NC}"
else
    echo -e "${RED}✗ Flask application failed to start${NC}"
    kill $FLASK_PID 2>/dev/null
    exit 1
fi

echo -e "${YELLOW}Starting Admin Web Dashboard...${NC}"
python3 admin_web.py &
ADMIN_PID=$!

sleep 3

# Test if Admin Dashboard is running
if curl -s http://localhost:5002/api/stats > /dev/null; then
    echo -e "${GREEN}✓ Admin Dashboard is running (PID: $ADMIN_PID)${NC}"
else
    echo -e "${RED}✗ Admin Dashboard failed to start${NC}"
    kill $ADMIN_PID 2>/dev/null
fi

echo -e "${YELLOW}Starting Celery worker...${NC}"
celery -A src.tasks.celery_tasks.celery worker --loglevel=info --detach
sleep 1
CELERY_PID=$(pgrep -f "celery.*worker")

echo -e "${YELLOW}Starting Celery beat scheduler...${NC}"
celery -A src.tasks.celery_tasks.celery beat --loglevel=info --detach
sleep 1
BEAT_PID=$(pgrep -f "celery.*beat")

sleep 2

echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${YELLOW}Services running:${NC}"
echo -e "  Flask App: http://localhost:5000 (PID: $FLASK_PID)"
echo -e "  Admin Dashboard: http://localhost:5002 (PID: $ADMIN_PID)"
echo -e "  Health Check: http://localhost:5000/health"
echo -e "  Celery Worker: PID $CELERY_PID"
echo -e "  Celery Beat: PID $BEAT_PID"
echo -e "  Redis: $(pgrep -x redis-server)"

echo -e "${YELLOW}To stop all services, run: ./scripts/stop.sh${NC}"
echo -e "${YELLOW}To monitor Celery tasks, install Flower and run:${NC}"
echo -e "  celery -A src.tasks.celery_tasks.celery flower"

# Save PIDs for stop script
mkdir -p tmp
echo $FLASK_PID > tmp/flask.pid
echo $ADMIN_PID > tmp/admin.pid
echo $CELERY_PID > tmp/celery.pid
echo $BEAT_PID > tmp/beat.pid
