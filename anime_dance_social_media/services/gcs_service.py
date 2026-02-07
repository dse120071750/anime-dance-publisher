"""
Google Cloud Storage Service for Anime Dance Social Media Pipeline.
Handles file uploads, downloads, and URL generation using nisan-n8n service account.
"""
import os
import mimetypes
from datetime import timedelta
from pathlib import Path
from typing import Optional, Union

try:
    from google.cloud import storage
    from google.oauth2 import service_account
except ImportError:
    raise ImportError("Please install google-cloud-storage: pip install google-cloud-storage")

# Load from .env or environment
from dotenv import load_dotenv
load_dotenv()

class GCSService:
    """
    Google Cloud Storage service wrapper for the anime dance pipeline.
    Uses service account nisan-n8n for authentication.
    """
    
    BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "nisan-n8n")
    PROJECT_ID = os.getenv("GCP_PROJECT_ID", "nisan-n8n")
    CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # Default prefix for all anime dance assets
    BASE_PREFIX = "anime_dance"
    
    def __init__(self):
        """Initialize GCS client with service account credentials."""
        if self.CREDENTIALS_PATH and os.path.exists(self.CREDENTIALS_PATH):
            credentials = service_account.Credentials.from_service_account_file(
                self.CREDENTIALS_PATH
            )
            self.client = storage.Client(
                project=self.PROJECT_ID,
                credentials=credentials
            )
        else:
            # Fall back to default credentials (ADC)
            self.client = storage.Client(project=self.PROJECT_ID)
        
        self.bucket = self.client.bucket(self.BUCKET_NAME)
        print(f"   🌐 GCS Service initialized: gs://{self.BUCKET_NAME}/{self.BASE_PREFIX}/")
    
    def _get_gcs_path(self, local_path: str) -> str:
        """
        Convert a local file path to a GCS object path.
        
        Example:
            C:\\...\\output\\characters\\nezuko.png 
            → anime_dance/characters/nezuko.png
        """
        path = Path(local_path)
        
        # Find the relative path from 'output' directory
        parts = path.parts
        if "output" in parts:
            output_idx = parts.index("output")
            relative_parts = parts[output_idx + 1:]  # Skip 'output'
            return f"{self.BASE_PREFIX}/" + "/".join(relative_parts)
        elif "characters" in parts:
            # Handle characters root folder
            char_idx = parts.index("characters")
            relative_parts = parts[char_idx:]
            return f"{self.BASE_PREFIX}/" + "/".join(relative_parts)
        else:
            # Use filename only
            return f"{self.BASE_PREFIX}/{path.name}"
    
    def upload_file(
        self, 
        local_path: str, 
        gcs_path: Optional[str] = None,
        make_public: bool = False
    ) -> str:
        """
        Upload a file to GCS.
        
        Args:
            local_path: Path to the local file
            gcs_path: Optional custom GCS path; auto-generated if not provided
            make_public: Whether to make the file publicly accessible
            
        Returns:
            GCS URI (gs://bucket/path) of the uploaded file
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        if gcs_path is None:
            gcs_path = self._get_gcs_path(local_path)
        
        blob = self.bucket.blob(gcs_path)
        
        # Set content type based on file extension
        content_type, _ = mimetypes.guess_type(local_path)
        if content_type:
            blob.content_type = content_type
        
        print(f"   📤 Uploading to GCS: {gcs_path}")
        blob.upload_from_filename(local_path)
        
        if make_public:
            blob.make_public()
        
        return f"gs://{self.BUCKET_NAME}/{gcs_path}"
    
    def download_file(self, gcs_path: str, local_path: str) -> str:
        """
        Download a file from GCS.
        
        Args:
            gcs_path: GCS object path (with or without gs:// prefix)
            local_path: Local destination path
            
        Returns:
            Local path of the downloaded file
        """
        # Strip gs:// prefix if present
        if gcs_path.startswith("gs://"):
            gcs_path = gcs_path.replace(f"gs://{self.BUCKET_NAME}/", "")
        
        blob = self.bucket.blob(gcs_path)
        
        # Ensure local directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        print(f"   📥 Downloading from GCS: {gcs_path}")
        blob.download_to_filename(local_path)
        
        return local_path
    
    def get_public_url(self, gcs_path: str) -> str:
        """
        Get the public URL for a GCS object.
        Note: Object must be public or have appropriate permissions.
        
        Args:
            gcs_path: GCS object path or URI
            
        Returns:
            Public HTTPS URL
        """
        if gcs_path.startswith("gs://"):
            gcs_path = gcs_path.replace(f"gs://{self.BUCKET_NAME}/", "")
        
        return f"https://storage.googleapis.com/{self.BUCKET_NAME}/{gcs_path}"
    
    def get_signed_url(
        self, 
        gcs_path: str, 
        expiration_hours: int = 24
    ) -> str:
        """
        Generate a signed URL for temporary access.
        Useful for Instagram API which requires public URLs.
        
        Args:
            gcs_path: GCS object path or URI
            expiration_hours: Hours until the URL expires
            
        Returns:
            Signed URL with temporary access
        """
        if gcs_path.startswith("gs://"):
            gcs_path = gcs_path.replace(f"gs://{self.BUCKET_NAME}/", "")
        
        blob = self.bucket.blob(gcs_path)
        
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET"
        )
        
        return url
    
    def delete_file(self, gcs_path: str) -> bool:
        """
        Delete a file from GCS.
        
        Args:
            gcs_path: GCS object path or URI
            
        Returns:
            True if deleted, False if not found
        """
        if gcs_path.startswith("gs://"):
            gcs_path = gcs_path.replace(f"gs://{self.BUCKET_NAME}/", "")
        
        blob = self.bucket.blob(gcs_path)
        
        if blob.exists():
            blob.delete()
            print(f"   🗑️ Deleted from GCS: {gcs_path}")
            return True
        return False
    
    def file_exists(self, gcs_path: str) -> bool:
        """Check if a file exists in GCS."""
        if gcs_path.startswith("gs://"):
            gcs_path = gcs_path.replace(f"gs://{self.BUCKET_NAME}/", "")
        
        blob = self.bucket.blob(gcs_path)
        return blob.exists()
    
    def list_files(self, prefix: str = None) -> list:
        """
        List all files under a given prefix.
        
        Args:
            prefix: GCS path prefix (defaults to anime_dance/)
            
        Returns:
            List of GCS object paths
        """
        if prefix is None:
            prefix = self.BASE_PREFIX
        
        blobs = self.client.list_blobs(self.bucket, prefix=prefix)
        return [blob.name for blob in blobs]
    
    def test_connection(self) -> dict:
        """
        Test GCS connection and bucket access.
        
        Returns:
            Dict with connection status and bucket info
        """
        try:
            # Try to get bucket metadata
            bucket = self.client.get_bucket(self.BUCKET_NAME)
            return {
                "status": "connected",
                "bucket": self.BUCKET_NAME,
                "project": self.PROJECT_ID,
                "location": bucket.location,
                "storage_class": bucket.storage_class
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Convenience singleton
_gcs_service = None

def get_gcs_service() -> GCSService:
    """Get or create the GCS service singleton."""
    global _gcs_service
    if _gcs_service is None:
        _gcs_service = GCSService()
    return _gcs_service


if __name__ == "__main__":
    # Quick test
    service = GCSService()
    result = service.test_connection()
    print(f"\n🔗 Connection Test: {result}")
