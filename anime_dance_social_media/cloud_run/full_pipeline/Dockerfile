# Cloud Run Full Pipeline Service - Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libfontconfig1 \
    libxrender1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY cloud_run/full_pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full pipeline service
COPY cloud_run/full_pipeline/ ./cloud_run/full_pipeline/

# Copy the entire project (needed for workflow imports)
COPY services/ ./services/
COPY workflows/ ./workflows/
COPY core/ ./core/
COPY utils/ ./utils/
COPY config.py ./

# Copy .env if it exists (for local development)
COPY .env* ./

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PORT=8080

# Create output directories
RUN mkdir -p /tmp/output /tmp/temp /tmp/references

# Expose port
EXPOSE 8080

# Run with gunicorn
# Using gevent worker for async handling
CMD exec gunicorn \
    --bind :$PORT \
    --workers 2 \
    --threads 4 \
    --worker-class gevent \
    --timeout 3600 \
    --keep-alive 120 \
    --max-requests 100 \
    --max-requests-jitter 20 \
    --access-logfile - \
    --error-logfile - \
    cloud_run.full_pipeline.main:app
