# Batch Workflow Cloud Sync Audit

**Date:** February 7, 2026  
**Auditor:** AI Agent

---

## 📋 Workflow-by-Workflow Analysis

### 1. `batch_new_chars_workflow.py`

**Purpose:** Sequential batch generation of new characters

**Flow:**
```
1. Check for pending dances (cosplay exists, no dance)
   → Calls run_end_to_end_pipeline() ✅
   
2. Generate new characters
   → Calls generate_characters() ✅
   → Then run_end_to_end_pipeline() ✅
```

**Cloud Sync Status:** ✅ **COVERED**
- `generate_characters()` → Now uploads to GCS/Firestore
- `run_end_to_end_pipeline()` → Now uploads to GCS/Firestore

**Action Required:** None

---

### 2. `redo_pipeline.py`

**Purpose:** Redo/regenerate existing projects

**Functions:**
- `redo_project()` - Redo single project
- `loop_all_projects()` - Loop through DB and finish processing
- `batch_process_redo_folder()` - Batch redo from folder

**Analysis:**

#### Function: `redo_project()`
```python
# Line 88-91: Updates DB with local paths (NO CLOUD SYNC)
upsert_asset(entry["id"], {
    "title": "primary",
    "anime_image": base_char_img  # LOCAL PATH
})

# Line 112: Updates DB with local paths (NO CLOUD SYNC)
upsert_asset(entry["id"], {"title": "primary", "cosplay_image": char_img})  # LOCAL PATH

# Line 166: Updates DB with local paths (NO CLOUD SYNC)
upsert_asset(entry["id"], {"title": "primary", "motion_ref_video": final_ref_video})  # LOCAL PATH

# Line 193: Updates DB with local paths (NO CLOUD SYNC)
upsert_asset(entry["id"], {"title": "primary", "motion_ref_video": final_ref_video})  # LOCAL PATH

# Line 205: Updates DB with local paths (NO CLOUD SYNC)
upsert_asset(entry["id"], {"title": "primary", "DELIVERABLE": deliverable_path})  # LOCAL PATH
```

**Cloud Sync Status:** ⚠️ **PARTIAL**
- Calls `run_end_to_end_pipeline()` which has cloud sync ✅
- BUT: Direct DB updates use LOCAL paths (lines 88, 112, 166, 193, 205) ❌

**Action Required:** Add cloud sync after each direct DB update

#### Function: `loop_all_projects()`
```python
# Line 280-286: Updates DB with local paths (NO CLOUD SYNC)
upsert_asset(char_id, {
    "title": "primary",
    "dance_video": fpath,  # LOCAL PATH
    "motion_ref_video": ref_video_path  # LOCAL PATH
})

# Line 296-300: Updates DB with local paths (NO CLOUD SYNC)
upsert_asset(char_id, {
    "title": alt_title,
    "dance_video": fpath,  # LOCAL PATH
    "motion_ref_video": ref_video_path  # LOCAL PATH
})

# Line 308: Updates DB with local paths (NO CLOUD SYNC)
upsert_asset(char_id, {"title": "primary", "DELIVERABLE": deliverable})  # LOCAL PATH
```

**Cloud Sync Status:** ⚠️ **MISSING**
- Registers found files to DB but with LOCAL paths ❌
- Calls `run_remix_pipeline()` which has cloud sync ✅
- But DB updates use LOCAL paths ❌

**Action Required:** Add cloud sync after DB registration

#### Function: `batch_process_redo_folder()`
```python
# Calls run_end_to_end_pipeline() which has cloud sync ✅
```

**Cloud Sync Status:** ✅ **COVERED**
- Uses `run_end_to_end_pipeline()` which has cloud sync

**Action Required:** None

---

### 3. `alignment_pipeline.py`

**Purpose:** Align character image to reference video pose

**Flow:**
```
1. Takes character image + reference video
2. Generates aligned image in temp_process_kling/aligned_inputs/
3. Returns aligned image path
```

**Cloud Sync Status:** ⚠️ **NOT NEEDED**
- Creates INTERMEDIATE files (temp folder)
- These are not final assets
- The aligned image is used immediately by Kling, not stored

**Action Required:** None (intermediate files don't need cloud sync)

---

## 🎯 Summary

| Workflow | Status | Action Needed |
|----------|--------|---------------|
| `batch_new_chars_workflow.py` | ✅ Covered | None |
| `redo_project()` | ⚠️ Partial | Add cloud sync after DB updates |
| `loop_all_projects()` | ⚠️ Missing | Add cloud sync after DB registration |
| `batch_process_redo_folder()` | ✅ Covered | None |
| `alignment_pipeline.py` | ⚠️ Not Needed | None (intermediate) |

---

## 🔧 Fixes Required

### Fix 1: `redo_pipeline.py` - `redo_project()` function

Add cloud sync after each direct DB update:

```python
from utils.cloud_sync import sync_character_images, sync_dance_video

# After line 91 (anime image update):
if os.path.exists(base_char_img):
    try:
        sync_character_images(entry["id"], base_char_img, None)
    except Exception as e:
        print(f"   ⚠️ Cloud sync failed: {e}")

# After line 112 (cosplay image update):
if os.path.exists(char_img):
    try:
        sync_character_images(entry["id"], None, char_img)
    except Exception as e:
        print(f"   ⚠️ Cloud sync failed: {e}")

# After line 205 (DELIVERABLE update):
if deliverable_path and os.path.exists(deliverable_path):
    try:
        sync_dance_video(entry["id"], deliverable_path, "primary_deliverable")
    except Exception as e:
        print(f"   ⚠️ Cloud sync failed: {e}")
```

### Fix 2: `redo_pipeline.py` - `loop_all_projects()` function

```python
from utils.cloud_sync import sync_dance_video

# After line 286 (primary asset registration):
if os.path.exists(fpath):
    try:
        sync_dance_video(char_id, fpath, "primary")
    except Exception as e:
        print(f"   ⚠️ Cloud sync failed: {e}")

# After line 300 (alternate asset registration):
if os.path.exists(fpath):
    try:
        sync_dance_video(char_id, fpath, alt_title)
    except Exception as e:
        print(f"   ⚠️ Cloud sync failed: {e}")

# After line 308 (DELIVERABLE update):
if deliverable and os.path.exists(deliverable):
    try:
        sync_dance_video(char_id, deliverable, "primary_deliverable")
    except Exception as e:
        print(f"   ⚠️ Cloud sync failed: {e}")
```

---

## 📝 Implementation Priority

1. **HIGH:** `redo_pipeline.py` - `redo_project()` 
   - This is actively used for fixing/upgrading projects
   - Leaves DB with local paths if not fixed

2. **HIGH:** `redo_pipeline.py` - `loop_all_projects()`
   - Used for batch finishing all projects
   - Registers files but doesn't sync them

3. **LOW:** `alignment_pipeline.py`
   - No action needed (intermediate files)

---

*End of Audit*
