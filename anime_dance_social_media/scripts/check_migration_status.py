"""
Cloud Migration Status Check Script
Checks GCS and Firestore to verify all dance videos have been uploaded.
"""
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.gcs_service import GCSService
from services.firestore_service import FirestoreService


def check_migration_status():
    print("=" * 60)
    print("🔍 CLOUD MIGRATION STATUS CHECK")
    print("=" * 60)

    # 1. GCS Check
    print("\n📦 GCS STORAGE CHECK")
    print("-" * 40)
    gcs = GCSService()

    # List all dances
    dance_files = gcs.list_files(prefix="anime_dance/dances/")
    dance_videos = [f for f in dance_files if f.endswith(".mp4")]
    dance_images = [f for f in dance_files if f.endswith(".png")]
    print(f"   Dance videos in GCS: {len(dance_videos)}")
    print(f"   Dance images (thumbnails/swapped): {len(dance_images)}")

    # List characters
    char_files = gcs.list_files(prefix="anime_dance/characters/")
    print(f"   Character files in GCS: {len(char_files)}")

    # List remixes
    remix_files = gcs.list_files(prefix="anime_dance/remixes/")
    print(f"   Remix files in GCS: {len(remix_files)}")

    # Total summary
    total_files = len(gcs.list_files())
    print(f"\n   📊 Total files in anime_dance/*: {total_files}")

    # 2. Firestore Check
    print("\n🔥 FIRESTORE CHECK")
    print("-" * 40)
    fs = FirestoreService()

    char_count = fs.get_character_count()
    print(f"   Total characters in Firestore: {char_count}")

    # Get all characters and count assets
    all_chars = fs.get_all_characters()
    total_assets = 0
    chars_with_dances = 0
    dance_count_total = 0

    for char in all_chars:
        assets = char.get("assets", [])
        total_assets += len(assets)
        for asset in assets:
            dance = (
                asset.get("dance_video")
                or asset.get("primary_dance_video")
                or asset.get("DELIVERABLE")
            )
            if dance:
                chars_with_dances += 1
                break
        # Count actual dance entries
        for asset in assets:
            if (
                asset.get("dance_video")
                or asset.get("primary_dance_video")
                or asset.get("DELIVERABLE")
            ):
                dance_count_total += 1

    print(f"   Total assets across all characters: {total_assets}")
    print(f"   Characters with dance videos: {chars_with_dances}")
    print(f"   Total dance video entries: {dance_count_total}")

    # 3. Path verification - check if paths in Firestore are GCS URIs
    print("\n🔗 PATH VERIFICATION (GCS vs Local)")
    print("-" * 40)
    
    gcs_paths = 0
    local_paths = 0
    path_examples = {"gcs": [], "local": []}
    
    for char in all_chars:
        for asset in char.get("assets", []):
            for key in ["dance_video", "primary_dance_video", "DELIVERABLE", "cosplay_image", "anime_image"]:
                val = asset.get(key)
                if val:
                    if val.startswith("gs://"):
                        gcs_paths += 1
                        if len(path_examples["gcs"]) < 3:
                            path_examples["gcs"].append({"char": char.get("name"), "key": key, "path": val})
                    else:
                        local_paths += 1
                        if len(path_examples["local"]) < 5:
                            path_examples["local"].append({"char": char.get("name"), "key": key, "path": val})

    print(f"   ✅ GCS URIs found: {gcs_paths}")
    print(f"   ❌ Local paths found: {local_paths}")
    
    if gcs_paths > 0:
        print("\n   Sample GCS paths:")
        for ex in path_examples["gcs"]:
            print(f"      {ex['char']} - {ex['key']}: {ex['path'][:70]}...")
    
    if local_paths > 0:
        print("\n   ⚠️ WARNING: Local paths detected (not migrated):")
        for ex in path_examples["local"]:
            print(f"      {ex['char']} - {ex['key']}: {ex['path'][:50]}...")

    # 4. Comparison - Local vs Cloud
    print("\n📊 LOCAL VS CLOUD COMPARISON")
    print("-" * 40)
    
    import os
    local_dances_dir = ROOT / "output" / "dances"
    if local_dances_dir.exists():
        local_dance_videos = [f for f in local_dances_dir.iterdir() if f.suffix == ".mp4"]
        local_dance_images = [f for f in local_dances_dir.iterdir() if f.suffix == ".png"]
        print(f"   Local dance videos: {len(local_dance_videos)}")
        print(f"   Local dance images: {len(local_dance_images)}")
        print(f"   GCS dance videos: {len(dance_videos)}")
        print(f"   GCS dance images: {len(dance_images)}")
        
        # Migration status
        video_diff = len(local_dance_videos) - len(dance_videos)
        if video_diff == 0:
            print(f"\n   ✅ VIDEO MIGRATION: COMPLETE (all {len(local_dance_videos)} videos uploaded)")
        elif video_diff > 0:
            print(f"\n   ⚠️ VIDEO MIGRATION: INCOMPLETE ({video_diff} videos not yet uploaded)")
        else:
            print(f"\n   ✅ VIDEO MIGRATION: MORE FILES IN CLOUD ({-video_diff} extra in GCS)")

    # 5. Generate summary
    print("\n" + "=" * 60)
    print("📋 MIGRATION SUMMARY")
    print("=" * 60)
    
    summary = {
        "gcs_dance_videos": len(dance_videos),
        "gcs_dance_images": len(dance_images),
        "gcs_character_files": len(char_files),
        "gcs_remix_files": len(remix_files),
        "gcs_total_files": total_files,
        "firestore_characters": char_count,
        "firestore_total_assets": total_assets,
        "firestore_chars_with_dances": chars_with_dances,
        "firestore_dance_entries": dance_count_total,
        "paths_gcs": gcs_paths,
        "paths_local": local_paths,
        "migration_complete": local_paths == 0 and gcs_paths > 0,
    }
    
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    
    return summary


if __name__ == "__main__":
    check_migration_status()
