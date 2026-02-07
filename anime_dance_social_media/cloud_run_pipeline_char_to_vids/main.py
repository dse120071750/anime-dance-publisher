"""
Lightweight Cloud Run Pipeline Service - Character to Videos
Optimized for scale-to-0 and minimal resource usage
"""
import os
import sys
import json
import uuid
import logging
from datetime import datetime
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask imports only
from flask import Flask, request, jsonify, g

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

# Configuration from environment
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'nisan-n8n')
BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'nisan-n8n')
API_KEY = os.getenv('PIPELINE_API_KEY', 'dev-key')

# Firestore collections
JOBS_COLLECTION = 'pipeline_jobs'
CHARACTERS_COLLECTION = 'characters'


def get_firestore():
    """Lazy load Firestore client"""
    if not hasattr(g, 'firestore'):
        from google.cloud import firestore
        g.firestore = firestore.Client(project=PROJECT_ID)
    return g.firestore


def get_gcs():
    """Lazy load GCS client"""
    if not hasattr(g, 'gcs'):
        from google.cloud import storage
        g.gcs = storage.Client(project=PROJECT_ID)
    return g.gcs


def require_api_key(f):
    """API key authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        key = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None
        if key != API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ============== HEALTH & INFO ==============

@app.route('/')
def index():
    """Service info"""
    return jsonify({
        'service': 'AURA Pipeline - Char to Videos',
        'version': '1.0.0-lite',
        'mode': 'cloud-run-scale-to-0',
        'endpoints': [
            'GET  /health',
            'POST /pipeline/run',
            'GET  /pipeline/status/<job_id>',
            'GET  /pipeline/jobs',
            'POST /pipeline/cancel/<job_id>'
        ]
    })


@app.route('/health')
def health():
    """Health check - lightweight"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# ============== PIPELINE API ==============

@app.route('/pipeline/run', methods=['POST'])
@require_api_key
def run_pipeline():
    """
    Start a new pipeline job
    
    Body: {
        "count": 1,
        "style_id": "kpop_dance",
        "webhook_url": "optional"
    }
    """
    try:
        data = request.get_json() or {}
        
        # Validate
        count = data.get('count', 1)
        if not isinstance(count, int) or count < 1 or count > 10:
            return jsonify({'error': 'Invalid count (1-10)'}), 400
        
        # Create job record
        job_id = str(uuid.uuid4())
        db = get_firestore()
        
        job_doc = {
            'job_id': job_id,
            'status': 'queued',
            'config': {
                'count': count,
                'style_id': data.get('style_id', 'kpop_dance'),
                'webhook_url': data.get('webhook_url'),
                'options': data.get('options', {})
            },
            'progress': {
                'total': count,
                'completed': 0,
                'current': None
            },
            'results': [],
            'errors': [],
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        db.collection(JOBS_COLLECTION).document(job_id).set(job_doc)
        
        # Trigger processing (in background thread for Cloud Run)
        import threading
        thread = threading.Thread(target=_process_job, args=(job_id, job_doc['config']))
        thread.daemon = True
        thread.start()
        
        logger.info(f"Job {job_id} started")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'queued',
            'message': f'Pipeline started for {count} character(s)',
            'estimated_time': f'{count * 20} minutes'
        }), 202
        
    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/pipeline/status/<job_id>')
@require_api_key
def get_status(job_id):
    """Get job status from Firestore"""
    try:
        db = get_firestore()
        doc = db.collection(JOBS_COLLECTION).document(job_id).get()
        
        if not doc.exists:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify(doc.to_dict())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/pipeline/jobs')
@require_api_key
def list_jobs():
    """List recent jobs"""
    try:
        db = get_firestore()
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 10))
        
        query = db.collection(JOBS_COLLECTION).order_by('created_at', direction='DESCENDING').limit(limit)
        
        if status_filter:
            query = query.where('status', '==', status_filter)
        
        jobs = [doc.to_dict() for doc in query.stream()]
        
        return jsonify({
            'jobs': jobs,
            'count': len(jobs)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/pipeline/cancel/<job_id>', methods=['POST'])
@require_api_key
def cancel_job(job_id):
    """Cancel a running job"""
    try:
        db = get_firestore()
        doc_ref = db.collection(JOBS_COLLECTION).document(job_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({'error': 'Job not found'}), 404
        
        doc_ref.update({
            'status': 'cancelled',
            'updated_at': datetime.utcnow().isoformat()
        })
        
        return jsonify({'success': True, 'message': 'Job cancelled'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============== BACKGROUND PROCESSING ==============

def _process_job(job_id: str, config: dict):
    """
    Process pipeline job in background
    Heavy imports done here to keep startup fast
    """
    logger.info(f"Processing job {job_id}")
    
    # Heavy imports only when processing
    try:
        from workflows.character_gen import generate_characters
        from workflows.main_pipeline import run_end_to_end_pipeline
        from utils.db_utils import get_entry
        import random
        import glob
        
        db = get_firestore()
        
        def update_status(status: str, progress: dict = None):
            updates = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            if progress:
                updates['progress'] = progress
            db.collection(JOBS_COLLECTION).document(job_id).update(updates)
        
        def add_result(result: dict):
            db.collection(JOBS_COLLECTION).document(job_id).update({
                'results': firestore.ArrayUnion([result]),
                'updated_at': datetime.utcnow().isoformat()
            })
        
        def add_error(error: str):
            db.collection(JOBS_COLLECTION).document(job_id).update({
                'errors': firestore.ArrayUnion([{
                    'message': error,
                    'time': datetime.utcnow().isoformat()
                }]),
                'updated_at': datetime.utcnow().isoformat()
            })
        
        # Update to running
        update_status('running', {'total': config['count'], 'completed': 0})
        
        count = config['count']
        style_id = config['style_id']
        
        # Load reference videos from GCS or local temp
        ref_videos = _get_reference_videos()
        
        if not ref_videos:
            raise ValueError("No reference videos available")
        
        # Generate characters
        logger.info(f"Generating {count} characters...")
        
        # Use workflow to brainstorm and generate
        from services.gemini_service import GeminiService
        
        service = GeminiService()
        from workflows.character_gen import generate_new_targets_list, generate_characters
        
        # Get existing names
        from utils.db_utils import load_db
        existing_names = {e.get('name') for e in load_db()}
        
        # Brainstorm targets
        targets = generate_new_targets_list(service, existing_names, count)
        
        for i, (name, anime) in enumerate(targets):
            # Check if cancelled
            doc = db.collection(JOBS_COLLECTION).document(job_id).get()
            if doc.to_dict().get('status') == 'cancelled':
                logger.info(f"Job {job_id} cancelled")
                return
            
            logger.info(f"Processing character {i+1}/{len(targets)}: {name}")
            update_status('running', {
                'total': count,
                'completed': i,
                'current': name,
                'stage': 'character_generation'
            })
            
            # Generate character
            char_ids = generate_characters(target_list=[(name, anime)])
            
            if not char_ids:
                add_error(f"Failed to generate character: {name}")
                continue
            
            char_id = char_ids[0]
            entry = get_entry(char_id)
            
            if not entry:
                add_error(f"Entry not found: {char_id}")
                continue
            
            # Get character image
            primary = next((a for a in entry.get('assets', []) if a.get('title') == 'primary'), None)
            char_img = primary.get('anime_image') if primary else None
            
            if not char_img or not os.path.exists(char_img):
                add_error(f"Character image not found: {char_id}")
                continue
            
            # Generate 3 dance versions with different refs
            dances = []
            for j in range(min(3, len(ref_videos))):
                ref = random.choice(ref_videos)
                
                update_status('running', {
                    'total': count,
                    'completed': i,
                    'current': name,
                    'stage': f'dance_generation_v{j+1}'
                })
                
                try:
                    deliverable = run_end_to_end_pipeline(
                        char_img=char_img,
                        ref_video=ref,
                        char_id=char_id,
                        reuse_cosplay=True,
                        style_id=style_id
                    )
                    
                    if deliverable:
                        dances.append({
                            'version': j+1,
                            'ref': os.path.basename(ref),
                            'deliverable': deliverable
                        })
                        
                except Exception as e:
                    logger.error(f"Dance generation failed: {e}")
                    add_error(f"Dance v{j+1} failed for {name}: {e}")
            
            # Add result
            add_result({
                'character_id': char_id,
                'name': name,
                'anime': anime,
                'dances_generated': len(dances),
                'status': 'completed' if dances else 'partial'
            })
        
        # Mark complete
        update_status('completed', {'total': count, 'completed': count})
        
        # Call webhook if provided
        if config.get('webhook_url'):
            _call_webhook(config['webhook_url'], {
                'job_id': job_id,
                'status': 'completed',
                'results': count
            })
        
        logger.info(f"Job {job_id} completed")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        try:
            db = get_firestore()
            db.collection(JOBS_COLLECTION).document(job_id).update({
                'status': 'failed',
                'errors': firestore.ArrayUnion([{'message': str(e)}]),
                'updated_at': datetime.utcnow().isoformat()
            })
        except:
            pass


def _get_reference_videos():
    """Get reference videos from temp directory or GCS"""
    # Local temp directory
    temp_dir = '/tmp/references'
    if os.path.exists(temp_dir):
        vids = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith('.mp4')]
        if vids:
            return vids
    
    # Fallback to project temp
    import glob
    fallback = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp_process_kling')
    if os.path.exists(fallback):
        return glob.glob(os.path.join(fallback, '*.mp4'))
    
    return []


def _call_webhook(url: str, payload: dict):
    """Call webhook URL"""
    try:
        import requests
        requests.post(url, json=payload, timeout=30)
    except Exception as e:
        logger.error(f"Webhook failed: {e}")


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    
    # Use gunicorn in production
    if os.getenv('FLASK_ENV') == 'production':
        # Gunicorn handles this
        pass
    else:
        # Development
        app.run(host='0.0.0.0', port=port, debug=False)
