"""
Firestore Service for Anime Dance Social Media Pipeline.
Handles character data, dance jobs, and Instagram post tracking.
Uses nisan-n8n service account for authentication.
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    from google.cloud import firestore
    from google.oauth2 import service_account
except ImportError:
    raise ImportError("Please install google-cloud-firestore: pip install google-cloud-firestore")

from dotenv import load_dotenv
load_dotenv()


class FirestoreService:
    """
    Firestore service wrapper for the anime dance pipeline.
    Replaces the local character_db.json with cloud-based storage.
    """
    
    PROJECT_ID = os.getenv("GCP_PROJECT_ID", "nisan-n8n")
    CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    DATABASE_ID = os.getenv("FIRESTORE_DATABASE", "(default)")
    
    # Collection names
    CHARACTERS_COLLECTION = "characters"
    DANCE_JOBS_COLLECTION = "dance_jobs"
    INSTAGRAM_POSTS_COLLECTION = "instagram_posts"
    
    def __init__(self):
        """Initialize Firestore client with service account credentials."""
        if self.CREDENTIALS_PATH and os.path.exists(self.CREDENTIALS_PATH):
            credentials = service_account.Credentials.from_service_account_file(
                self.CREDENTIALS_PATH
            )
            self.db = firestore.Client(
                project=self.PROJECT_ID,
                credentials=credentials,
                database=self.DATABASE_ID
            )
        else:
            # Fall back to default credentials (ADC)
            self.db = firestore.Client(
                project=self.PROJECT_ID,
                database=self.DATABASE_ID
            )
        
        print(f"   🔥 Firestore Service initialized: {self.PROJECT_ID}/{self.DATABASE_ID}")
    
    # ========== Character Operations ==========
    
    def save_character(self, character_data: dict) -> str:
        """
        Save or update a character document.
        
        Args:
            character_data: Character dict with 'id', 'name', 'anime', 'assets', etc.
            
        Returns:
            Document ID
        """
        char_id = character_data.get("id")
        if not char_id:
            raise ValueError("Character data must include 'id' field")
        
        # Add timestamp
        character_data["updated_at"] = firestore.SERVER_TIMESTAMP
        
        doc_ref = self.db.collection(self.CHARACTERS_COLLECTION).document(char_id)
        doc_ref.set(character_data, merge=True)
        
        print(f"   💾 Saved character: {char_id}")
        return char_id
    
    def get_character(self, char_id: str) -> Optional[dict]:
        """
        Get a character by ID.
        
        Args:
            char_id: Character document ID
            
        Returns:
            Character dict or None if not found
        """
        doc_ref = self.db.collection(self.CHARACTERS_COLLECTION).document(char_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        return None
    
    def get_all_characters(self) -> List[dict]:
        """
        Get all characters from Firestore.
        Replacement for load_character_db().
        
        Returns:
            List of character dicts
        """
        docs = self.db.collection(self.CHARACTERS_COLLECTION).stream()
        return [doc.to_dict() for doc in docs]
    
    def update_character_asset(
        self, 
        char_id: str, 
        asset_title: str, 
        updates: dict
    ) -> bool:
        """
        Update a specific asset within a character's assets array.
        
        Args:
            char_id: Character document ID
            asset_title: Title of the asset to update (e.g., 'primary', 'jennie_kpop')
            updates: Dict of fields to update within the asset
            
        Returns:
            True if updated, False if character not found
        """
        doc_ref = self.db.collection(self.CHARACTERS_COLLECTION).document(char_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return False
        
        char_data = doc.to_dict()
        assets = char_data.get("assets", [])
        
        updated = False
        # Find and update the matching asset
        for asset in assets:
            if asset.get("title") == asset_title:
                asset.update(updates)
                updated = True
                break
        
        if updated:
            # Save back
            doc_ref.update({"assets": assets, "updated_at": firestore.SERVER_TIMESTAMP})
            print(f"   📝 Updated asset '{asset_title}' for {char_id}")
            return True
        return False

    def add_character_asset(self, char_id: str, new_asset: dict) -> bool:
        """
        Add a new asset to a character's assets list.
        
        Args:
            char_id: Character ID
            new_asset: Asset dict (must include 'title')
            
        Returns:
            True if added, False if character not found
        """
        if "title" not in new_asset:
            raise ValueError("Asset must include a 'title'")
            
        doc_ref = self.db.collection(self.CHARACTERS_COLLECTION).document(char_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return False
            
        char_data = doc.to_dict()
        assets = char_data.get("assets", [])
        
        # Check if already exists, if so update it
        for i, asset in enumerate(assets):
            if asset.get("title") == new_asset["title"]:
                assets[i].update(new_asset)
                doc_ref.update({"assets": assets, "updated_at": firestore.SERVER_TIMESTAMP})
                print(f"   📝 Updated existing asset '{new_asset['title']}' for {char_id}")
                return True
            
        # Otherwise append new asset
        assets.append(new_asset)
        doc_ref.update({"assets": assets, "updated_at": firestore.SERVER_TIMESTAMP})
        print(f"   ➕ Added new asset '{new_asset['title']}' for {char_id}")
        return True
    
    def query_characters(
        self, 
        anime: Optional[str] = None,
        has_deliverable: Optional[bool] = None,
        limit: int = 100
    ) -> List[dict]:
        """
        Query characters with filters.
        
        Args:
            anime: Filter by anime name
            has_deliverable: Filter by whether character has a deliverable video
            limit: Max results to return
            
        Returns:
            List of matching character dicts
        """
        query = self.db.collection(self.CHARACTERS_COLLECTION)
        
        if anime:
            query = query.where("anime", "==", anime)
        
        query = query.limit(limit)
        
        results = [doc.to_dict() for doc in query.stream()]
        
        # Client-side filter for has_deliverable (nested field)
        if has_deliverable is not None:
            filtered = []
            for char in results:
                has_del = any(
                    asset.get("DELIVERABLE") or asset.get("deliverable")
                    for asset in char.get("assets", [])
                )
                if has_del == has_deliverable:
                    filtered.append(char)
            results = filtered
        
        return results
    
    def delete_character(self, char_id: str) -> bool:
        """Delete a character document."""
        doc_ref = self.db.collection(self.CHARACTERS_COLLECTION).document(char_id)
        if doc_ref.get().exists:
            doc_ref.delete()
            print(f"   🗑️ Deleted character: {char_id}")
            return True
        return False
    
    # ========== Dance Job Operations ==========
    
    def create_dance_job(
        self, 
        char_id: str, 
        motion_ref_video: str, 
        status: str = "pending"
    ) -> str:
        """
        Create a new dance generation job record.
        
        Args:
            char_id: Character ID
            motion_ref_video: GCS path to motion reference video
            status: Job status (pending, processing, completed, failed)
            
        Returns:
            Job document ID
        """
        job_data = {
            "character_id": char_id,
            "motion_ref_video": motion_ref_video,
            "status": status,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = self.db.collection(self.DANCE_JOBS_COLLECTION).add(job_data)
        job_id = doc_ref[1].id
        
        print(f"   📋 Created dance job: {job_id}")
        return job_id
    
    def update_dance_job(self, job_id: str, updates: dict) -> None:
        """Update a dance job record."""
        updates["updated_at"] = firestore.SERVER_TIMESTAMP
        self.db.collection(self.DANCE_JOBS_COLLECTION).document(job_id).update(updates)
    
    # ========== Instagram Post Operations ==========
    
    def save_instagram_post(
        self,
        char_id: str,
        asset_title: str,
        media_url: str,
        status: str = "draft",
        post_id: str = None
    ) -> str:
        """
        Save an Instagram post record.
        
        Args:
            char_id: Character ID
            asset_title: Asset title being posted
            media_url: GCS URL of the media
            status: Post status (draft, scheduled, published, failed)
            post_id: Instagram media ID
            
        Returns:
            Post document ID
        """
        post_data = {
            "character_id": char_id,
            "asset_title": asset_title,
            "media_url": media_url,
            "status": status,
            "post_id": post_id,
            "published_at": firestore.SERVER_TIMESTAMP if status == "published" else None,
            "insights": {"likes": 0, "comments": 0, "views": 0},
            "created_at": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = self.db.collection(self.INSTAGRAM_POSTS_COLLECTION).add(post_data)
        return doc_ref[1].id
    
    def update_instagram_post(self, doc_id: str, updates: dict) -> None:
        """Update an Instagram post record."""
        self.db.collection(self.INSTAGRAM_POSTS_COLLECTION).document(doc_id).update(updates)
    
    def get_posts_by_status(self, status: str) -> List[dict]:
        """Get all Instagram posts with a given status."""
        query = self.db.collection(self.INSTAGRAM_POSTS_COLLECTION).where("status", "==", status)
        return [doc.to_dict() | {"doc_id": doc.id} for doc in query.stream()]
    
    # ========== Utility ==========
    
    def test_connection(self) -> dict:
        """
        Test Firestore connection.
        
        Returns:
            Dict with connection status
        """
        try:
            # Try to list collections (light operation)
            collections = list(self.db.collections())
            return {
                "status": "connected",
                "project": self.PROJECT_ID,
                "database": self.DATABASE_ID,
                "collections": [c.id for c in collections]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_character_count(self) -> int:
        """Get total number of characters."""
        # Use aggregation query if available, otherwise count docs
        docs = self.db.collection(self.CHARACTERS_COLLECTION).stream()
        return sum(1 for _ in docs)


# Convenience singleton
_firestore_service = None

def get_firestore_service() -> FirestoreService:
    """Get or create the Firestore service singleton."""
    global _firestore_service
    if _firestore_service is None:
        _firestore_service = FirestoreService()
    return _firestore_service


if __name__ == "__main__":
    # Quick test
    service = FirestoreService()
    result = service.test_connection()
    print(f"\n🔗 Connection Test: {result}")
