"""
TikTok Content Publishing API Service for Anime Dance Social Media Pipeline.
Handles video uploads and publishing to TikTok via the official API.

API Documentation: https://developers.tiktok.com/doc/content-posting-api-get-started
"""
import os
import time
import requests
from typing import Optional, Dict, Any
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()


class TikTokService:
    """
    TikTok Content Publishing API service for uploading videos.
    
    Requirements:
    - TikTok Developer App with Content Posting API enabled
    - User authorization with 'video.publish' scope
    - Access token and open_id from OAuth flow
    """
    
    # API Configuration
    BASE_URL = "https://open.tiktokapis.com/v2"
    
    # Environment variables
    ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")
    OPEN_ID = os.getenv("TIKTOK_OPEN_ID")
    
    # Video constraints
    MIN_DURATION_SEC = 3
    MAX_DURATION_SEC = 600  # 10 minutes
    MAX_CAPTION_LENGTH = 2200
    DAILY_POST_LIMIT = 25
    
    def __init__(self):
        """Initialize TikTok service."""
        if not self.ACCESS_TOKEN:
            raise ValueError("TIKTOK_ACCESS_TOKEN not set in environment")
        if not self.OPEN_ID:
            raise ValueError("TIKTOK_OPEN_ID not set in environment")
        
        self._headers = {
            "Authorization": f"Bearer {self.ACCESS_TOKEN}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        
        print("   📱 TikTok Service initialized")
    
    def publish_video_from_url(
        self,
        video_url: str,
        caption: str = "",
        disable_duet: bool = False,
        disable_comment: bool = False,
        disable_stitch: bool = False,
        privacy_level: str = "PUBLIC_TO_EVERYONE"
    ) -> Dict[str, Any]:
        """
        Publish a video to TikTok by pulling from a public URL.
        
        The video URL must be publicly accessible (e.g., signed GCS URL).
        
        Args:
            video_url: Public URL to the video file
            caption: Caption text (max 2200 chars, hashtags included)
            disable_duet: Disable duet feature
            disable_comment: Disable comments
            disable_stitch: Disable stitch feature
            privacy_level: PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, SELF_ONLY
            
        Returns:
            Dict with publish_id and status
        """
        print(f"   📤 Publishing video to TikTok...")
        
        # Validate caption length
        if len(caption) > self.MAX_CAPTION_LENGTH:
            caption = caption[:self.MAX_CAPTION_LENGTH - 3] + "..."
        
        # Step 1: Initialize video upload
        init_result = self._init_video_upload(
            video_url=video_url,
            caption=caption,
            disable_duet=disable_duet,
            disable_comment=disable_comment,
            disable_stitch=disable_stitch,
            privacy_level=privacy_level
        )
        
        if init_result.get("error"):
            return init_result
        
        publish_id = init_result.get("publish_id")
        
        # Step 2: Wait for processing
        status = self._wait_for_processing(publish_id)
        
        if status.get("status") == "PUBLISH_COMPLETE":
            print(f"   ✅ Video published! Publish ID: {publish_id}")
            return {
                "success": True,
                "publish_id": publish_id,
                "status": "published",
                "published_at": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "publish_id": publish_id,
                "status": status.get("status"),
                "error": status.get("fail_reason", "Unknown error")
            }
    
    def _init_video_upload(
        self,
        video_url: str,
        caption: str,
        disable_duet: bool,
        disable_comment: bool,
        disable_stitch: bool,
        privacy_level: str
    ) -> Dict[str, Any]:
        """Initialize video upload using PULL_FROM_URL method."""
        url = f"{self.BASE_URL}/post/publish/video/init/"
        
        payload = {
            "post_info": {
                "title": caption,
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_comment": disable_comment,
                "disable_stitch": disable_stitch
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url
            }
        }
        
        try:
            response = requests.post(
                url,
                headers=self._headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("error", {}).get("code") != "ok":
                return {
                    "success": False,
                    "error": data.get("error", {}).get("message", "Unknown error")
                }
            
            publish_id = data.get("data", {}).get("publish_id")
            print(f"   📦 Upload initiated: {publish_id}")
            
            return {
                "success": True,
                "publish_id": publish_id
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _wait_for_processing(
        self,
        publish_id: str,
        max_wait_seconds: int = 300,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Wait for video processing to complete.
        
        Returns:
            Dict with status and optionally fail_reason
        """
        url = f"{self.BASE_URL}/post/publish/status/fetch/"
        
        elapsed = 0
        while elapsed < max_wait_seconds:
            try:
                response = requests.post(
                    url,
                    headers=self._headers,
                    json={"publish_id": publish_id}
                )
                response.raise_for_status()
                data = response.json()
                
                status = data.get("data", {}).get("status", "UNKNOWN")
                print(f"   ⏳ Processing status: {status} ({elapsed}s)")
                
                if status == "PUBLISH_COMPLETE":
                    return {"status": status}
                elif status in ["FAILED", "SEND_TO_USER_INBOX_FAILED"]:
                    return {
                        "status": status,
                        "fail_reason": data.get("data", {}).get("fail_reason")
                    }
                
                time.sleep(poll_interval)
                elapsed += poll_interval
                
            except requests.exceptions.RequestException as e:
                return {"status": "ERROR", "fail_reason": str(e)}
        
        return {"status": "TIMEOUT", "fail_reason": "Processing timed out"}
    
    def get_creator_info(self) -> Dict[str, Any]:
        """Get information about the authenticated TikTok creator."""
        url = f"{self.BASE_URL}/post/publish/creator_info/query/"
        
        try:
            response = requests.post(url, headers=self._headers, json={})
            response.raise_for_status()
            data = response.json()
            
            creator_info = data.get("data", {})
            return {
                "status": "connected",
                "creator_info": creator_info
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test TikTok API connection."""
        try:
            result = self.get_creator_info()
            if result.get("status") == "connected":
                return {
                    "status": "connected",
                    "privacy_level_options": result.get("creator_info", {}).get("privacy_level_options", []),
                    "max_video_post_duration": result.get("creator_info", {}).get("max_video_post_duration_sec")
                }
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Convenience singleton
_tiktok_service = None

def get_tiktok_service() -> TikTokService:
    """Get or create the TikTok service singleton."""
    global _tiktok_service
    if _tiktok_service is None:
        _tiktok_service = TikTokService()
    return _tiktok_service


if __name__ == "__main__":
    # Quick test
    print("\n🔗 TikTok Service Connection Test")
    print("=" * 40)
    
    try:
        service = TikTokService()
        result = service.test_connection()
        print(f"\nResult: {result}")
    except ValueError as e:
        print(f"\n⚠️  Configuration Error: {e}")
        print("\nRequired environment variables:")
        print("  - TIKTOK_ACCESS_TOKEN")
        print("  - TIKTOK_OPEN_ID")
