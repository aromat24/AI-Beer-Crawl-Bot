# 🍺 AI Beer Crawl Bot

An intelligent WhatsApp bot that organizes and manages beer crawls with automated group formation, real-time coordination, and comprehensive admin controls.

## 🌟 Features

### 🤖 Bot Capabilities
- **Smart Group Formation**: Automatically creates beer crawl groups based on location and preferences
- **Real-time Coordination**: Manages group progression through multiple bars
- **WhatsApp Integration**: Seamless messaging through Green API
- **Intelligent Responses**: Context-aware conversation handling
- **Deduplication**: Prevents spam and duplicate messages

### 🎛️ Admin Dashboard
- **Real-time Monitoring**: Live stats for users, groups, and system health
- **Database Management**: View and manage users, crawls, and group data
- **Redis Monitoring**: Track cache usage and deduplication entries
- **System Controls**: Start/stop services, clear databases, view logs

### 🏗️ Technical Features
- **Flask Web Framework**: RESTful API architecture
- **Celery Task Processing**: Asynchronous background job handling
- **Redis Caching**: Fast data storage and message deduplication
- **SQLite Database**: Reliable data persistence
- **Docker Support**: Easy deployment and scaling
- **Comprehensive Logging**: Detailed system monitoring
docker-compose up -d

# Production environment
docker-compose -f docker-compose.prod.yml up -d
```

3. The application will be available at:
- Main app: http://localhost:5000
- Health check: http://localhost:5000/health
- Flower (Celery monitoring): http://localhost:5555

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start Redis server:
```bash
redis-server
```

4. Initialize database:
```bash
export FLASK_APP=app.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

5. Start the application:
```bash
# Terminal 1: Main Flask app
python app.py

# Terminal 2: Celery worker
celery -A src.tasks.celery_tasks.celery worker --loglevel=info

# Terminal 3: Celery beat scheduler
celery -A src.tasks.celery_tasks.celery beat --loglevel=info
```

## Features

### Core Functionality
- **User Registration**: WhatsApp-based user signup with preferences
- **Group Formation**: Automatic matching of users into beer crawl groups
- **Dynamic Routing**: Real-time bar progression with GPS coordinates
- **WhatsApp Integration**: Complete conversation flow via WhatsApp Business API
- **Background Processing**: Celery-powered asynchronous task handling

### Technical Features
- **Database Migrations**: Flask-Migrate integration for schema management
- **Containerization**: Multi-stage Docker builds for different environments
- **CI/CD Pipeline**: GitHub Actions for automated testing and deployment
- **Monitoring**: Flower dashboard for Celery task monitoring
- **Health Checks**: Built-in health monitoring endpoints

## API Endpoints

### Beer Crawl API
- `POST /api/beer-crawl/signup` - User registration
- `POST /api/beer-crawl/find-group` - Find or create group
- `POST /api/beer-crawl/groups/{id}/start` - Start group crawl
- `POST /api/beer-crawl/groups/{id}/next-bar` - Progress to next bar
- `GET /api/beer-crawl/groups` - List groups
- `GET /api/beer-crawl/bars` - List bars

### WhatsApp Webhooks
- `POST /webhook/whatsapp` - Receive WhatsApp messages
- `GET /webhook/whatsapp` - Webhook verification

### System
- `GET /health` - Health check endpoint

## Environment Variables

### Required
```bash
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///database/app.db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### WhatsApp Integration
```bash
WHATSAPP_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token
```

### Optional
```bash
FLASK_DEBUG=True
PORT=5000
API_BASE_URL=http://localhost:5000
CORS_ORIGINS=*
```

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-flask

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_beer_crawl_api.py -v
```

### Database Migrations
```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Downgrade (rollback)
flask db downgrade
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8 .

# Type checking
mypy src/
```

## Deployment

### Docker Swarm (Production)
```bash
# Initialize swarm
docker swarm init

# Create secrets
echo "your-secret-key" | docker secret create flask_secret_key -
echo "your-whatsapp-token" | docker secret create whatsapp_token -
echo "your-db-password" | docker secret create db_password -
echo "your-flower-password" | docker secret create flower_password -

# Deploy stack
docker stack deploy -c docker-compose.prod.yml beer-crawl
```

### Kubernetes
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/
```

### Traditional Deployment
```bash
# Install production dependencies
pip install gunicorn supervisor

# Start with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app

# Or use supervisor for process management
supervisord -c supervisor.conf
```

## Monitoring

### Flower Dashboard
Access Celery task monitoring at http://localhost:5555

### Health Checks
- Application health: `GET /health`
- Redis: `redis-cli ping`
- Database: Check via health endpoint

### Logging
- Application logs: `logs/app.log`
- Celery logs: `logs/celery.log`
- Nginx logs: `logs/nginx/`

## Architecture

### Components
1. **Flask Web Application**: Main API server
2. **Celery Workers**: Background task processing
3. **Celery Beat**: Scheduled task management
4. **Redis**: Message broker and result backend
5. **PostgreSQL/SQLite**: Primary database
6. **Nginx**: Reverse proxy (production)

### Data Flow
1. WhatsApp webhook receives message
2. Message queued for processing via Celery
3. User registration/group matching logic executed
4. Database updated with group status
5. Response sent back via WhatsApp API
6. Scheduled tasks handle group progression

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

[Add your license information here]
