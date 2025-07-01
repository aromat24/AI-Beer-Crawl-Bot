#!/bin/bash
# Quick verification that all services are running correctly

echo "🍺 AI Beer Crawl App - Service Verification"
echo "=========================================="

# Test Flask App
echo -n "📱 Flask App (Port 5000): "
if curl -s http://localhost:5000/health | grep -q "healthy"; then
    echo "✅ RUNNING"
else
    echo "❌ FAILED"
fi

# Test Admin Dashboard
echo -n "🎛️ Admin Dashboard (Port 5002): "
if curl -s http://localhost:5002/api/stats | grep -q "total_users"; then
    echo "✅ RUNNING"
else
    echo "❌ FAILED"
fi

# Test Redis
echo -n "🗄️ Redis (Port 6379): "
if redis-cli ping | grep -q "PONG"; then
    echo "✅ RUNNING"
else
    echo "❌ FAILED"
fi

# Test Celery Worker
echo -n "⚙️ Celery Worker: "
if pgrep -f "celery.*worker" > /dev/null; then
    echo "✅ RUNNING"
else
    echo "❌ FAILED"
fi

# Test Celery Beat
echo -n "📅 Celery Beat: "
if pgrep -f "celery.*beat" > /dev/null; then
    echo "✅ RUNNING"
else
    echo "❌ FAILED"
fi

echo ""
echo "🌐 Access URLs:"
echo "   Main App: http://localhost:5000"
echo "   Admin Dashboard: http://localhost:5002"
echo "   Health Check: http://localhost:5000/health"
echo "   API Docs: http://localhost:5000/api"
echo ""
echo "🛠️ Management:"
echo "   Start all: ./scripts/start.sh"
echo "   Stop all:  ./scripts/stop.sh"
echo "   Verify:    ./verify.sh"
