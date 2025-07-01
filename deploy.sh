#!/bin/bash

# AI Beer Crawl App - Production Deployment Script
# This script sets up and deploys the complete production environment

set -e  # Exit on any error

echo "🍺 AI Beer Crawl App - Production Deployment"
echo "============================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check prerequisites
print_step "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Prerequisites check passed ✅"

# Environment setup
print_step "Setting up environment..."

# Create necessary directories
mkdir -p logs
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources
mkdir -p nginx/ssl

# Generate secure secrets if not provided
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env
    
    # Generate secure secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/your-secret-key-here/$SECRET_KEY/" .env
    
    # Generate PostgreSQL password
    POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
    sed -i "s/your-postgres-password/$POSTGRES_PASSWORD/" .env
    
    print_status "Generated secure secrets in .env file"
else
    print_status ".env file already exists"
fi

# Create Grafana datasource configuration
cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Create Grafana dashboard configuration
cat > monitoring/grafana/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

print_status "Environment setup completed ✅"

# Build and deploy
print_step "Building and deploying services..."

# Stop any running services
docker-compose down 2>/dev/null || true

# Build the application
print_status "Building application image..."
docker-compose -f docker-compose.monitoring.yml build

# Start core services first
print_status "Starting infrastructure services..."
docker-compose -f docker-compose.monitoring.yml up -d redis db

# Wait for database to be ready
print_status "Waiting for database to be ready..."
timeout 60 bash -c 'until docker-compose -f docker-compose.monitoring.yml exec -T db pg_isready -U postgres; do sleep 2; done'

# Run database migrations
print_status "Running database migrations..."
docker-compose -f docker-compose.monitoring.yml run --rm app flask db upgrade

# Start all services
print_status "Starting all services..."
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Health checks
print_step "Running health checks..."

# Check if Flask app is running
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    print_status "Flask application: ✅ Running"
else
    print_error "Flask application: ❌ Not responding"
fi

# Check if Redis is running
if docker-compose -f docker-compose.monitoring.yml exec -T redis redis-cli ping | grep -q PONG; then
    print_status "Redis: ✅ Running"
else
    print_error "Redis: ❌ Not responding"
fi

# Check if PostgreSQL is running
if docker-compose -f docker-compose.monitoring.yml exec -T db pg_isready -U postgres > /dev/null 2>&1; then
    print_status "PostgreSQL: ✅ Running"
else
    print_error "PostgreSQL: ❌ Not responding"
fi

# Check if Prometheus is running
if curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_status "Prometheus: ✅ Running"
else
    print_warning "Prometheus: ⚠️ May still be starting..."
fi

# Check if Grafana is running
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    print_status "Grafana: ✅ Running"
else
    print_warning "Grafana: ⚠️ May still be starting..."
fi

# Show service URLs
print_step "Deployment completed! 🎉"
echo ""
echo "Service URLs:"
echo "============="
echo "🍺 Main Application:    http://localhost:5000"
echo "🏥 Health Check:        http://localhost:5000/health"
echo "📊 Prometheus Metrics:  http://localhost:9090"
echo "📈 Grafana Dashboard:   http://localhost:3000 (admin/admin)"
echo "🌸 Flower (Celery):     http://localhost:5555"
echo "📋 API Documentation:   http://localhost:5000/api/beer-crawl/bars"
echo ""
echo "Database:"
echo "========="
echo "🐘 PostgreSQL:          localhost:5432"
echo "🔑 Database:            beer_crawl"
echo "👤 User:                postgres"
echo ""
echo "Monitoring:"
echo "==========="
echo "📊 Prometheus:          http://localhost:9090"
echo "📈 Grafana:             http://localhost:3000"
echo "📊 Node Exporter:       http://localhost:9100"
echo "🔄 Redis Exporter:      http://localhost:9121"
echo ""

# Show logs command
echo "To view logs:"
echo "============="
echo "docker-compose -f docker-compose.monitoring.yml logs -f [service_name]"
echo ""
echo "Services: app, worker, beat, db, redis, prometheus, grafana, flower"
echo ""

# Show useful commands
echo "Useful commands:"
echo "================"
echo "Stop all services:      docker-compose -f docker-compose.monitoring.yml down"
echo "View service status:    docker-compose -f docker-compose.monitoring.yml ps"
echo "Scale workers:          docker-compose -f docker-compose.monitoring.yml up -d --scale worker=3"
echo "Backup database:        docker-compose -f docker-compose.monitoring.yml exec db pg_dump -U postgres beer_crawl > backup.sql"
echo ""

print_status "Production deployment completed successfully! 🚀"

# Optional: run integration tests
if [ "$1" = "--test" ]; then
    print_step "Running integration tests..."
    
    # Test API endpoints
    echo "Testing API endpoints..."
    
    # Health check
    if curl -f http://localhost:5000/health | grep -q "healthy"; then
        print_status "Health check: ✅ PASSED"
    else
        print_error "Health check: ❌ FAILED"
    fi
    
    # Bars API
    if curl -f http://localhost:5000/api/beer-crawl/bars | grep -q "bars"; then
        print_status "Bars API: ✅ PASSED"
    else
        print_error "Bars API: ❌ FAILED"
    fi
    
    # Groups API
    if curl -f http://localhost:5000/api/beer-crawl/groups | grep -q "groups"; then
        print_status "Groups API: ✅ PASSED"
    else
        print_error "Groups API: ❌ FAILED"
    fi
    
    print_status "Integration tests completed!"
fi
