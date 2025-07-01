#!/bin/bash
# AI Beer Crawl Bot Stop Script
# This script stops all bot services

echo "🛑 Stopping AI Beer Crawl Bot..."
echo "================================"

# Kill processes if PID file exists
if [ -f .bot_pids ]; then
    echo "📋 Reading process IDs..."
    read NGROK_PID CELERY_PID FLASK_PID ADMIN_PID < .bot_pids
    
    echo "🌐 Stopping ngrok (PID: $NGROK_PID)..."
    kill $NGROK_PID 2>/dev/null || true
    
    echo "🔄 Stopping Celery worker (PID: $CELERY_PID)..."
    kill $CELERY_PID 2>/dev/null || true
    
    echo "🚀 Stopping Flask app (PID: $FLASK_PID)..."
    kill $FLASK_PID 2>/dev/null || true
    
    echo "📊 Stopping admin dashboard (PID: $ADMIN_PID)..."
    kill $ADMIN_PID 2>/dev/null || true
    
    rm -f .bot_pids
fi

# Fallback: kill by process name
echo "🧹 Cleaning up any remaining processes..."
pkill -f "celery worker" > /dev/null 2>&1 || true
pkill -f "python app.py" > /dev/null 2>&1 || true
pkill -f "python admin_web.py" > /dev/null 2>&1 || true
pkill -f "ngrok" > /dev/null 2>&1 || true

# Clean up log files
echo "🗑️  Cleaning up log files..."
rm -f ngrok.log celery.log flask.log admin.log

echo "✅ AI Beer Crawl Bot stopped successfully!"
