"""
Instagram Graph API Service for Anime Dance Social Media Pipeline.
Handles publishing Reels and tracking post performance.
"""
import os
import time
import requests
from typing import Optional, Dict, Any
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()


class InstagramService:
    """
    Instagram Graph API service for publishing Reels.
    Uses the Instagram Content Publishing API.
    """
    
    USER_TOKEN = os.getenv("INSTAGRAM_USER_TOKEN")
    GRAPH_API_VERSION = "v18.0"
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    
    def __init__(self):
        """Initialize Instagram service."""
        if not self.USER_TOKEN:
            raise ValueError("INSTAGRAM_USER_TOKEN not set in environment")
        
        self._user_id = None
        print("   📸 Instagram Service initialized")
    
    @property
    def user_id(self) -> str:
        """Get the Instagram Business Account ID."""
        if self._user_id is None:
            self._user_id = self._get_instagram_account_id()
        return self._user_id
    
    def _get_instagram_account_id(self) -> str:
        """Fetch the Instagram Business Account ID from the token."""
        # Try direct approach first (for Page Access Tokens)
        url = f"{self.BASE_URL}/me"
        params = {
            "fields": "instagram_business_account",
            "access_token": self.USER_TOKEN
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        ig_account = data.get("instagram_business_account", {})
        if ig_account.get("id"):
            return ig_account["id"]
        
        # Fallback: Try /me/accounts for User Access Tokens
        url = f"{self.BASE_URL}/me/accounts"
        params = {"access_token": self.USER_TOKEN}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            raise ValueError("No Facebook Pages found for this token")
        
        page_id = data["data"][0]["id"]
        
        # Now get the Instagram account linked to this page
        url = f"{self.BASE_URL}/{page_id}"
        params = {
            "fields": "instagram_business_account",
            "access_token": self.USER_TOKEN
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        ig_account = data.get("instagram_business_account", {})
        if not ig_account.get("id"):
            raise ValueError("No Instagram Business Account linked to this Page")
        
        return ig_account["id"]
    
    def publish_reel(
        self,
        video_url: str,
        caption: str = "",
        share_to_feed: bool = True
    ) -> Dict[str, Any]:
        """
        Publish a video as an Instagram Reel.
        
        The video URL must be publicly accessible. For GCS, use a signed URL.
        
        Args:
            video_url: Public URL to the video file
            caption: Caption text for the post
            share_to_feed: Whether to also share to the main feed
            
        Returns:
            Dict with creation_id, media_id, and status
        """
        print(f"   📤 Publishing Reel to Instagram...")
        
        # Step 1: Create media container
        container_id = self._create_reel_container(video_url, caption, share_to_feed)
        
        # Step 2: Wait for video processing
        status = self._wait_for_processing(container_id)
        
        if status != "FINISHED":
            return {
                "success": False,
                "container_id": container_id,
                "status": status,
                "error": f"Video processing failed with status: {status}"
            }
        
        # Step 3: Publish the container
        media_id = self._publish_container(container_id)
        
        print(f"   ✅ Reel published! Media ID: {media_id}")
        
        return {
            "success": True,
            "container_id": container_id,
            "media_id": media_id,
            "status": "published",
            "published_at": datetime.utcnow().isoformat()
        }
    
    def _create_reel_container(
        self, 
        video_url: str, 
        caption: str, 
        share_to_feed: bool
    ) -> str:
        """Create a Reel media container."""
        url = f"{self.BASE_URL}/{self.user_id}/media"
        
        params = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": str(share_to_feed).lower(),
            "access_token": self.USER_TOKEN
        }
        
        response = requests.post(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        container_id = data.get("id")
        print(f"   📦 Created container: {container_id}")
        
        return container_id
    
    def _wait_for_processing(
        self, 
        container_id: str, 
        max_wait_seconds: int = 300,
        poll_interval: int = 10
    ) -> str:
        """
        Wait for video to finish processing.
        
        Returns:
            Status string: FINISHED, ERROR, EXPIRED, or IN_PROGRESS
        """
        url = f"{self.BASE_URL}/{container_id}"
        params = {
            "fields": "status_code",
            "access_token": self.USER_TOKEN
        }
        
        elapsed = 0
        while elapsed < max_wait_seconds:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            status = data.get("status_code", "UNKNOWN")
            print(f"   ⏳ Processing status: {status} ({elapsed}s)")
            
            if status == "FINISHED":
                return status
            elif status in ["ERROR", "EXPIRED"]:
                return status
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        return "TIMEOUT"
    
    def _publish_container(self, container_id: str) -> str:
        """Publish a processed media container."""
        url = f"{self.BASE_URL}/{self.user_id}/media_publish"
        
        params = {
            "creation_id": container_id,
            "access_token": self.USER_TOKEN
        }
        
        response = requests.post(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        return data.get("id")
    
    def get_media_insights(self, media_id: str) -> Dict[str, int]:
        """
        Get insights for a published media.
        
        Returns:
            Dict with plays, likes, comments, shares, saved, reach
        """
        url = f"{self.BASE_URL}/{media_id}/insights"
        
        params = {
            "metric": "plays,likes,comments,shares,saved,reach",
            "access_token": self.USER_TOKEN
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        insights = {}
        for item in data.get("data", []):
            insights[item["name"]] = item["values"][0]["value"]
        
        return insights
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get basic account information."""
        url = f"{self.BASE_URL}/{self.user_id}"
        
        params = {
            "fields": "username,name,followers_count,media_count",
            "access_token": self.USER_TOKEN
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Instagram API connection."""
        try:
            account_info = self.get_account_info()
            return {
                "status": "connected",
                "username": account_info.get("username"),
                "followers": account_info.get("followers_count"),
                "media_count": account_info.get("media_count")
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Convenience singleton
_instagram_service = None

def get_instagram_service() -> InstagramService:
    """Get or create the Instagram service singleton."""
    global _instagram_service
    if _instagram_service is None:
        _instagram_service = InstagramService()
    return _instagram_service


if __name__ == "__main__":
    # Quick test
    service = InstagramService()
    result = service.test_connection()
    print(f"\n🔗 Connection Test: {result}")
