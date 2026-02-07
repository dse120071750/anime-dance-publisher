# Cloud Run & Scheduler: Instagram Publishing Service

This document details the automated Instagram publishing infrastructure deployed on Google Cloud.

---

## Overview

The `publish-to-ig` Cloud Run service automatically publishes anime dance remix videos to Instagram. It is triggered by Cloud Scheduler every 3 hours to post a random character's original soundtrack remix.

---

## Cloud Run Service

### Deployment Details

| Property | Value |
|----------|-------|
| **Service Name** | `publish-to-ig` |
| **Region** | `us-central1` |
| **Project** | `nisan-n8n` |
| **URL** | `https://publish-to-ig-632190740539.us-central1.run.app` |
| **Authentication** | Allow unauthenticated |

### Source Location

```
cloud_run/publish_to_ig/
├── main.py                 # Flask application with endpoints
├── Dockerfile              # Container configuration
├── requirements.txt        # Python dependencies
├── config.py               # Environment configuration
├── .env                    # Environment variables (secrets)
├── service_account_key.json # GCP service account
└── services/
    ├── gcs_service.py      # Google Cloud Storage operations
    ├── firestore_service.py # Firestore database operations
    └── instagram_service.py # Instagram Graph API operations
```

### API Endpoints

#### `POST /publish`
Publish a specific character's video to Instagram.

**Request Body:**
```json
{
  "character_id": "bulma_1770089530",
  "asset_title": "primary",
  "version": "remix_orig_watermarked",
  "caption": "Custom caption here! #anime #dance"
}
```

**Parameters:**
- `character_id` (required): Firestore character document ID
- `asset_title` (optional, default: `primary`): Asset to publish
- `version` (optional, default: `remix_orig_watermarked`): Video version
  - `remix_kpop_watermarked` - K-pop soundtrack version
  - `remix_orig_watermarked` - Original soundtrack version
  - `remix_structured_watermarked` - AI-scored version
- `caption` (optional): Custom Instagram caption

**Response:**
```json
{
  "success": true,
  "container_id": "17854210536656441",
  "media_id": "18074143598382842",
  "status": "published",
  "published_at": "2026-02-06T21:30:00.000Z"
}
```

#### `GET /publish_random`
Publish a random character's original soundtrack remix. Used by Cloud Scheduler.

**Logic:**
1. Fetches all characters from Firestore
2. Filters for those with `remix_orig_watermarked` asset
3. Randomly selects one
4. Generates a signed GCS URL (1 hour expiry)
5. Publishes to Instagram via Graph API
6. Logs the post to Firestore `instagram_posts` collection

**Response:**
```json
{
  "message": "Random post successful",
  "character": "violet_evergarden_1770090117",
  "asset": "primary",
  "success": true,
  "media_id": "18085781675123456"
}
```

#### `GET /health`
Health check endpoint for Cloud Run.

---

## Cloud Scheduler

### Job Details

| Property | Value |
|----------|-------|
| **Job Name** | `random-ig-publish` |
| **Location** | `us-central1` |
| **Schedule** | `0 */3 * * *` (every 3 hours) |
| **Target** | `https://publish-to-ig-632190740539.us-central1.run.app/publish_random` |
| **HTTP Method** | `GET` |
| **Timeout** | 180 seconds |

### Schedule Breakdown
- Runs at: 00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00 UTC
- Approximately 8 posts per day

---

## Environment Variables

Required in `.env` file within `cloud_run/publish_to_ig/`:

```bash
# Instagram Graph API
INSTAGRAM_USER_TOKEN=EAAN7csu0FuUBQ...

# Google Cloud
GCS_BUCKET_NAME=nisan-n8n
GCP_PROJECT_ID=nisan-n8n
GOOGLE_APPLICATION_CREDENTIALS=/app/service_account_key.json
```

> **Note:** The `GOOGLE_APPLICATION_CREDENTIALS` path must be `/app/service_account_key.json` for the container, not a local Windows path.

---

## Deployment Commands

### Deploy the Service
```bash
cd cloud_run/publish_to_ig
gcloud run deploy publish-to-ig \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Create the Scheduler Job
```bash
gcloud scheduler jobs create http random-ig-publish \
  --schedule="0 */3 * * *" \
  --uri="https://publish-to-ig-632190740539.us-central1.run.app/publish_random" \
  --http-method=GET \
  --location=us-central1 \
  --description="Publishes a random IG Reel every 3 hours"
```

### Manually Trigger the Scheduler
```bash
gcloud scheduler jobs run random-ig-publish --location=us-central1
```

### View Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=publish-to-ig" --limit=20 --format="value(textPayload)"
```

---

## Firestore Data Structure

### `characters` Collection
```json
{
  "id": "bulma_1770089530",
  "name": "Bulma",
  "anime": "Dragon Ball",
  "assets": [
    {
      "title": "primary",
      "anime_image": "gs://nisan-n8n/anime_dance/characters/bulma_1770089530.png",
      "cosplay_image": "gs://nisan-n8n/anime_dance/characters/bulma_1770089530_cosplay.png",
      "dance_video": "gs://nisan-n8n/anime_dance/dances/dance_bulma_1770089530_cosplay_on_SdgAy1i_DdA.mp4",
      "remix_kpop_watermarked": "gs://nisan-n8n/anime_dance/remixes/.../[kpop_soundtrack]_..._watermarked.mp4",
      "remix_orig_watermarked": "gs://nisan-n8n/anime_dance/remixes/.../[orig_soundtrack]_..._watermarked.mp4",
      "remix_structured_watermarked": "gs://nisan-n8n/anime_dance/remixes/.../_structured_scored_watermarked.mp4"
    }
  ]
}
```

### `instagram_posts` Collection
```json
{
  "character_id": "bulma_1770089530",
  "asset_title": "primary",
  "media_url": "gs://nisan-n8n/anime_dance/remixes/.../[orig_soundtrack]_..._watermarked.mp4",
  "status": "published",
  "post_id": "18074143598382842",
  "published_at": "2026-02-06T21:30:00Z",
  "insights": { "likes": 0, "comments": 0, "views": 0 },
  "created_at": "2026-02-06T21:30:00Z"
}
```

---

## Instagram Account

| Property | Value |
|----------|-------|
| **Username** | `@miashen.swim` |
| **IG Business Account ID** | `17841467182279476` |
| **Facebook Page ID** | `1040271232491933` |
| **Token Type** | Page Access Token |

---

## Troubleshooting

### Token Expired
If publishing fails with a 400 error, the Instagram token may have expired. Generate a new Page Access Token from the [Meta Business Suite](https://business.facebook.com/) and update `.env`.

### Video Processing Timeout
Instagram video processing can take 30-60 seconds. The service polls for status every 10 seconds with a 5-minute timeout.

### Signed URL Issues
GCS signed URLs expire after 1 hour. If Instagram fails to fetch the video, ensure the publish happens quickly after URL generation.
