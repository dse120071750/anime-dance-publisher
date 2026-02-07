# 🔍 Workflow Cloud Integration Audit

**Date:** February 7, 2026  
**Issue:** Workflows create local assets but don't auto-upload to cloud

---

## 📋 Current Pipeline Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. Character   │────▶│  2. Dance Gen   │────▶│  3. Remix       │
│     Generation  │     │   (Kling AI)    │     │  + Soundtrack   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
   Local: output/           Local: output/          Local: output/
   characters/              dances/                 remixes/
         │                       │                       │
         ▼                       ▼                       ▼
   Local DB Only          Local DB Only           Local DB Only
   ❌ No GCS Upload       ❌ No GCS Upload        ❌ No GCS Upload
   ❌ No Firestore        ❌ No Firestore         ❌ No Firestore
```

---

## 🔍 Workflow Analysis

### 1. `character_gen.py`
**Creates:** Character images (anime + cosplay)  
**Saves to:** `output/characters/`  
**Database:** `register_character()` + `upsert_asset()` → Local JSON only  
**Cloud Upload:** ❌ NO

```python
# Current behavior (local only):
register_character(char_id, name, anime, ...)
upsert_asset(char_id, {
    "title": "primary",
    "anime_image": output_path,        # Local path
    "cosplay_image": cosplay_path      # Local path
})
```

### 2. `main_pipeline.py` / `redo_pipeline.py`
**Creates:** Dance videos, remixes, variants  
**Saves to:** `output/dances/`, `output/remixes/`  
**Database:** `upsert_asset()` → Local JSON only  
**Cloud Upload:** ❌ NO

```python
# Current behavior (local only):
upsert_asset(char_id, {
    "title": "primary",
    "dance_video": target_path,        # Local path
    "cosplay_image": cosplay_path      # Local path
})
```

### 3. `audio_pipeline.py`
**Creates:** AI-generated music, scored videos  
**Saves to:** `output/remixes/*/result/`  
**Database:** None  
**Cloud Upload:** ❌ NO

### 4. `watermark_job.py`
**Creates:** Watermarked videos, icon/name stickers  
**Saves to:** `output/remixes/*/result/`  
**Database:** None  
**Cloud Upload:** ❌ NO

### 5. `batch_soundtrack_remix.py`
**Creates:** Dual soundtrack versions (kpop/orig)  
**Saves to:** `output/remixes/*/result/`  
**Database:** None  
**Cloud Upload:** ❌ NO

---

## 📊 Asset Type Mapping

| Asset Type | Local Path | GCS Path | Firestore Field |
|------------|-----------|----------|-----------------|
| Anime Image | `characters/{id}.png` | `anime_dance/characters/{id}.png` | `assets[].anime_image` |
| Cosplay Image | `characters/{id}_cosplay.png` | `anime_dance/characters/{id}_cosplay.png` | `assets[].cosplay_image` |
| Dance Video | `dances/dance_{id}...mp4` | `anime_dance/dances/dance_{id}...mp4` | `assets[].dance_video` |
| Remix Video | `remixes/.../REMIX_...mp4` | `anime_dance/remixes/.../REMIX_...mp4` | `assets[].deliverable` |
| Variant Video | `remixes/.../variants/...mp4` | `anime_dance/remixes/.../variants/...mp4` | `assets[].dance_video` |
| K-Pop Version | `remixes/.../result/[kpop]_...mp4` | `anime_dance/remixes/.../result/[kpop]_...mp4` | `assets[].kpop_video` |
| Orig Version | `remixes/.../result/[orig]_...mp4` | `anime_dance/remixes/.../result/[orig]_...mp4` | `assets[].orig_video` |
| Watermarked | `remixes/.../..._watermarked.mp4` | `anime_dance/remixes/.../..._watermarked.mp4` | `assets[].watermarked` |
| AI Music | `remixes/.../result/generated_kpop_music.mp3` | `anime_dance/remixes/.../result/...mp3` | `assets[].ai_music` |
| Icons | `remixes/.../result/icon_...png` | `anime_dance/remixes/.../result/icon_...png` | `assets[].icon` |

---

## ⚠️ Critical Findings

### Finding 1: Local-Only Storage
**Severity:** HIGH  
All workflows store paths as local file paths (`C:\\oo\\bar`) instead of GCS URIs (`gs://bucket/path`).

**Impact:**
- Cloud Run services can't access local paths
- Instagram publishing fails (needs GCS signed URLs)
- Web showcase can't display assets
- Data loss risk if local files deleted

### Finding 2: No Automatic Cloud Sync
**Severity:** HIGH  
New assets created after the initial migration are NOT automatically uploaded.

**Impact:**
- Manual migration needed periodically
- Inconsistent data between local and cloud
- Production pipeline broken for new characters

### Finding 3: Missing Assets in Firestore
**Severity:** MEDIUM  
Soundtrack variants, watermarked versions, and AI music not tracked in Firestore.

**Impact:**
- Can't query for specific versions
- Publishing workflow incomplete
- Asset management difficult

---

## ✅ Solution: Auto-Upload Decorator

### Proposed Architecture

```python
from utils.cloud_utils import auto_upload_to_gcs, update_firestore_gcs_path

@auto_upload_to_gcs(asset_type="character_image")
def generate_character_image(...):
    # Local generation
    output_path = service.generate_image(...)
    
    # Auto-upload happens here
    return output_path, gcs_uri

# In workflows:
local_path, gcs_uri = generate_character_image(...)
upsert_asset(char_id, {
    "title": "primary",
    "anime_image": gcs_uri,  # GCS URI instead of local path
})
```

### Files to Modify

1. **utils/db_utils.py** - Add cloud sync wrapper
2. **workflows/character_gen.py** - Upload images + update DB with GCS paths
3. **workflows/main_pipeline.py** - Upload dance videos + remixes
4. **workflows/audio_pipeline.py** - Upload generated music
5. **workflows/watermark_job.py** - Upload watermarked videos
6. **workflows/batch_soundtrack_remix.py** - Upload soundtrack variants

---

## 🔧 Immediate Fix Required

### Option 1: Add Upload to Workflows (Recommended)
Modify each workflow to upload after creation:

```python
from services.gcs_service import GCSService
from services.firestore_service import FirestoreService

gcs = GCSService()
fs = FirestoreService()

# After creating local asset
gcs_uri = gcs.upload_file(local_path)
fs.update_character_asset(char_id, "primary", {"anime_image": gcs_uri})
```

### Option 2: Background Sync Daemon
Create a watcher that syncs new files automatically:

```python
# sync_daemon.py
watch_directory("output/", auto_upload=True)
```

### Option 3: Post-Processing Step
Run migration script after each workflow:

```python
# After workflow completes
python scripts/migrate_new_assets.py --char-id=ai_hoshino
```

---

## 📈 Migration Status (Current)

| Asset Category | Local Count | GCS Count | Sync Status |
|----------------|-------------|-----------|-------------|
| Character Images | 121 | 121 | ✅ Complete |
| Dance Videos | 62 | 70 | ✅ Complete |
| Remix Videos | 64 dirs | 498 files | ✅ Complete |
| AI Music | ~50 | Unknown | ⚠️ Partial |
| Watermarked | ~60 | Unknown | ⚠️ Partial |
| Icons/Stickers | ~60 | Unknown | ⚠️ Partial |

**Note:** Initial migration was one-time. New assets since then are NOT synced.

---

## 🎯 Action Items

- [ ] Create `utils/cloud_sync.py` helper module
- [ ] Modify `character_gen.py` to auto-upload images
- [ ] Modify `main_pipeline.py` to auto-upload videos
- [ ] Modify `audio_pipeline.py` to auto-upload music
- [ ] Modify `watermark_job.py` to auto-upload watermarked videos
- [ ] Modify `batch_soundtrack_remix.py` to auto-upload soundtrack versions
- [ ] Run full re-sync to catch up missed assets
- [ ] Test cloud-only workflow (delete local, verify cloud still works)

---

*Report generated by Cloud Integration Auditor*
