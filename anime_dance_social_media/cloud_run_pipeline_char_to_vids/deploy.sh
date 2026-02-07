#!/bin/bash
# Deploy lightweight pipeline service to Cloud Run

set -e

PROJECT_ID="nisan-n8n"
SERVICE_NAME="pipeline-char-to-vids"
REGION="us-central1"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  AURA Pipeline - Char to Videos (Lightweight)               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check env vars
if [ -z "$PIPELINE_API_KEY" ]; then
    echo "⚠️  Warning: PIPELINE_API_KEY not set, using default"
    export PIPELINE_API_KEY="aura-pipeline-2026-secret"
fi

# Set project
gcloud config set project $PROJECT_ID

echo "🔧 Building and deploying..."
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo ""

# Build from parent directory (needed for imports)
cd ..

gcloud builds submit \
  --config cloud_run_pipeline_char_to_vids/cloudbuild.yaml \
  . \
  --timeout=15m

echo ""
echo "✅ Deployment Complete!"
echo ""

# Get URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo "Service URL: $SERVICE_URL"
echo ""
echo "Test endpoints:"
echo "  curl $SERVICE_URL/health"
echo "  curl -X POST $SERVICE_URL/pipeline/run -H \"Authorization: Bearer $PIPELINE_API_KEY\" -d '{\"count\":1}'"
echo ""
