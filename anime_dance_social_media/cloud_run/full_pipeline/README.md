# Cloud Run Full Pipeline Service

Complete anime dance pipeline deployed as a Cloud Run service.

## Features

- **Character Generation**: Brainstorm → Anime Image → Cosplay Version
- **3 Dance Versions**: Each character dances to 3 different reference videos
- **Remix Generation**: Outfit variants (K-Pop, Swimsuit)
- **Soundtrack Versions**: K-Pop and Original music
- **Auto Cloud Upload**: All assets uploaded to GCS + Firestore
- **Real-time Tracking**: Job progress via Firestore
- **Webhook Callbacks**: Get notified on completion

## API Endpoints

### Start Pipeline
```bash
curl -X POST https://<service-url>/api/v1/pipeline/run \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "count": 5,
    "style_id": "kpop_dance",
    "webhook_url": "https://your-app.com/webhook"
  }'
```

### Check Status
```bash
curl https://<service-url>/api/v1/pipeline/status/<job_id> \
  -H "Authorization: Bearer $API_KEY"
```

### List Jobs
```bash
curl "https://<service-url>/api/v1/pipeline/jobs?status=running&limit=10" \
  -H "Authorization: Bearer $API_KEY"
```

## Deployment

### Prerequisites
1. Set up GCP project with billing
2. Enable APIs: Cloud Run, Firestore, Cloud Storage
3. Create service account with permissions
4. Set up secrets (API_KEY, GCP credentials)

### Deploy
```bash
# Set project
gcloud config set project nisan-n8n

# Deploy to Cloud Run
gcloud run deploy full-pipeline-service \
  --source . \
  --region us-central1 \
  --memory 8Gi \
  --cpu 4 \
  --timeout 3600 \
  --concurrency 1 \
  --max-instances 5 \
  --service-account pipeline-runner@nisan-n8n.iam.gserviceaccount.com \
  --set-env-vars "PIPELINE_API_KEY=$API_KEY,GCP_PROJECT_ID=nisan-n8n,GCS_BUCKET_NAME=nisan-n8n"
```

### Mount Reference Videos
```bash
# Upload reference videos to GCS
gsutil cp *.mp4 gs://nisan-n8n/references/

# Service will download them on startup
```

## Resource Requirements

| Resource | Value | Reason |
|----------|-------|--------|
| Memory | 8 GB | MoviePy video processing |
| CPU | 4 cores | Parallel processing |
| Timeout | 3600s | Per character takes ~15-20 min |
| Concurrency | 1 | Sequential processing per instance |

## Monitoring

View logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=full-pipeline-service" --limit=50
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│ Cloud Run   │────▶│  Firestore  │
│             │◀────│  Service    │◀────│    (Jobs)   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │     GCS     │
                    │  (Assets)   │
                    └─────────────┘
```

## Development

### Local Testing
```bash
cd anime_dance_social_media/cloud_run/full_pipeline

# Set env vars
export PIPELINE_API_KEY=test-key
export GCP_PROJECT_ID=nisan-n8n
export GOOGLE_APPLICATION_CREDENTIALS=../../../service_account_key.json

# Run
python main.py
```

### Test API
```bash
# Health check
curl http://localhost:8080/api/v1/health

# Start pipeline
curl -X POST http://localhost:8080/api/v1/pipeline/run \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -d '{"count": 1}'
```

## License

Private - AURA MACHINE
