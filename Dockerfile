# AI Beer Crawl App - Multi-stage Docker Build
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-flask \
    pytest-xdist \
    black \
    isort \
    flake8 \
    mypy \
    bandit \
    safety

# Copy application code
COPY . .

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 5000

# Command for development
CMD ["python", "app.py"]

# Production stage
FROM base as production

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/database /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Production command
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "120", "app:app"]

# Worker stage (for Celery workers)
FROM base as worker

# Copy application code
COPY . .

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

# Command for Celery worker
CMD ["celery", "-A", "src.tasks.celery_tasks.celery", "worker", "--loglevel=info", "--concurrency=4"]

# Beat scheduler stage
FROM base as beat

# Copy application code
COPY . .

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

# Command for Celery beat
CMD ["celery", "-A", "src.tasks.celery_tasks.celery", "beat", "--loglevel=info"]
