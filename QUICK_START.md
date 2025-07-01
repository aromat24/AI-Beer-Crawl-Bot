# 🍺 AI Beer Crawl Bot - Quick Start Guide

## 🚀 Starting the Bot (Easy Way)

### Option 1: Bash Script (Recommended)
```bash
./start_bot.sh
```

### Option 2: Python Script
```bash
python start_bot.py
```

### Option 3: Manual Start
```bash
# 1. Start ngrok
ngrok http 5000 &

# 2. Start Celery worker
celery -A src.tasks.celery_tasks.celery worker --loglevel=info &

# 3. Start Flask app
python app.py &

# 4. Update webhook URL manually in Green API dashboard
```

## 🛑 Stopping the Bot

### Using the stop script:
```bash
./stop_bot.sh
```

### Or press `Ctrl+C` in the terminal running the start script

## 📋 What the Scripts Do

The startup scripts automatically:
1. ✅ Check if Redis is running
2. ✅ Clean up any existing processes
3. ✅ Start ngrok tunnel for public access
4. ✅ Start Celery worker for background tasks
5. ✅ Start Flask application for webhooks
6. ✅ Update Green API webhook URL automatically
7. ✅ Show you all the important URLs and info

## 🔍 Monitoring

Once started, you can monitor:
- **Bot Status**: Check the terminal output
- **Ngrok Dashboard**: http://localhost:4040
- **Flask App**: http://localhost:5000
- **Webhook Debugger**: http://localhost:5001 (if running separately)

## 📱 Testing

Send any of these messages to **+66955124860**:
- "join"
- "beer crawl" 
- "I want to join a beer crawl"

You should get automated responses about finding beer crawl groups!

## 🔧 Troubleshooting

### If the bot doesn't respond:
1. Check if all services are running (you'll see them in the terminal)
2. Check the ngrok URL is accessible
3. Verify the Green API webhook URL is set correctly
4. Check the Celery worker logs for errors

### If ngrok fails:
- Make sure you have ngrok installed: `npm install -g ngrok` or download from ngrok.com
- Sign up for a free ngrok account if needed

### If Redis fails:
- Install Redis: `sudo apt install redis-server` (Linux) or `brew install redis` (Mac)
- Start Redis: `sudo service redis-server start` or `redis-server`

## 📁 Log Files

When running, the scripts create these log files:
- `celery.log` - Celery worker output
- `flask.log` - Flask application output  
- `ngrok.log` - Ngrok tunnel output

## ⚙️ Environment Variables

Make sure your `.env` file has:
```
GREEN_API_INSTANCE_ID=7105273198
GREEN_API_TOKEN=b8ed3b46b6c046e0a87997ccbfffe38eb7932e1730b747848d
WHATSAPP_PHONE_NUMBER=+66955124860
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Group Size Configuration (for testing)
MIN_GROUP_SIZE=2
MAX_GROUP_SIZE=5

# Message Deduplication & Rate Limiting
MESSAGE_COOLDOWN=30        # Duplicate message cooldown (seconds)
USER_COOLDOWN=10          # User cooldown between any messages (seconds)
RATE_LIMIT_WINDOW=300     # Rate limit time window (seconds)
RATE_LIMIT_MAX=5          # Max messages per time window
```

> **Note**: The bot is currently configured for testing with 2-person groups instead of the default 5. Change `MIN_GROUP_SIZE=3` and update the React frontend to use production settings.

## 🛡️ Anti-Spam Features

The bot now includes built-in protection against message spam:

- **Duplicate Detection**: Ignores identical messages within 30 seconds
- **User Cooldown**: 10-second cooldown between any messages from the same user
- **Rate Limiting**: Max 5 messages per 5-minute window per user
- **Auto-Response**: Users get warned when they hit rate limits

### Clear Spam Protection (for testing):
```bash
# Clear deduplication for a specific user
python -c "
import sys; sys.path.insert(0, 'src')
from tasks.celery_tasks import clear_user_deduplication
clear_user_deduplication('+66955124860')
"

# Or clear all deduplication data
redis-cli -n 1 FLUSHDB
```

## 🎯 Next Steps

1. **Test the bot** by sending messages to +66955124860
2. **Customize responses** in `src/tasks/celery_tasks.py`
3. **Add more features** like group management, bar recommendations, etc.
4. **Deploy to production** using a proper server instead of ngrok

---

**Happy Beer Crawling! 🍺🚶‍♂️🚶‍♀️**
