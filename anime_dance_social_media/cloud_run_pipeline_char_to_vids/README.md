# Cloud Run Pipeline - Char to Videos (Lightweight)

Optimized Cloud Run service for the anime dance pipeline. Scales to 0 when idle.

## Features

- ✅ **Scale to 0** - No cost when idle
- ✅ **Fast cold start** - Minimal dependencies loaded at startup
- ✅ **GCS/Firestore only** - No local storage dependencies
- ✅ **Background processing** - API returns immediately, processing continues
- ✅ **Cost optimized** - 4GB RAM, 2 CPU (vs 8GB/4 CPU)

## API

### Start Pipeline
```bash
curl -X POST https://<service-url>/pipeline/run \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"count": 5, "style_id": "kpop_dance"}'
```

### Check Status
```bash
curl https://<service-url>/pipeline/status/<job_id> \
  -H "Authorization: Bearer $API_KEY"
```

## Deploy

```bash
cd anime_dance_social_media/cloud_run_pipeline_char_to_vids
./deploy.sh
```

Or manually:
```bash
gcloud builds submit --config cloudbuild.yaml ..
```

## Architecture

```
┌─────────────┐
│  Cloud Run  │ ◄── Scales to 0
│  (Flask)    │     when idle
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  API Request                            │
│  ↓                                      │
│  Create Firestore Job Doc               │
│  ↓                                      │
│  Start Background Thread                │
│  ↓                                      │
│  Return 202 Accepted                    │
│  ↓                                      │
│  Background:                            │
│    - Generate Character                 │
│    - Upload images to GCS               │
│    - Generate 3 dance versions          │
│    - Upload videos to GCS               │
│    - Update Firestore                   │
└─────────────────────────────────────────┘
```

## Cost Optimization

| Setting | Value | Why |
|---------|-------|-----|
| min-instances | 0 | Scale to 0 when idle |
| max-instances | 3 | Limit concurrent processing |
| memory | 4GB | Reduced from 8GB |
| cpu | 2 | Reduced from 4 |
| concurrency | 1 | Sequential job processing |

## File Structure

```
cloud_run_pipeline_char_to_vids/
├── main.py              # Flask app
├── Dockerfile           # Container (lightweight)
├── requirements.txt     # Minimal deps
├── cloudbuild.yaml      # Build & deploy
└── README.md            # This file
```
