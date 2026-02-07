# ☁️ Cloud Run Full Pipeline Service - Implementation Plan

**Objective:** Deploy the complete anime dance pipeline (character gen → 3 dance versions → GCS/Firestore) as a Cloud Run service.

**Base Workflow:** `batch_new_chars_workflow.py` (brainstorm → generate → dance → remix)

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT REQUEST                                     │
│  POST /api/v1/pipeline/run                                                  │
│  {                                                                          │
│    "count": 5,                    # Number of characters to generate        │
│    "style_id": "kpop_dance",      # Music style                             │
│    "reference_videos": ["ref1.mp4", "ref2.mp4"],  # Optional: specific refs │
│    "webhook_url": "https://..."   # Optional: callback on completion        │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLOUD RUN SERVICE                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  FLASK API LAYER                                                    │   │
│  │  - POST /api/v1/pipeline/run          → Start new pipeline job      │   │
│  │  - GET  /api/v1/pipeline/status/{id}  → Check job status            │   │
│  │  - GET  /api/v1/pipeline/jobs         → List recent jobs            │   │
│  │  - POST /api/v1/pipeline/cancel/{id}  → Cancel running job          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  JOB ORCHESTRATOR                                                   │   │
│  │  - Creates Firestore job document                                   │   │
│  │  - Spawns background thread for execution                           │   │
│  │  - Updates job status throughout                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PIPELINE EXECUTOR (Reuses batch_new_chars_workflow.py logic)       │   │
│  │                                                                     │   │
│  │  Phase 1: CHARACTER GENERATION                                      │   │
│  │   ├─ Brainstorm character concept                                   │   │
│  │   ├─ Generate anime image                                           │   │
│  │   ├─ Generate cosplay version                                       │   │
│  │   ├─ Upload to GCS → gs://nisan-n8n/anime_dance/characters/         │   │
│  │   └─ Save to Firestore (characters collection)                      │   │
│  │                                                                     │   │
│  │  Phase 2: DANCE GENERATION (3 versions)                             │   │
│  │   ├─ For each reference video:                                      │   │
│  │   │   ├─ Submit Kling AI job                                        │   │
│  │   │   ├─ Wait for completion                                        │   │
│  │   │   ├─ Upload dance to GCS → gs://nisan-n8n/anime_dance/dances/   │   │
│  │   │   └─ Update Firestore                                           │   │
│  │   │                                                                 │   │
│  │  Phase 3: REMIX GENERATION                                          │   │
│  │   ├─ Generate outfit variants (jennie_kpop, jennie_swimsuit)        │   │
│  │   ├─ Submit variant dance jobs                                      │   │
│  │   ├─ Create remix video                                             │   │
│  │   ├─ Audio scoring                                                  │   │
│  │   ├─ Apply watermark                                                │   │
│  │   ├─ Create soundtrack versions (kpop/orig)                         │   │
│  │   ├─ Upload ALL to GCS → gs://nisan-n8n/anime_dance/remixes/        │   │
│  │   └─ Update Firestore                                               │   │
│  │                                                                     │   │
│  │  Phase 4: FINAL OUTPUTS                                             │   │
│  │   ├─ 3x Dance videos (on different references)                      │   │
│  │   ├─ 2x Remix variants (kpop, swimsuit)                             │   │
│  │   ├─ 2x Soundtrack versions (kpop, original)                        │   │
│  │   ├─ 1x Final watermarked deliverable                               │   │
│  │   └─ All uploaded to GCS with public URLs                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FIRESTORE (State Management)                        │
│                                                                             │
│  Collection: pipeline_jobs                                                  │
│  {                                                                          │
│    "job_id": "uuid",                                                        │
│    "status": "running|completed|failed|cancelled",                          │
│    "created_at": timestamp,                                                 │
│    "updated_at": timestamp,                                                 │
│    "config": {count, style_id, ...},                                        │
│    "progress": {                                                            │
│      "total_characters": 5,                                                 │
│      "completed": 2,                                                        │
│      "current_stage": "dance_generation",                                   │
│      "current_character": "ai_hoshino_1770337530"                           │
│    },                                                                       │
│    "results": [                                                             │
│      {                                                                      │
│        "character_id": "...",                                               │
│        "name": "Ai Hoshino",                                                │
│        "assets": {                                                          │
│          "anime_image": "gs://...",                                         │
│          "cosplay_image": "gs://...",                                       │
│          "dances": ["gs://...", "gs://...", "gs://..."],                    │
│          "remixes": {                                                       │
│            "kpop": "gs://...",                                              │
│            "swimsuit": "gs://..."                                           │
│          },                                                                 │
│          "deliverables": [                                                  │
│            {"type": "watermarked", "url": "gs://..."},                      │
│            {"type": "kpop_soundtrack", "url": "gs://..."},                  │
│            {"type": "orig_soundtrack", "url": "gs://..."}                   │
│          ]                                                                  │
│        }                                                                    │
│      }                                                                      │
│    ],                                                                       │
│    "errors": []                                                             │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
anime_dance_social_media/cloud_run/full_pipeline/
├── main.py                     # Flask app entry point
├── Dockerfile                  # Container build
├── requirements.txt            # Python dependencies
├── config.py                   # Environment configuration
├── services/
│   ├── pipeline_service.py     # Core pipeline orchestrator
│   ├── job_tracker.py          # Firestore job tracking
│   └── gcs_uploader.py         # GCS upload utilities
├── executor/
│   └── pipeline_executor.py    # Wraps batch workflow logic
├── routes/
│   └── api.py                  # API endpoints
└── CLOUD_RUN_FULL_PIPELINE_PLAN.md  # This document
```

---

## 🔌 API Endpoints

### 1. Start Pipeline
```http
POST /api/v1/pipeline/run
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "count": 5,                      # Required: Number of characters
  "style_id": "kpop_dance",        # Optional: Music style (default: kpop_dance)
  "reference_videos": [],          # Optional: Specific ref videos (auto-pick if empty)
  "webhook_url": "https://...",    # Optional: Callback on completion
  "options": {
    "skip_existing": true,         # Skip if character already exists
    "generate_variants": true,     # Generate outfit variants
    "create_soundtracks": true,    # Create kpop/orig versions
    "apply_watermark": true        # Apply watermark
  }
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Pipeline job started",
  "estimated_duration": "15-20 minutes per character"
}
```

### 2. Check Status
```http
GET /api/v1/pipeline/status/{job_id}
Authorization: Bearer {api_key}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": {
    "total": 5,
    "completed": 2,
    "current_character": "ai_hoshino_1770337530",
    "current_stage": "remix_generation",
    "percent_complete": 45
  },
  "results": [...],
  "created_at": "2026-02-07T10:00:00Z",
  "updated_at": "2026-02-07T10:15:30Z",
  "estimated_completion": "2026-02-07T10:35:00Z"
}
```

### 3. List Jobs
```http
GET /api/v1/pipeline/jobs?status=running&limit=10
Authorization: Bearer {api_key}
```

### 4. Cancel Job
```http
POST /api/v1/pipeline/cancel/{job_id}
Authorization: Bearer {api_key}
```

---

## 🏗️ Implementation Steps

### Phase 1: Core Wrapper (Day 1)

1. **Create Pipeline Executor**
   ```python
   # executor/pipeline_executor.py
   from workflows.batch_new_chars_workflow import run_batch_new_chars
   from utils.cloud_sync import CloudSyncManager
   
   class PipelineExecutor:
       def __init__(self, job_id, config):
           self.job_id = job_id
           self.config = config
           self.sync = CloudSyncManager()
           self.tracker = JobTracker(job_id)
       
       def execute(self):
           # Wrap the existing workflow with progress tracking
           run_batch_new_chars(
               count=self.config['count'],
               style_id=self.config['style_id'],
               progress_callback=self.update_progress
           )
   ```

2. **Create Job Tracker**
   ```python
   # services/job_tracker.py
   from services.firestore_service import FirestoreService
   
   class JobTracker:
       def __init__(self, job_id):
           self.job_id = job_id
           self.fs = FirestoreService()
       
       def update_status(self, status, progress=None):
           self.fs.db.collection('pipeline_jobs').document(self.job_id).update({
               'status': status,
               'progress': progress,
               'updated_at': firestore.SERVER_TIMESTAMP
           })
   ```

3. **Create Flask App**
   ```python
   # main.py
   from flask import Flask, request, jsonify
   from routes.api import api_bp
   
   app = Flask(__name__)
   app.register_blueprint(api_bp, url_prefix='/api/v1')
   
   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=8080)
   ```

### Phase 2: Background Execution (Day 2)

1. **Async Processing**
   - Since Cloud Run has request timeout (60min max), use background threads
   - Or use Cloud Tasks for long-running jobs
   - Store job state in Firestore

2. **Progress Streaming**
   - Use Firestore real-time updates
   - Client can poll or use Firestore listeners

### Phase 3: 3 Dance Versions (Day 3)

1. **Modify Pipeline for 3 Versions**
   ```python
   # In executor, after main dance, trigger 2 more with different refs
   references = [
       pick_random_reference(),
       pick_random_reference(),
       pick_random_reference()
   ]
   
   for i, ref in enumerate(references):
       run_end_to_end_pipeline(
           char_img=char_img,
           ref_video=ref,
           char_id=char_id,
           style_id=style_id
       )
   ```

2. **Aggregate Results**
   - Store all 3 dance URLs in Firestore
   - Store all remix variants
   - Store soundtrack versions

### Phase 4: Deployment (Day 4)

1. **Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   # Install system deps (ffmpeg, etc.)
   RUN apt-get update && apt-get install -y ffmpeg
   
   # Copy and install Python deps
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   # Copy application
   COPY . .
   
   # Environment
   ENV PORT=8080
   ENV PYTHONUNBUFFERED=1
   
   CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "3600", "main:app"]
   ```

2. **Deploy Command**
   ```bash
   gcloud run deploy full-pipeline-service \
     --source . \
     --region us-central1 \
     --memory 4Gi \
     --cpu 2 \
     --timeout 3600 \
     --concurrency 1 \
     --max-instances 5 \
     --service-account pipeline-runner@nisan-n8n.iam.gserviceaccount.com
   ```

---

## 🔐 Security & Authentication

### API Key Authentication
```python
# middleware/auth.py
from functools import wraps
from flask import request, jsonify

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('Authorization', '').replace('Bearer ', '')
        if key != os.getenv('PIPELINE_API_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated
```

### Service Account Permissions
- Cloud Run service account needs:
  - `roles/storage.objectAdmin` (GCS)
  - `roles/datastore.user` (Firestore)
  - `roles/logging.logWriter` (Logs)

---

## 📊 Resource Requirements

| Resource | Value | Reason |
|----------|-------|--------|
| **Memory** | 4-8 GB | MoviePy video processing |
| **CPU** | 2-4 cores | Parallel processing |
| **Timeout** | 3600s (1 hour) | Per character takes ~15-20 min |
| **Concurrency** | 1 | Sequential processing per instance |
| **Max Instances** | 5-10 | Cost control |

---

## 💰 Cost Optimization

1. **Use Cloud Tasks for async processing**
   - Cloud Run can return immediately
   - Task queue handles execution
   - Pay only for actual processing time

2. **Batch processing**
   - Process multiple characters in one job
   - Reuse Gemini service instances

3. **Storage lifecycle**
   - Auto-delete temp files after 7 days
   - Keep only final deliverables long-term

---

## 🧪 Testing Plan

### Unit Tests
```python
def test_pipeline_executor():
    executor = PipelineExecutor(
        job_id="test-123",
        config={"count": 1, "style_id": "kpop_dance"}
    )
    result = executor.execute()
    assert result['completed'] == 1
```

### Integration Test
```bash
curl -X POST https://full-pipeline-service-url/api/v1/pipeline/run \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -d '{"count": 1, "style_id": "kpop_dance"}'
```

---

## 🚀 Next Steps

1. ✅ Review this plan
2. Create `cloud_run/full_pipeline/` directory structure
3. Implement Phase 1 (Core Wrapper)
4. Test locally
5. Deploy to Cloud Run
6. Monitor and optimize

---

*Plan Version: 1.0*  
*Estimated Implementation: 3-4 days*  
*Complexity: Medium-High*
