FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install system dependencies (curl for healthchecks if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Create non-root system user and adjust permissions
RUN addgroup --system --gid 1001 wintergroup \
    && adduser --system --uid 1001 --ingroup wintergroup winteruser \
    && chown -R winteruser:wintergroup /app

USER winteruser

EXPOSE 8000

# Default entrypoint for Railway web service (Railway supplies $PORT dynamically)
CMD ["sh", "-c", "gunicorn winter_arc.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --threads 2 --timeout 60"]


