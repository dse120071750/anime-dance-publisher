# Lightweight Cloud Run Pipeline Service
# Optimized for scale-to-0 and fast cold starts

FROM python:3.11-slim

WORKDIR /app

# Install minimal system deps (no ffmpeg - it will be installed if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy only this service's requirements
COPY cloud_run_pipeline_char_to_vids/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service code
COPY cloud_run_pipeline_char_to_vids/*.py ./

# Copy required project modules (minimal)
COPY config.py ./
COPY services/ ./services/
COPY workflows/ ./workflows/
COPY core/ ./core/
COPY utils/ ./utils/

# Create temp directories
RUN mkdir -p /tmp/output /tmp/temp /tmp/references

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production
ENV PORT=8080

# Expose port
EXPOSE 8080

# Use gunicorn with gevent for async handling
# --preload for faster fork, --max-requests for memory cleanup
CMD exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --threads 2 \
    --worker-class gevent \
    --timeout 3600 \
    --max-requests 10 \
    --max-requests-jitter 5 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    main:app
