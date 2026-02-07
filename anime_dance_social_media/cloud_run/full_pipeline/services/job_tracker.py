"""
Job Tracker - Manages pipeline job state in Firestore
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent.parent.parent  # up to anime_dance_social_media
sys.path.insert(0, str(ROOT))

from google.cloud import firestore
from services.firestore_service import FirestoreService
from config import Config


class JobTracker:
    """Tracks pipeline job progress in Firestore"""
    
    def __init__(self, job_id: Optional[str] = None):
        self.job_id = job_id or str(uuid.uuid4())
        self.fs = FirestoreService()
        self.collection = self.fs.db.collection(Config.FIRESTORE_COLLECTION_JOBS)
    
    def create_job(self, config: Dict[str, Any]) -> str:
        """Create a new job document in Firestore"""
        job_data = {
            'job_id': self.job_id,
            'status': 'queued',
            'config': config,
            'progress': {
                'total_characters': config.get('count', 1),
                'completed': 0,
                'current_character': None,
                'current_stage': 'initializing',
                'percent_complete': 0
            },
            'results': [],
            'errors': [],
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'started_at': None,
            'completed_at': None
        }
        
        self.collection.document(self.job_id).set(job_data)
        print(f"[JobTracker] Created job: {self.job_id}")
        return self.job_id
    
    def update_status(self, status: str, message: Optional[str] = None):
        """Update job status"""
        updates = {
            'status': status,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        if message:
            updates['message'] = message
        if status == 'running' and not self._get_field('started_at'):
            updates['started_at'] = firestore.SERVER_TIMESTAMP
        if status in ['completed', 'failed']:
            updates['completed_at'] = firestore.SERVER_TIMESTAMP
        
        self.collection.document(self.job_id).update(updates)
        print(f"[JobTracker] Job {self.job_id} status: {status}")
    
    def update_progress(
        self,
        current_character: Optional[str] = None,
        current_stage: Optional[str] = None,
        completed: Optional[int] = None,
        percent_complete: Optional[int] = None
    ):
        """Update job progress"""
        progress = self._get_field('progress') or {}
        
        if current_character:
            progress['current_character'] = current_character
        if current_stage:
            progress['current_stage'] = current_stage
        if completed is not None:
            progress['completed'] = completed
        if percent_complete is not None:
            progress['percent_complete'] = percent_complete
        
        self.collection.document(self.job_id).update({
            'progress': progress,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
    
    def add_character_result(self, character_data: Dict[str, Any]):
        """Add a completed character result"""
        self.collection.document(self.job_id).update({
            'results': firestore.ArrayUnion([character_data]),
            'updated_at': firestore.SERVER_TIMESTAMP
        })
    
    def add_error(self, error: str):
        """Add an error message"""
        self.collection.document(self.job_id).update({
            'errors': firestore.ArrayUnion([{
                'message': error,
                'timestamp': datetime.utcnow().isoformat()
            }]),
            'updated_at': firestore.SERVER_TIMESTAMP
        })
    
    def get_job(self) -> Optional[Dict[str, Any]]:
        """Get job document"""
        doc = self.collection.document(self.job_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    
    def _get_field(self, field: str) -> Any:
        """Get a specific field from job document"""
        doc = self.collection.document(self.job_id).get()
        if doc.exists:
            return doc.to_dict().get(field)
        return None
    
    @staticmethod
    def list_jobs(
        status: Optional[str] = None,
        limit: int = 10,
        order_by: str = 'created_at'
    ) -> List[Dict[str, Any]]:
        """List jobs with optional filtering"""
        fs = FirestoreService()
        query = fs.db.collection(Config.FIRESTORE_COLLECTION_JOBS)
        
        if status:
            query = query.where('status', '==', status)
        
        query = query.order_by(order_by, direction=firestore.Query.DESCENDING)
        query = query.limit(limit)
        
        return [doc.to_dict() for doc in query.stream()]
    
    def cancel(self) -> bool:
        """Mark job as cancelled"""
        try:
            self.update_status('cancelled', 'Job cancelled by user')
            return True
        except Exception as e:
            print(f"[JobTracker] Failed to cancel job: {e}")
            return False
