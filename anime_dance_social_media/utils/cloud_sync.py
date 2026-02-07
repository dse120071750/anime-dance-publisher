"""
Cloud Sync Utilities for Anime Dance Pipeline

This module provides automatic upload to GCS and Firestore updates
for all assets created by the pipeline workflows.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.gcs_service import GCSService
from services.firestore_service import FirestoreService


class CloudSyncManager:
    """
    Manager for automatic cloud synchronization of pipeline assets.
    """
    
    def __init__(self):
        self.gcs = GCSService()
        self.fs = FirestoreService()
        self._upload_cache = {}  # Prevent duplicate uploads
    
    def upload_and_sync(
        self,
        local_path: str,
        char_id: str,
        asset_title: str,
        asset_fields: Dict[str, str],
        make_public: bool = False
    ) -> Dict[str, Any]:
        """
        Upload a file to GCS and update Firestore with GCS URIs.
        
        Args:
            local_path: Path to local file
            char_id: Character ID
            asset_title: Asset title (e.g., 'primary', 'jennie_kpop')
            asset_fields: Dict mapping field names to local paths
                         e.g., {"anime_image": local_path, "cosplay_image": cosplay_path}
            make_public: Whether to make GCS objects public
            
        Returns:
            Dict with gcs_uris for each field
        """
        if not local_path or not os.path.exists(local_path):
            print(f"   ⚠️ CloudSync: File not found: {local_path}")
            return {}
        
        # Check cache to avoid re-uploading
        file_mtime = os.path.getmtime(local_path)
        cache_key = f"{local_path}:{file_mtime}"
        if cache_key in self._upload_cache:
            print(f"   ☁️ CloudSync: Using cached upload for {os.path.basename(local_path)}")
            return self._upload_cache[cache_key]
        
        results = {}
        
        # Upload each file in asset_fields
        for field_name, file_path in asset_fields.items():
            if not file_path or not os.path.exists(file_path):
                continue
                
            try:
                # Upload to GCS
                gcs_uri = self.gcs.upload_file(file_path, make_public=make_public)
                public_url = self.gcs.get_public_url(gcs_uri)
                
                results[field_name] = {
                    "gcs_uri": gcs_uri,
                    "public_url": public_url,
                    "local_path": file_path
                }
                
                print(f"   ☁️ Uploaded {field_name}: {os.path.basename(file_path)}")
                
            except Exception as e:
                print(f"   ❌ CloudSync upload failed for {field_name}: {e}")
                results[field_name] = {
                    "error": str(e),
                    "local_path": file_path
                }
        
        # Update Firestore with GCS URIs
        if results:
            try:
                firestore_updates = {
                    k: v["gcs_uri"] for k, v in results.items() 
                    if "gcs_uri" in v
                }
                
                if firestore_updates:
                    firestore_updates["title"] = asset_title
                    self.fs.add_character_asset(char_id, firestore_updates)
                    print(f"   🔥 Firestore updated for {char_id}/{asset_title}")
                    
            except Exception as e:
                print(f"   ❌ CloudSync Firestore update failed: {e}")
        
        # Cache the result
        self._upload_cache[cache_key] = results
        return results
    
    def upload_character_images(
        self,
        char_id: str,
        anime_image_path: str,
        cosplay_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload character images and update Firestore.
        """
        asset_fields = {"anime_image": anime_image_path}
        if cosplay_image_path and os.path.exists(cosplay_image_path):
            asset_fields["cosplay_image"] = cosplay_image_path
        
        return self.upload_and_sync(
            local_path=anime_image_path,
            char_id=char_id,
            asset_title="primary",
            asset_fields=asset_fields,
            make_public=True
        )
    
    def upload_dance_video(
        self,
        char_id: str,
        dance_video_path: str,
        asset_title: str = "primary"
    ) -> Dict[str, Any]:
        """
        Upload dance video and update Firestore.
        """
        return self.upload_and_sync(
            local_path=dance_video_path,
            char_id=char_id,
            asset_title=asset_title,
            asset_fields={"dance_video": dance_video_path},
            make_public=True
        )
    
    def upload_remix_assets(
        self,
        char_id: str,
        remix_dir: str,
        variant_type: str = "jennie_kpop"
    ) -> Dict[str, Any]:
        """
        Upload all assets from a remix directory.
        """
        results = {}
        
        # Find all video files in remix dir
        remix_path = Path(remix_dir)
        if not remix_path.exists():
            print(f"   ⚠️ Remix dir not found: {remix_dir}")
            return results
        
        # Upload variant videos
        variants_dir = remix_path / "variants"
        if variants_dir.exists():
            for video_file in variants_dir.glob("*.mp4"):
                variant_name = video_file.stem
                upload_result = self.upload_and_sync(
                    local_path=str(video_file),
                    char_id=char_id,
                    asset_title=variant_name,
                    asset_fields={"dance_video": str(video_file)},
                    make_public=True
                )
                results[variant_name] = upload_result
        
        # Upload result files (final outputs)
        result_dir = remix_path / "result"
        if result_dir.exists():
            result_fields = {}
            
            # Find specific output files
            for pattern in ["*_watermarked.mp4", "[kpop_]*.mp4", "[orig_]*.mp4", "*.mp3"]:
                for file_path in result_dir.glob(pattern):
                    field_name = file_path.stem.replace("[", "").replace("]", "_")
                    result_fields[field_name] = str(file_path)
            
            if result_fields:
                upload_result = self.upload_and_sync(
                    local_path=str(result_dir),  # Dummy, using fields
                    char_id=char_id,
                    asset_title=f"{variant_type}_final",
                    asset_fields=result_fields,
                    make_public=True
                )
                results["final_outputs"] = upload_result
        
        # Upload main remix file (in root of remix_dir)
        for remix_file in remix_path.glob("REMIX_*.mp4"):
            upload_result = self.upload_and_sync(
                local_path=str(remix_file),
                char_id=char_id,
                asset_title="remix_main",
                asset_fields={"deliverable": str(remix_file)},
                make_public=True
            )
            results["main_remix"] = upload_result
        
        return results
    
    def upload_soundtrack_versions(
        self,
        char_id: str,
        result_dir: str,
        base_name: str
    ) -> Dict[str, Any]:
        """
        Upload soundtrack variants (kpop/orig) and update Firestore.
        """
        result_path = Path(result_dir)
        asset_fields = {}
        
        # Find soundtrack versions
        patterns = {
            "kpop_video": f"[kpop_soundtrack]*{base_name}*.mp4",
            "orig_video": f"[orig_soundtrack]*{base_name}*.mp4",
            "kpop_audio": "generated_kpop_music.mp3",
            "orig_audio": "orig_music.mp3"
        }
        
        for field_name, pattern in patterns.items():
            matching_files = list(result_path.glob(pattern))
            if matching_files:
                asset_fields[field_name] = str(matching_files[0])
        
        if not asset_fields:
            print(f"   ⚠️ No soundtrack files found in {result_dir}")
            return {}
        
        return self.upload_and_sync(
            local_path=str(result_path),
            char_id=char_id,
            asset_title="soundtracks",
            asset_fields=asset_fields,
            make_public=True
        )


# Global instance for convenience
_cloud_sync = None

def get_cloud_sync() -> CloudSyncManager:
    """Get or create the CloudSyncManager singleton."""
    global _cloud_sync
    if _cloud_sync is None:
        _cloud_sync = CloudSyncManager()
    return _cloud_sync


# Convenience functions for direct import
def sync_character_images(char_id: str, anime_image: str, cosplay_image: str = None):
    """Upload character images to cloud."""
    return get_cloud_sync().upload_character_images(char_id, anime_image, cosplay_image)

def sync_dance_video(char_id: str, dance_video: str, asset_title: str = "primary"):
    """Upload dance video to cloud."""
    return get_cloud_sync().upload_dance_video(char_id, dance_video, asset_title)

def sync_remix_directory(char_id: str, remix_dir: str, variant_type: str = "jennie_kpop"):
    """Upload all remix assets to cloud."""
    return get_cloud_sync().upload_remix_assets(char_id, remix_dir, variant_type)

def sync_soundtracks(char_id: str, result_dir: str, base_name: str):
    """Upload soundtrack versions to cloud."""
    return get_cloud_sync().upload_soundtrack_versions(char_id, result_dir, base_name)


if __name__ == "__main__":
    # Test
    sync = CloudSyncManager()
    print(f"CloudSyncManager initialized")
    print(f"GCS Bucket: {sync.gcs.BUCKET_NAME}")
    print(f"Firestore Project: {sync.fs.PROJECT_ID}")
