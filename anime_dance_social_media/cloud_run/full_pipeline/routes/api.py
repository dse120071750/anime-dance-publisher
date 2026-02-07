"""
API Routes for Full Pipeline Service
"""
import os
from functools import wraps
from flask import Blueprint, request, jsonify

from config import Config, PipelineConfig
from services.job_tracker import JobTracker
from executor.pipeline_executor import PipelineExecutor

api_bp = Blueprint('api', __name__)


def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        api_key = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None
        
        if not api_key or api_key != Config.API_KEY:
            return jsonify({
                'success': False,
                'error': 'Unauthorized. Valid API key required.'
            }), 401
        
        return f(*args, **kwargs)
    return decorated


def validate_json(f):
    """Decorator to validate JSON body"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ['POST', 'PUT'] and not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400
        return f(*args, **kwargs)
    return decorated


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'full-pipeline',
        'version': '1.0.0'
    })


@api_bp.route('/pipeline/run', methods=['POST'])
@require_api_key
@validate_json
def run_pipeline():
    """
    Start a new pipeline job
    
    Request Body:
    {
        "count": 5,                      # Required: Number of characters
        "style_id": "kpop_dance",        # Optional: Music style
        "reference_videos": [],          # Optional: Specific ref videos
        "webhook_url": "https://...",    # Optional: Callback URL
        "options": {                     # Optional: Pipeline options
            "skip_existing": true,
            "generate_variants": true,
            "create_soundtracks": true,
            "apply_watermark": true
        }
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'count' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: count'
            }), 400
        
        # Validate count
        count = data.get('count', 1)
        if not isinstance(count, int) or count < 1 or count > Config.MAX_COUNT:
            return jsonify({
                'success': False,
                'error': f'Invalid count. Must be between 1 and {Config.MAX_COUNT}'
            }), 400
        
        # Create pipeline config
        config = PipelineConfig(data)
        
        # Create job tracker
        tracker = JobTracker()
        job_id = tracker.create_job(config.to_dict())
        
        # Start pipeline execution in background
        import threading
        def run_async():
            try:
                executor = PipelineExecutor(job_id, config)
                result = executor.execute()
                
                # Call webhook if provided
                if config.webhook_url:
                    _call_webhook(config.webhook_url, {
                        'job_id': job_id,
                        'status': 'completed',
                        'result': result
                    })
                    
            except Exception as e:
                print(f"[Pipeline] Job {job_id} failed: {e}")
                tracker.update_status('failed', str(e))
                tracker.add_error(str(e))
                
                if config.webhook_url:
                    _call_webhook(config.webhook_url, {
                        'job_id': job_id,
                        'status': 'failed',
                        'error': str(e)
                    })
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'queued',
            'message': 'Pipeline job started successfully',
            'estimated_duration': f'{15 * count}-{20 * count} minutes'
        }), 202
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to start pipeline: {str(e)}'
        }), 500


@api_bp.route('/pipeline/status/<job_id>', methods=['GET'])
@require_api_key
def get_status(job_id):
    """Get pipeline job status"""
    try:
        tracker = JobTracker(job_id)
        job = tracker.get_job()
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        return jsonify({
            'success': True,
            'job': job
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/pipeline/jobs', methods=['GET'])
@require_api_key
def list_jobs():
    """List pipeline jobs"""
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 10))
        
        jobs = JobTracker.list_jobs(status=status, limit=limit)
        
        return jsonify({
            'success': True,
            'jobs': jobs,
            'count': len(jobs)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/pipeline/cancel/<job_id>', methods=['POST'])
@require_api_key
def cancel_job(job_id):
    """Cancel a running pipeline job"""
    try:
        tracker = JobTracker(job_id)
        job = tracker.get_job()
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        if job.get('status') in ['completed', 'failed', 'cancelled']:
            return jsonify({
                'success': False,
                'error': f'Job already {job["status"]}'
            }), 400
        
        success = tracker.cancel()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Job cancelled successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to cancel job'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/pipeline/characters', methods=['GET'])
@require_api_key
def list_characters():
    """List all characters in Firestore"""
    try:
        from services.firestore_service import FirestoreService
        
        fs = FirestoreService()
        chars = fs.get_all_characters()
        
        # Simplify response
        simplified = []
        for char in chars:
            simplified.append({
                'id': char.get('id'),
                'name': char.get('name'),
                'anime': char.get('anime'),
                'asset_count': len(char.get('assets', [])),
                'updated_at': char.get('updated_at')
            })
        
        return jsonify({
            'success': True,
            'characters': simplified,
            'count': len(simplified)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _call_webhook(url: str, payload: dict):
    """Call webhook URL with payload"""
    try:
        import requests
        requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
    except Exception as e:
        print(f"[Webhook] Failed to call {url}: {e}")
