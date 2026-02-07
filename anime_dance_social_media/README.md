# Anime Dance Social Media Pipeline

An automated pipeline for generating AI anime dance videos and publishing them to Instagram.

## Architecture

The project uses a **cloud-first** architecture:
- **Storage**: Google Cloud Storage (`gs://nisan-n8n/anime_dance/`)
- **Database**: Firestore (`nisan-n8n` project, `characters` collection)
- **Publishing**: Cloud Run (`publish-to-ig`) with Cloud Scheduler (every 3 hours)

## Project Structure

```
anime_dance_social_media/
├── cloud_run/              # Cloud Run deployments
│   └── publish_to_ig/      # Instagram publishing service
├── core/                   # Business logic (animation, cosplay)
├── services/               # API wrappers (GCS, Firestore, Instagram, Gemini, Minimax)
├── workflows/              # Orchestration scripts (main_pipeline, character_gen, audio_pipeline)
├── utils/                  # Helpers (download, cleanup, batch)
├── scripts/                # Migration & maintenance scripts
├── output/                 # Local output directory
│   ├── characters/         # Character images & character_db.json
│   ├── dances/             # Kling AI dance outputs
│   └── remixes/            # Final remixed videos
└── config.py               # Centralized configuration
```

## Key Scripts

| Script | Purpose |
|--------|---------|
| `workflows/main_pipeline.py` | End-to-end remix generation |
| `workflows/character_gen.py` | Character asset generation |
| `workflows/audio_pipeline.py` | BPM analysis & music scoring |
| `scripts/migrate_to_gcs.py` | One-time migration to cloud |
| `scripts/migrate_remixes_to_gcs.py` | Upload remixes to GCS |
| `scripts/verify_migration.py` | Verify cloud migration |

## Cloud Services

### GCS Bucket Structure
```
gs://nisan-n8n/anime_dance/
├── characters/       # Character images
├── dances/           # Dance videos
└── remixes/          # Final remixed videos
```

### Firestore Collections
- `characters`: Character metadata and asset URLs
- `instagram_posts`: Published post tracking
- `dance_jobs`: Dance generation job tracking

### Cloud Run Service
- **URL**: `https://publish-to-ig-632190740539.us-central1.run.app`
- **Endpoints**:
  - `POST /publish` - Publish specific character/asset
  - `GET /publish_random` - Publish random remix (used by scheduler)
  - `GET /health` - Health check

## Environment Variables

Required in `.env`:
```
INSTAGRAM_USER_TOKEN=...
GCS_BUCKET_NAME=nisan-n8n
GCP_PROJECT_ID=nisan-n8n
GOOGLE_APPLICATION_CREDENTIALS=...
```

## Quick Start

1. **Generate a character**: `python -m workflows.character_gen`
2. **Create a remix**: `python -m workflows.main_pipeline`
3. **Publish to Instagram**: Automatically via Cloud Scheduler (every 3 hours)
