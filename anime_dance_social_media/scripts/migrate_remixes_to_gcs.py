"""
Migration Script: Local Remixes → GCS + Firestore

This script scans the 'remixes' directory, identifies the 3 specific watermarked versions 
requested by the user, uploads them to GCS, and registers them in the Firestore 
character assets.

Target Files:
1. [kpop_soundtrack]_REMIX_JENNIE_{...}_watermarked.mp4
2. [orig_soundtrack]_REMIX_JENNIE_{...}_watermarked.mp4
3. REMIX_JENNIE_{...}_structured_scored_watermarked.mp4
"""

import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.gcs_service import GCSService
from services.firestore_service import FirestoreService
from config import config

def migrate_remixes(dry_run=False):
    print("\n" + "="*60)
    print("   🚀 Migrating Final Remixes to Cloud")
    print("="*60 + "\n")

    gcs = GCSService()
    firestore = FirestoreService()
    
    remixes_dir = ROOT / "output" / "remixes"
    if not remixes_dir.exists():
        print(f"❌ Remixes directory not found: {remixes_dir}")
        return

    # 1. Get all characters from Firestore
    print("📖 Fetching characters from Firestore...")
    characters = firestore.get_all_characters()
    char_map = {c['id']: c for c in characters}
    print(f"   Total characters: {len(characters)}")

    # 2. Iterate through remix folders
    remix_folders = [d for d in remixes_dir.iterdir() if d.is_dir()]
    print(f"   Found {len(remix_folders)} remix folders\n")

    uploaded_count = 0
    updated_count = 0

    for folder in remix_folders:
        folder_name = folder.name
        print(f"📂 Processing: {folder_name}")

        # Extract Character ID and Ref ID from folder name
        # Format: dance_ID_cosplay_on_REFID
        char_id = None
        ref_id = None
        if folder_name.startswith("dance_") and "_cosplay_on_" in folder_name:
            parts = folder_name[6:].split("_cosplay_on_")
            char_id = parts[0]
            ref_id = parts[1]
        
        if not char_id or char_id not in char_map:
            # Fallback: maybe the folder name is different?
            # Let's try to find an ID that is contained in the folder name
            matched_id = None
            for cid in char_map:
                if cid in folder_name:
                    matched_id = cid
                    break
            
            if matched_id:
                char_id = matched_id
                print(f"   ℹ️  Partial match found: {char_id}")
            else:
                print(f"   ⚠️  Could not find character ID for '{folder_name}' in Firestore. Skipping.")
                continue

        target_char = char_map[char_id]
        
        # 3. Find which asset this folder belongs to
        target_asset = None
        for asset in target_char.get("assets", []):
            dv = asset.get("dance_video") or ""
            mv = asset.get("motion_ref_video") or ""
            if ref_id and (ref_id in dv or ref_id in mv):
                target_asset = asset
                break
        
        asset_title = None
        if target_asset:
            asset_title = target_asset["title"]
        else:
            # If no asset matches the ref_id, we will create a NEW asset entry
            # with title remix_REFID
            asset_title = f"remix_{ref_id}" if ref_id else "remix_generic"
            print(f"   ℹ️  Asset for ref '{ref_id}' not found. Will create new asset: {asset_title}")

        # 4. Identify target files
        files_to_upload = {} # label -> local_path
        
        # Result subfolder
        result_dir = folder / "result"
        
        # Pattern 1: [kpop_soundtrack]_REMIX_JENNIE_{...}_watermarked.mp4
        kpop_path = result_dir / f"[kpop_soundtrack]_REMIX_JENNIE_{folder_name}_watermarked.mp4"
        if kpop_path.exists():
            files_to_upload["remix_kpop_watermarked"] = str(kpop_path)
        
        # Pattern 2: [orig_soundtrack]_REMIX_JENNIE_{...}_watermarked.mp4
        orig_path = result_dir / f"[orig_soundtrack]_REMIX_JENNIE_{folder_name}_watermarked.mp4"
        if orig_path.exists():
            files_to_upload["remix_orig_watermarked"] = str(orig_path)
            
        # Pattern 3: REMIX_JENNIE_{...}_structured_scored_watermarked.mp4
        struc_path = result_dir / f"REMIX_JENNIE_{folder_name}_structured_scored_watermarked.mp4"
        if not struc_path.exists():
            struc_path = folder / f"REMIX_JENNIE_{folder_name}_structured_scored_watermarked.mp4"
            
        if struc_path.exists():
            files_to_upload["remix_structured_watermarked"] = str(struc_path)

        if not files_to_upload:
            print(f"   ⚠️  No target watermarked files found in this folder. Skipping.")
            continue

        # 5. Upload to GCS and update Firestore
        if dry_run:
            print(f"   🔍 Dry run: Would upload {len(files_to_upload)} files for {char_id} (Asset: {asset_title})")
            continue

        updates = {}
        for label, local_path in files_to_upload.items():
            try:
                gcs_uri = gcs.upload_file(local_path)
                updates[label] = gcs_uri
                uploaded_count += 1
            except Exception as e:
                print(f"   ❌ Error uploading {label}: {e}")

        if updates:
            # Check if asset exists in Firestore record (local map might be stale but firestore is source of truth)
            # Actually we use our firestore service to handle the heavy lifting
            
            # Check if asset exists by title
            asset_exists = any(a.get("title") == asset_title for a in target_char.get("assets", []))
            
            if not asset_exists:
                # Create a minimal new asset entry
                new_asset = {
                    "title": asset_title,
                    "motion_ref_video": f"https://www.youtube.com/watch?v={ref_id}" if ref_id and len(ref_id) == 11 else ref_id,
                    **updates
                }
                success = firestore.add_character_asset(char_id, new_asset)
            else:
                success = firestore.update_character_asset(char_id, asset_title, updates)
                
            if success:
                print(f"   ✅ Updated Firestore for {char_id} (Asset: {asset_title})")
                updated_count += 1
            else:
                print(f"   ❌ Failed to update Firestore for {char_id}")

    print("\n" + "="*60)
    print("   ✅ REMIX MIGRATION COMPLETE")
    print("="*60)
    print(f"   - Folders processed: {len(remix_folders)}")
    print(f"   - Files uploaded: {uploaded_count}")
    print(f"   - Assets updated: {updated_count}\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    migrate_remixes(dry_run=args.dry_run)
