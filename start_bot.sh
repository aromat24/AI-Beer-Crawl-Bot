#!/bin/bash
# AI Beer Crawl Bot Startup Script
# This script starts all necessary services for the WhatsApp bot

echo "🍺 Starting AI Beer Crawl Bot..."
echo "=================================="

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Starting Redis..."
    sudo service redis-server start
    sleep 2
fi

# Kill any existing processes on ports we need
echo "🧹 Cleaning up existing processes..."
pkill -f "celery worker" > /dev/null 2>&1 || true
pkill -f "python app.py" > /dev/null 2>&1 || true
pkill -f "python admin_web.py" > /dev/null 2>&1 || true
pkill -f "ngrok" > /dev/null 2>&1 || true

# Wait a moment for processes to stop
sleep 2

# Start ngrok in background to expose port 5000
echo "🌐 Starting ngrok tunnel..."
ngrok http 5000 --log stdout > ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to start and get the public URL
echo "⏳ Waiting for ngrok to initialize..."
sleep 5

# Get the ngrok public URL
NGROK_URL=""
for i in {1..10}; do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data.get('tunnels', []):
        if tunnel.get('config', {}).get('addr') == 'http://localhost:5000':
            print(tunnel['public_url'])
            break
except:
    pass
" 2>/dev/null)
    
    if [ ! -z "$NGROK_URL" ]; then
        break
    fi
    echo "   Retrying in 2 seconds..."
    sleep 2
done

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL. Please check ngrok manually."
    exit 1
fi

echo "✅ Ngrok tunnel created: $NGROK_URL"

# Start Celery worker in background
echo "🔄 Starting Celery worker..."
celery -A src.tasks.celery_tasks.celery worker --loglevel=info > celery.log 2>&1 &
CELERY_PID=$!

# Wait for Celery to start
sleep 3

# Start Flask app in background
echo "🚀 Starting Flask application..."
python app.py > flask.log 2>&1 &
FLASK_PID=$!

# Wait for Flask to start
sleep 3

# Start admin dashboard in background
echo "📊 Starting admin web dashboard..."
python admin_web.py > admin.log 2>&1 &
ADMIN_PID=$!

# Wait for admin dashboard to start
sleep 3

# Update Green API webhook URL
echo "🔗 Updating Green API webhook URL..."
WEBHOOK_URL="${NGROK_URL}/webhook/whatsapp"

python3 -c "
import requests
import os
from dotenv import load_dotenv

load_dotenv()

instance_id = os.environ.get('GREEN_API_INSTANCE_ID')
token = os.environ.get('GREEN_API_TOKEN')
base_url = os.environ.get('GREEN_API_URL', 'https://7105.api.greenapi.com')

url = f'{base_url}/waInstance{instance_id}/setSettings/{token}'
data = {'webhookUrl': '${WEBHOOK_URL}'}

try:
    response = requests.post(url, json=data, timeout=10)
    if response.status_code == 200:
        print('✅ Webhook URL updated successfully')
    else:
        print(f'❌ Failed to update webhook URL: {response.status_code}')
        print(response.text)
except Exception as e:
    print(f'❌ Error updating webhook URL: {e}')
"

echo ""
echo "🎉 AI Beer Crawl Bot is now running!"
echo "=================================="
echo "📱 WhatsApp Number: +66955124860"
echo "🌐 Public Webhook URL: $WEBHOOK_URL"
echo "🔍 Flask App: http://localhost:5000"
echo "📊 Admin Dashboard: http://localhost:5002"
echo "� Ngrok Dashboard: http://localhost:4040"
echo ""
echo "📝 Log files:"
echo "   - Celery: celery.log"
echo "   - Flask: flask.log"
echo "   - Admin: admin.log"
echo "   - Ngrok: ngrok.log"
echo ""
echo "⚠️  Keep this terminal open or the bot will stop working!"
echo "   To stop the bot, press Ctrl+C or run: ./stop_bot.sh"
echo ""

# Save PIDs for cleanup
echo "$NGROK_PID $CELERY_PID $FLASK_PID $ADMIN_PID" > .bot_pids

# Wait for user to stop the script
trap 'echo ""; echo "🛑 Stopping bot..."; pkill -P $$; rm -f .bot_pids ngrok.log celery.log flask.log admin.log; echo "✅ Bot stopped."; exit 0' INT

echo "🟢 Bot is running! Send 'join' or 'beer crawl' to +66955124860 to test."
echo "   Press Ctrl+C to stop the bot."

# Keep the script running
while true; do
    sleep 1
done
