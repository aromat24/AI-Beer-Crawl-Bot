# Celery Setup Guide for AI Beer Crawl App

This guide will walk you through setting up Celery for background task processing in your AI Beer Crawl application. This is an alternative to using n8n for automation and provides more control within your Python environment.

## Prerequisites

Before you begin, ensure you have:

1.  **Redis Server**: Celery uses a message broker to communicate between the Flask application and the Celery workers. Redis is a popular and easy-to-use choice for this. If you don't have Redis installed, you can typically install it via your system's package manager (e.g., `sudo apt-get install redis-server` on Ubuntu, or use Docker).
2.  **Python Environment**: Your Flask backend should already have a virtual environment set up.

## 1. Install Celery and Redis Dependencies

First, you need to install the necessary Python packages within your backend's virtual environment.

1.  Open a new integrated terminal in VS Code.
2.  Navigate to your backend directory:
    ```bash
    cd ai_beer_crawl_app/backend
    ```
3.  Activate your virtual environment:
    ```bash
    source venv/bin/activate
    ```
4.  Install Celery and the Redis client:
    ```bash
    pip install celery redis
    ```

## 2. Configure Celery in Flask Application

Ensure your Flask application (`flask_celery_implementation.py` or your `main.py` if you integrated it there) is correctly configured for Celery. The `flask_celery_implementation.py` file I provided already includes the necessary configuration:

```python
# Flask app configuration
app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"
app.config["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
app.config["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"

# Celery configuration
celery = Celery(app.name, broker=app.config["CELERY_BROKER_URL"])
celery.conf.update(app.config)
```

**Important**: Make sure your `CELERY_BROKER_URL` points to your running Redis instance. `redis://localhost:6379/0` is the default.

## 3. Set Environment Variables

Your `flask_celery_implementation.py` uses environment variables for WhatsApp API credentials. You need to set these before running the application and Celery workers.

```bash
export WHATSAPP_TOKEN="your_whatsapp_token"
export WHATSAPP_PHONE_ID="your_phone_number_id"
export WHATSAPP_VERIFY_TOKEN="your_verify_token"
```

Replace `your_whatsapp_token`, `your_phone_number_id`, and `your_verify_token` with your actual WhatsApp Business API credentials.

## 4. Start Redis Server

Celery requires a running Redis server. If you installed Redis, start it:

```bash
redis-server
```

If you are using Docker, you might run a Redis container:

```bash
docker run --name some-redis -p 6379:6379 -d redis
```

## 5. Start Celery Worker

Open a **new integrated terminal** in VS Code (you'll need a separate terminal for the Flask app, Celery worker, and Celery beat).

1.  Navigate to your backend directory:
    ```bash
    cd ai_beer_crawl_app/backend
    ```
2.  Activate your virtual environment:
    ```bash
    source venv/bin/activate
    ```
3.  Start the Celery worker. This command tells Celery to look for tasks in `flask_celery_implementation.py`:
    ```bash
    celery -A flask_celery_implementation.celery worker --loglevel=info
    ```
    You should see output indicating the worker has started and is ready to process tasks.

## 6. Start Celery Beat (for Scheduled Tasks)

Celery Beat is a scheduler that periodically sends tasks to the Celery worker. This is used for tasks like the daily cleanup.

Open yet **another new integrated terminal** in VS Code.

1.  Navigate to your backend directory:
    ```bash
    cd ai_beer_crawl_app/backend
    ```
2.  Activate your virtual environment:
    ```bash
    source venv/bin/activate
    ```
3.  Start Celery Beat:
    ```bash
    celery -A flask_celery_implementation.celery beat --loglevel=info
    ```
    You should see output indicating Celery Beat has started and is scheduling tasks.

## 7. Run the Flask Application

Finally, run your Flask application. This is the part that receives webhooks and dispatches tasks to Celery.

Open a **fourth integrated terminal** in VS Code (or use the one where you installed dependencies).

1.  Navigate to your backend directory:
    ```bash
    cd ai_beer_crawl_app/backend
    ```
2.  Activate your virtual environment:
    ```bash
    source venv/bin/activate
    ```
3.  Run the Flask application:
    ```bash
    python flask_celery_implementation.py
    ```
    The Flask app will run on `http://localhost:5001` (note the different port from the previous backend).

## 8. Configure WhatsApp Webhook

Once your Flask application is running, you need to configure your WhatsApp Business API webhook to point to your Flask app's webhook endpoint. This will likely require a public URL, which you can get using a service like ngrok if you're developing locally.

Set your WhatsApp webhook URL to:

`https://your-public-domain.com/webhook/whatsapp`

And ensure the verify token matches the `WHATSAPP_VERIFY_TOKEN` you set as an environment variable.

By following these steps, you will have the Flask backend, Celery worker, and Celery Beat running, allowing your application to handle WhatsApp messages and background tasks efficiently.

