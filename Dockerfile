# Multi-stage / Production-ready Dockerfile for Winter Arc
FROM python:3.12-slim AS runner

# Set system environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies needed for compiling extensions and PostgreSQL client tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user and group for security
RUN groupadd -r winterarc && useradd -r -g winterarc -d /app -s /sbin/nologin winterarc

WORKDIR /app

# Install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project source code
COPY . /app/

# Ensure media and static directories exist with proper permissions for the non-root user
RUN mkdir -p /app/staticfiles /app/media /app/logs && \
    chown -R winterarc:winterarc /app

# Switch to non-root user
USER winterarc

# Default entrypoint runs Gunicorn WSGI server, binding to dynamic $PORT (or 8000)
CMD exec gunicorn winter_arc.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --threads 2 --timeout 60 --access-logfile - --error-logfile -

