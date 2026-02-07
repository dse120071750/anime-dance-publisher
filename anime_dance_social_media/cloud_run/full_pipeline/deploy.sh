#!/bin/bash
# Deploy script for Cloud Run Full Pipeline Service

set -e

# Configuration
PROJECT_ID="nisan-n8n"
SERVICE_NAME="full-pipeline-service"
REGION="us-central1"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  AURA Full Pipeline Service - Deployment Script             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

if [ -z "$PIPELINE_API_KEY" ]; then
    echo "❌ PIPELINE_API_KEY environment variable not set"
    echo "   Run: export PIPELINE_API_KEY=your-secret-key"
    exit 1
fi

# Set project
echo "🔧 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable APIs
echo "🔌 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable storage.googleapis.com

# Deploy to Cloud Run
echo ""
echo "🚀 Deploying to Cloud Run..."
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo ""

cd ../../..  # Go to project root

gcloud run deploy $SERVICE_NAME \
  --source anime_dance_social_media/cloud_run/full_pipeline \
  --region $REGION \
  --platform managed \
  --memory 8Gi \
  --cpu 4 \
  --timeout 3600 \
  --concurrency 1 \
  --max-instances 5 \
  --min-instances 0 \
  --set-env-vars "PIPELINE_API_KEY=$PIPELINE_API_KEY,GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET_NAME=$PROJECT_ID" \
  --set-env-vars "GOOGLE_APPLICATION_CREDENTIALS=/tmp/creds.json" \
  --allow-unauthenticated

# Get service URL
echo ""
echo "🔍 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "Test with:"
echo "  curl $SERVICE_URL/api/v1/health"
echo ""
echo "Start pipeline:"
echo "  curl -X POST $SERVICE_URL/api/v1/pipeline/run \\"
echo "    -H \"Authorization: Bearer $PIPELINE_API_KEY\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"count\": 1}'"
echo ""
