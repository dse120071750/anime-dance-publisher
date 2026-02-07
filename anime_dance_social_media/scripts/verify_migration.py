"""
Verification script for GCS and Firestore migration.
Checks if files exist in GCS and documents exist in Firestore.
"""
import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.gcs_service import GCSService
from services.firestore_service import FirestoreService

def verify():
    print("\n" + "="*60)
    print("   🔍 Cloud Migration Verification")
    print("="*60 + "\n")

    # 1. Verify GCS
    print("🌐 Verifying GCS Storage...")
    gcs = GCSService()
    gcs_status = gcs.test_connection()
    print(f"   Bucket: {gcs_status.get('bucket')} (Status: {gcs_status.get('status')})")
    
    files = gcs.list_files(prefix="anime_dance/characters/")
    print(f"   Found {len(files)} files in anime_dance/characters/")
    if files:
        print(f"   Sample file: {files[0]}")
    
    # 2. Verify Firestore
    print("\n🔥 Verifying Firestore Database...")
    firestore = FirestoreService()
    fs_status = firestore.test_connection()
    print(f"   Collections: {fs_status.get('collections')} (Status: {fs_status.get('status')})")
    
    char_count = firestore.get_character_count()
    print(f"   Total characters in Firestore: {char_count}")
    
    if char_count > 0:
        chars = firestore.get_all_characters()
        sample_char = chars[0]
        print(f"   Sample Character: {sample_char.get('name')} ({sample_char.get('id')})")
        
        # Check first asset path
        assets = sample_char.get('assets', [])
        if assets:
            first_asset = assets[0]
            print(f"   Sample Asset Path: {first_asset.get('anime_image')}")
            if first_asset.get('anime_image', '').startswith('gs://'):
                print("   ✅ Path verification: GCS URI detected")
            else:
                print("   ❌ Path verification: LOCAL PATH detected (Migration Failure?)")

    print("\n" + "="*60)
    print("   ✅ VERIFICATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    verify()
