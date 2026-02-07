"""
Finalize Cloud Sync
1. Scans output/ for any files not in GCS and uploads them.
2. Repairs broken or local paths in Firestore.
"""
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.gcs_service import GCSService
from services.firestore_service import FirestoreService

def finalize():
    print("="*60)
    print("🚀 FINALIZE CLOUD MIGRATION")
    print("="*60)
    
    gcs = GCSService()
    fs = FirestoreService()
    
    # 1. Scan output directory and upload missing files
    print("\n📤 Syncing raw files from output/ to GCS...")
    output_dir = ROOT / "output"
    extensions = [".mp4", ".png", ".jpg", ".jpeg", ".mp3"]
    
    files_to_check = []
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                files_to_check.append(os.path.join(root, file))
                
    print(f"   Found {len(files_to_check)} local files to verify.")
    
    uploaded = 0
    skipped = 0
    for i, local_path in enumerate(files_to_check):
        try:
            gcs_path = gcs._get_gcs_path(local_path)
            if not gcs.file_exists(gcs_path):
                gcs.upload_file(local_path)
                uploaded += 1
            else:
                skipped += 1
            
            if (i+1) % 50 == 0:
                print(f"   Processed {i+1}/{len(files_to_check)}...")
        except Exception as e:
            print(f"   ❌ Error checking {Path(local_path).name}: {e}")
            
    print(f"✅ GCS Upload Sync: {uploaded} uploaded, {skipped} already in cloud.")

    # 2. Repair Firestore paths
    print("\n🔥 Repairing Firestore local paths...")
    chars = fs.get_all_characters()
    repaired = 0
    missing = 0
    
    for char in chars:
        char_id = char.get("id")
        name = char.get("name", char_id)
        assets = char.get("assets", [])
        changed = False
        
        for asset in assets:
            for key in ["anime_image", "cosplay_image", "dance_video", "primary_dance_video", "DELIVERABLE", "motion_ref_video"]:
                val = asset.get(key)
                if val and isinstance(val, str) and not val.startswith("gs://"):
                    # Try to fix local path
                    local_path = Path(val)
                    
                    # Attempt 1: As is
                    if not local_path.exists():
                        # Attempt 2: Prepend output (if it's a relative path starting with 'characters' or 'dances')
                        if str(val).startswith("characters") or str(val).startswith("dances"):
                            local_path = ROOT / "output" / val
                            
                        # Attempt 3: Insert 'output' into absolute path (for the common bug we saw)
                        if not local_path.exists():
                            path_str = str(val)
                            if "anime_dance_social_media" in path_str and "output" not in path_str:
                                fixed_path = path_str.replace("anime_dance_social_media", os.path.join("anime_dance_social_media", "output"))
                                local_path = Path(fixed_path)
                    
                    if local_path.exists():
                        print(f"   📍 Repairing {name} ({key}): Uploading {local_path.name}")
                        gcs_uri = gcs.upload_file(str(local_path))
                        asset[key] = gcs_uri
                        changed = True
                        repaired += 1
                    else:
                        print(f"   ⚠️ Still missing: {name} ({key}) -> {val}")
                        missing += 1
        
        if changed:
            fs.save_character(char)
            
    print(f"\n✅ Firestore Repair Complete:")
    print(f"   • Repaired: {repaired}")
    print(f"   • Still Missing: {missing}")
    print("="*60)

if __name__ == "__main__":
    finalize()
