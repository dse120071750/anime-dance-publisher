# Anime Dance Social Media Pipeline - Agent Guide

This document provides essential information for AI coding agents working on the Anime Dance Social Media Pipeline project.

## Project Overview

An automated pipeline that generates AI anime dance videos and publishes them to Instagram. The pipeline creates anime characters, transforms them into realistic cosplay versions, generates dance videos using motion transfer, creates multi-outfit remixes with AI-composed music, and automatically publishes to social media.

**Core Workflow:**
1. Generate anime character images (Gemini Image 3)
2. Create photorealistic cosplay versions (Gemini Image 3)
3. Generate dance videos via motion transfer (Kling AI via FAL)
4. Create outfit variants and remix videos (MoviePy)
5. Generate AI music and sync to video (Minimax + Beat alignment)
6. Publish to Instagram automatically (Cloud Run + Cloud Scheduler)

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Language** | Python 3.11+ |
| **AI/ML APIs** | Google Gemini 3 (Image/Text), Kling AI (Video), Minimax (Music) |
| **Video Processing** | MoviePy v2.2.1+ |
| **Cloud Platform** | Google Cloud Platform (GCS, Firestore, Cloud Run, Cloud Scheduler) |
| **Web Framework** | Flask (Cloud Run service) |
| **Container** | Docker, Gunicorn |
| **External APIs** | Instagram Graph API, FAL AI |

## Project Structure

```
primordial-hubble/
├── anime_dance_social_media/          # Main project directory
│   ├── workflows/                     # Orchestration scripts (entry points)
│   │   ├── main_pipeline.py          # End-to-end remix generation
│   │   ├── character_gen.py          # Character asset generation
│   │   ├── audio_pipeline.py         # BPM analysis & music scoring
│   │   ├── watermark_job.py          # Apply watermarks to videos
│   │   ├── alignment_pipeline.py     # Character-to-video alignment
│   │   ├── batch_new_chars_workflow.py
│   │   ├── batch_soundtrack_remix.py
│   │   └── redo_pipeline.py
│   ├── core/                          # Business logic layer
│   │   ├── animation.py              # Kling AI integration, video generation
│   │   └── cosplay.py                # Photo-realism style transfer
│   ├── services/                      # API wrappers (infrastructure layer)
│   │   ├── gemini_service.py         # Google Gemini client with key rotation
│   │   ├── gcs_service.py            # Google Cloud Storage operations
│   │   ├── firestore_service.py      # Firestore database operations
│   │   ├── instagram_service.py      # Instagram Graph API
│   │   ├── minimax_service.py        # Minimax music generation
│   │   └── tiktok_service.py
│   ├── utils/                         # Support utilities
│   │   ├── db_utils.py               # Local JSON DB helpers
│   │   ├── download.py               # File download utilities
│   │   ├── cleanup.py                # Temp file cleanup
│   │   └── batch_utils.py            # Batch processing tools
│   ├── scripts/                       # Migration & maintenance
│   │   ├── migrate_to_gcs.py
│   │   ├── migrate_remixes_to_gcs.py
│   │   ├── verify_migration.py
│   │   └── sync_web_showcase.py
│   ├── cloud_run/                     # Cloud Run deployments
│   │   └── publish_to_ig/            # Instagram publishing service
│   │       ├── main.py               # Flask app entry point
│   │       ├── Dockerfile
│   │       ├── requirements.txt
│   │       └── services/             # Service copies for container
│   ├── output/                        # Local output directory
│   │   ├── characters/               # Character images & character_db.json
│   │   ├── dances/                   # Raw Kling dance outputs
│   │   └── remixes/                  # Final remixed videos
│   ├── docs/                          # Static HTML documentation
│   ├── config.py                      # Centralized configuration
│   ├── README.md
│   ├── PROJECT_STRUCTURE.md
│   └── WORKFLOW.md
├── .env                               # Environment variables (root level)
└── service_account_key.json          # GCP service account credentials
```

## Configuration

### Environment Variables (.env)

Located at project root (`C:\Users\gasil\.gemini\antigravity\playground\primordial-hubble\.env`):

```bash
# Instagram Graph API
INSTAGRAM_USER_TOKEN=EAAN7csu0FuUBQ...

# Google / Gemini (supports key rotation)
GOOGLE_ROTATION_KEYS=key1,key2,key3

# FAL AI (for Kling video generation)
FAL_AI_KEY=xxx
FAL_AI_ENDPOINT=https://queue.fal.run/fal-ai/nano-banana-pro/edit

# Google Cloud Platform
GCS_BUCKET_NAME=nisan-n8n
GCP_PROJECT_ID=nisan-n8n
GOOGLE_APPLICATION_CREDENTIALS=C:\Users\gasil\.gemini\antigravity\playground\primordial-hubble\service_account_key.json

# Minimax (AI music generation)
MINIMAX_API_KEY=sk-api-...

# Supabase (legacy, may not be actively used)
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...
```

### Config Class (config.py)

Centralized configuration via `Config` class:

```python
from anime_dance_social_media.config import Config

# Key paths
Config.OUTPUT_DIR          # Root output directory
Config.CHARACTERS_DIR      # Character images
Config.DANCES_DIR          # Dance videos
Config.REMIXES_DIR         # Final remixes
Config.TEMP_DIR            # Temporary files

# Cloud settings
Config.GCP_PROJECT_ID      # "nisan-n8n"
Config.GCS_BUCKET_NAME     # "nisan-n8n"
Config.GCS_BASE_PREFIX     # "anime_dance"

# Feature flags
Config.USE_CLOUD_STORAGE   # True = use GCS, False = local only
Config.USE_FIRESTORE       # True = use Firestore, False = local JSON
```

## Running the Pipeline

### Generate a New Character

```bash
cd anime_dance_social_media
python -m workflows.character_gen
```

This generates:
- Anime character image (output/characters/{name}_{id}.png)
- Cosplay version (output/characters/{name}_{id}_cosplay.png)
- Entry in character_db.json

### Create a Remix Video

```bash
cd anime_dance_social_media
python -m workflows.main_pipeline <path_to_dance_video>
```

Or for end-to-end (character → dance → remix):
```bash
python -m workflows.main_pipeline <character_image> <reference_video>
```

### Run Audio Scoring Only

```bash
python -m workflows.audio_pipeline <video_path>
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `python -m workflows.character_gen` | Generate new character assets |
| `python -m workflows.main_pipeline <video>` | Create remix from dance video |
| `python -m workflows.main_pipeline <img> <ref>` | Full pipeline: char → dance → remix |
| `python -m workflows.audio_pipeline <video>` | Analyze and score video with AI music |
| `python -m workflows.watermark_job` | Apply watermarks to videos |
| `python config.py` | Validate configuration |

## Code Conventions

### Import Pattern

```python
import os
import sys

# Add project root to path for imports
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from services.gemini_service import GeminiService
from utils.db_utils import get_entry, upsert_asset
```

### Service Usage Pattern

```python
# Initialize service
service = GeminiService()

# Use with retry/rotation handling
result = service.generate_image(prompt, output_path)
result = service.edit_image(input_path, output_path, prompt)
analysis = service.generate_text(prompt, context_files=[image_path])
```

### Database Operations

```python
from utils.db_utils import get_entry, upsert_asset, load_db

# Get character by ID
char = get_entry("bulma_1770089530")

# Update asset information
upsert_asset(char_id, {
    "title": "primary",
    "dance_video": video_path,
    "cosplay_image": image_path
})
```

### Path Handling

```python
from pathlib import Path
from config import Config

# Use Config for standard paths
char_dir = Config.CHARACTERS_DIR
output_path = Config.REMIXES_DIR / f"remix_{char_id}.mp4"

# Ensure directories exist
Config.ensure_dirs()
```

## Cloud Architecture

### GCS Bucket Structure

```
gs://nisan-n8n/anime_dance/
├── characters/       # Character images (PNG)
├── dances/           # Dance videos (MP4)
└── remixes/          # Final remixed videos (MP4)
```

### Firestore Collections

- **characters**: Character metadata and asset URLs
- **instagram_posts**: Published post tracking
- **dance_jobs**: Dance generation job tracking

### Cloud Run Service

- **URL**: `https://publish-to-ig-632190740539.us-central1.run.app`
- **Endpoints**:
  - `POST /publish` - Publish specific character/asset
  - `GET /publish_random` - Publish random remix (used by scheduler)
  - `GET /health` - Health check

### Cloud Scheduler

- **Schedule**: Every 3 hours (`0 */3 * * *`)
- **Target**: `/publish_random` endpoint
- **Posts per day**: ~8

## Testing Strategy

No formal test suite exists. Testing is done via:

1. **Manual pipeline runs** with test videos
2. **Config validation**: `python config.py`
3. **Service tests**: Each service module has `if __name__ == "__main__":` block
4. **Migration verification**: `python scripts/verify_migration.py`

## Security Considerations

1. **API Keys**: Stored in `.env` (gitignored), never commit to repository
2. **Service Account**: Uses `service_account_key.json` (gitignored)
3. **Instagram Token**: Page access token with limited permissions
4. **GCS URLs**: Signed URLs used for Instagram (1-hour expiry)
5. **Cloud Run**: Service allows unauthenticated requests (scheduler requirement)

### .gitignore Rules

- `.env` - Environment variables
- `*.json` - JSON credentials (except docs/)
- `service_account_key.json` - GCP credentials
- `output/` - Generated content
- `*.mp4`, `*.mp3`, `*.png` - Media files

## Dependencies

Dependencies are managed per-component (no root requirements.txt):

### Core Dependencies (needed for most workflows)
```bash
pip install moviepy google-genai fal-client python-dotenv requests pillow
```

### Cloud Dependencies
```bash
pip install google-cloud-storage google-cloud-firestore
```

### Cloud Run Service Dependencies
See `cloud_run/publish_to_ig/requirements.txt`:
```
flask
google-cloud-storage
google-cloud-firestore
requests
python-dotenv
gunicorn
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Ensure `sys.path.append(ROOT)` is set correctly
2. **Gemini 429 Errors**: Service automatically rotates through multiple API keys
3. **MoviePy import errors**: Use `moviepy.video.io.VideoFileClip` pattern (v2.x)
4. **GCS authentication**: Check `GOOGLE_APPLICATION_CREDENTIALS` path exists
5. **Instagram publish fails**: Token may be expired; generate new Page Access Token

### File Locations

- Local DB: `anime_dance_social_media/output/characters/character_db.json`
- Temp files: `anime_dance_social_media/output/temp/`
- Service account: Project root `service_account_key.json`
- Environment: Project root `.env`

## Development Notes

- The project uses **MoviePy v2.x** (import patterns differ from v1.x)
- All AI services implement **retry logic with exponential backoff**
- **Key rotation** is implemented for Gemini API to handle rate limits
- The pipeline is designed to be **idempotent** - safe to re-run
- Cloud-first architecture: assets synced to GCS, metadata in Firestore
