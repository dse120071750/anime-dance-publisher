# Lightweight Cloud Run Pipeline Service
# Build context: anime_dance_social_media/

FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg only (needed for moviepy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY cloud_run_pipeline_char_to_vids/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY cloud_run_pipeline_char_to_vids/*.py ./

# Copy required modules from project
COPY config.py ./
COPY services/ ./services/
COPY workflows/ ./workflows/
COPY core/ ./core/
COPY utils/ ./utils/

# Create temp dirs
RUN mkdir -p /tmp/output /tmp/temp /tmp/references

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production
ENV PORT=8080

EXPOSE 8080

# Run with gunicorn (standard worker for compatibility)
CMD exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --threads 4 \
    --timeout 3600 \
    --max-requests 10 \
    --access-logfile - \
    --error-logfile - \
    main:app
