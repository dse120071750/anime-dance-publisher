"""
Migration Script: Local Files → GCS + Firestore

One-time migration script to:
1. Upload all media files from output/ to GCS
2. Migrate character_db.json to Firestore
3. Transform local paths to GCS URIs

Usage:
    python -m scripts.migrate_to_gcs --dry-run    # Preview changes
    python -m scripts.migrate_to_gcs              # Run migration
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.gcs_service import GCSService
from services.firestore_service import FirestoreService


def load_local_character_db() -> list:
    """Load the existing character_db.json."""
    db_path = ROOT / "output" / "characters" / "character_db.json"
    
    if not db_path.exists():
        print(f"❌ Character DB not found: {db_path}")
        return []
    
    with open(db_path, "r", encoding="utf-8") as f:
        return json.load(f)


def backup_character_db():
    """Create a timestamped backup of character_db.json."""
    db_path = ROOT / "output" / "characters" / "character_db.json"
    
    if db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = ROOT / "output" / "characters" / f"character_db_backup_{timestamp}.json"
        
        with open(db_path, "r", encoding="utf-8") as f:
            data = f.read()
        
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(data)
        
        print(f"   💾 Backup created: {backup_path.name}")
        return backup_path
    
    return None


def collect_files_to_upload(characters: list) -> list:
    """
    Extract all file paths from character data that need uploading.
    
    Returns:
        List of tuples: (local_path, gcs_path, field_name, char_id, asset_idx)
    """
    files = []
    
    # File fields to check in assets
    file_fields = [
        "anime_image",
        "cosplay_image", 
        "dance_video",
        "motion_ref_video",
        "DELIVERABLE"
    ]
    
    for char in characters:
        char_id = char.get("id", "unknown")
        
        for asset_idx, asset in enumerate(char.get("assets", [])):
            for field in file_fields:
                path_value = asset.get(field)
                
                if path_value and isinstance(path_value, str):
                    # Skip if already a GCS path
                    if path_value.startswith("gs://"):
                        continue
                    
                    # Check if file exists
                    local_path = Path(path_value)
                    if local_path.exists():
                        files.append({
                            "local_path": str(local_path),
                            "field": field,
                            "char_id": char_id,
                            "asset_idx": asset_idx
                        })
    
    return files


def run_migration(dry_run: bool = False):
    """Run the full migration."""
    print("\n" + "="*60)
    print("   🚀 GCS + Firestore Migration")
    print("="*60 + "\n")
    
    if dry_run:
        print("   ⚠️  DRY RUN MODE - No changes will be made\n")
    
    # Step 1: Load character data
    print("📖 Loading character_db.json...")
    characters = load_local_character_db()
    print(f"   Found {len(characters)} characters\n")
    
    if not characters:
        print("❌ No characters to migrate. Exiting.")
        return
    
    # Step 2: Collect files to upload
    print("🔍 Scanning for files to upload...")
    files_to_upload = collect_files_to_upload(characters)
    print(f"   Found {len(files_to_upload)} files to upload\n")
    
    # Preview files
    print("📁 Files to upload (first 10):")
    for f in files_to_upload[:10]:
        print(f"   • {Path(f['local_path']).name} ({f['field']})")
    if len(files_to_upload) > 10:
        print(f"   ... and {len(files_to_upload) - 10} more\n")
    
    if dry_run:
        print("\n✅ Dry run complete. Run without --dry-run to execute migration.")
        return
    
    # Step 3: Create backup
    print("\n💾 Creating backup...")
    backup_character_db()
    
    # Step 4: Initialize services
    print("\n🌐 Initializing cloud services...")
    gcs = GCSService()
    firestore = FirestoreService()
    
    # Step 5: Upload files and build path mapping
    print("\n📤 Uploading files to GCS...")
    path_mapping = {}  # local_path -> gcs_uri
    
    uploaded = 0
    skipped = 0
    errors = 0
    
    for i, file_info in enumerate(files_to_upload):
        local_path = file_info["local_path"]
        
        try:
            # Check if already exists in GCS
            gcs_path = gcs._get_gcs_path(local_path)
            
            if gcs.file_exists(gcs_path):
                skipped += 1
                gcs_uri = f"gs://{gcs.BUCKET_NAME}/{gcs_path}"
            else:
                gcs_uri = gcs.upload_file(local_path)
                uploaded += 1
            
            path_mapping[local_path] = gcs_uri
            
            # Progress
            if (i + 1) % 50 == 0:
                print(f"   Progress: {i + 1}/{len(files_to_upload)}")
                
        except Exception as e:
            print(f"   ❌ Error uploading {Path(local_path).name}: {e}")
            errors += 1
    
    print(f"\n   ✅ Uploaded: {uploaded}, Skipped: {skipped}, Errors: {errors}")
    
    # Step 6: Update character data with GCS paths
    print("\n🔄 Updating character paths...")
    
    for char in characters:
        for asset in char.get("assets", []):
            for field in ["anime_image", "cosplay_image", "dance_video", 
                          "motion_ref_video", "DELIVERABLE"]:
                old_path = asset.get(field)
                if old_path and old_path in path_mapping:
                    asset[field] = path_mapping[old_path]
    
    # Step 7: Write to Firestore
    print("\n🔥 Writing to Firestore...")
    
    for char in characters:
        try:
            firestore.save_character(char)
        except Exception as e:
            print(f"   ❌ Error saving {char.get('id')}: {e}")
    
    print(f"\n   ✅ Migrated {len(characters)} characters to Firestore")
    
    # Step 8: Summary
    print("\n" + "="*60)
    print("   ✅ MIGRATION COMPLETE")
    print("="*60)
    print(f"""
Summary:
   • Characters migrated: {len(characters)}
   • Files uploaded: {uploaded}
   • Files skipped (already exist): {skipped}
   • Errors: {errors}
   
Next steps:
   1. Verify data in GCS Console
   2. Verify data in Firestore Console
   3. Update workflows to use cloud services
""")


def main():
    parser = argparse.ArgumentParser(description="Migrate local files to GCS + Firestore")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    args = parser.parse_args()
    
    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
