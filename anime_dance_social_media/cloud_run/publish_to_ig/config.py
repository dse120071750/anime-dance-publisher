"""
Configuration module for Anime Dance Social Media Pipeline.
Centralizes environment variables and cloud configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


class Config:
    """Centralized configuration for the anime dance pipeline."""
    
    # ========== Project Paths ==========
    PROJECT_ROOT = PROJECT_ROOT
    OUTPUT_DIR = PROJECT_ROOT / "anime_dance_social_media" / "output"
    CHARACTERS_DIR = OUTPUT_DIR / "characters"
    DANCES_DIR = OUTPUT_DIR / "dances"
    REMIXES_DIR = OUTPUT_DIR / "remixes"
    TEMP_DIR = OUTPUT_DIR / "temp"
    
    # ========== Google Cloud ==========
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "nisan-n8n")
    GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "nisan-n8n")
    GCS_BASE_PREFIX = "anime_dance"
    
    # Service account credentials
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "(default)")
    
    # ========== External APIs ==========
    # Gemini
    GOOGLE_ROTATION_KEYS = os.getenv("GOOGLE_ROTATION_KEYS", "").split(",")
    
    # FAL AI
    FAL_AI_KEY = os.getenv("FAL_AI_KEY")
    FAL_AI_ENDPOINT = os.getenv("FAL_AI_ENDPOINT")
    
    # Minimax
    MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
    
    # Instagram
    INSTAGRAM_USER_TOKEN = os.getenv("INSTAGRAM_USER_TOKEN")
    
    # Supabase (legacy)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    # ========== Feature Flags ==========
    USE_CLOUD_STORAGE = True  # Set to False to use local storage
    USE_FIRESTORE = True      # Set to False to use local JSON
    
    @classmethod
    def get_gcs_path(cls, local_path: str) -> str:
        """Convert a local path to GCS path."""
        path = Path(local_path)
        
        # Find relative path from output directory
        try:
            relative = path.relative_to(cls.OUTPUT_DIR)
            return f"gs://{cls.GCS_BUCKET_NAME}/{cls.GCS_BASE_PREFIX}/{relative.as_posix()}"
        except ValueError:
            # Path is not under OUTPUT_DIR
            return f"gs://{cls.GCS_BUCKET_NAME}/{cls.GCS_BASE_PREFIX}/{path.name}"
    
    @classmethod
    def get_local_path(cls, gcs_uri: str) -> Path:
        """Convert a GCS URI to local path."""
        # gs://nisan-n8n/anime_dance/characters/file.png
        # → C:\...\output\characters\file.png
        if not gcs_uri.startswith("gs://"):
            return Path(gcs_uri)
        
        # Extract path after bucket/prefix
        parts = gcs_uri.replace(f"gs://{cls.GCS_BUCKET_NAME}/{cls.GCS_BASE_PREFIX}/", "")
        return cls.OUTPUT_DIR / parts.replace("/", os.sep)
    
    @classmethod
    def ensure_dirs(cls):
        """Ensure all output directories exist."""
        for dir_path in [cls.OUTPUT_DIR, cls.CHARACTERS_DIR, cls.DANCES_DIR, 
                         cls.REMIXES_DIR, cls.TEMP_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls) -> dict:
        """Validate configuration and return status."""
        status = {
            "gcp_project": cls.GCP_PROJECT_ID,
            "gcs_bucket": cls.GCS_BUCKET_NAME,
            "credentials_set": bool(cls.GOOGLE_APPLICATION_CREDENTIALS),
            "credentials_exists": (
                os.path.exists(cls.GOOGLE_APPLICATION_CREDENTIALS) 
                if cls.GOOGLE_APPLICATION_CREDENTIALS else False
            ),
            "instagram_token_set": bool(cls.INSTAGRAM_USER_TOKEN),
            "gemini_keys_count": len([k for k in cls.GOOGLE_ROTATION_KEYS if k]),
        }
        return status


# Create convenience instance
config = Config()


if __name__ == "__main__":
    print("🔧 Configuration Validation:")
    for key, value in Config.validate().items():
        print(f"   {key}: {value}")
