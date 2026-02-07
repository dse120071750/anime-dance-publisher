"""
Configuration for Cloud Run Full Pipeline Service
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask
    PORT = int(os.getenv('PORT', 8080))
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Security
    API_KEY = os.getenv('PIPELINE_API_KEY')
    
    # Google Cloud
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'nisan-n8n')
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'nisan-n8n')
    
    # Firestore Collections
    FIRESTORE_COLLECTION_JOBS = 'pipeline_jobs'
    FIRESTORE_COLLECTION_CHARACTERS = 'characters'
    
    # Pipeline Defaults
    DEFAULT_STYLE_ID = 'kpop_dance'
    DEFAULT_COUNT = 1
    MAX_COUNT = 10  # Prevent abuse
    
    # Paths (mounted in Cloud Run)
    OUTPUT_DIR = '/tmp/output'  # Use /tmp for Cloud Run (ephemeral)
    TEMP_DIR = '/tmp/temp'
    REFERENCE_DIR = '/tmp/references'
    
    # Timeouts (seconds)
    JOB_TIMEOUT = int(os.getenv('JOB_TIMEOUT', 3600))  # 1 hour
    
    @classmethod
    def ensure_dirs(cls):
        """Ensure output directories exist"""
        for d in [cls.OUTPUT_DIR, cls.TEMP_DIR, cls.REFERENCE_DIR]:
            os.makedirs(d, exist_ok=True)


class PipelineConfig:
    """Configuration for pipeline execution"""
    
    def __init__(self, data: dict):
        self.count = min(data.get('count', Config.DEFAULT_COUNT), Config.MAX_COUNT)
        self.style_id = data.get('style_id', Config.DEFAULT_STYLE_ID)
        self.reference_videos = data.get('reference_videos', [])
        self.webhook_url = data.get('webhook_url')
        self.options = data.get('options', {})
        
        # Option defaults
        self.skip_existing = self.options.get('skip_existing', True)
        self.generate_variants = self.options.get('generate_variants', True)
        self.create_soundtracks = self.options.get('create_soundtracks', True)
        self.apply_watermark = self.options.get('apply_watermark', True)
    
    def to_dict(self):
        return {
            'count': self.count,
            'style_id': self.style_id,
            'reference_videos': self.reference_videos,
            'webhook_url': self.webhook_url,
            'options': {
                'skip_existing': self.skip_existing,
                'generate_variants': self.generate_variants,
                'create_soundtracks': self.create_soundtracks,
                'apply_watermark': self.apply_watermark
            }
        }
