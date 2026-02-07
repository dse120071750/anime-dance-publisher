"""
Cloud Run Full Pipeline Service - Main Entry Point
"""
import os
import sys
from pathlib import Path

# Add project root to Python path (for importing workflows)
ROOT = Path(__file__).parent.parent.parent  # up to anime_dance_social_media
sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify
from config import Config
from routes.api import api_bp

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Ensure output directories exist
    Config.ensure_dirs()
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found',
            'available_endpoints': [
                'GET  /api/v1/health',
                'POST /api/v1/pipeline/run',
                'GET  /api/v1/pipeline/status/<job_id>',
                'GET  /api/v1/pipeline/jobs',
                'POST /api/v1/pipeline/cancel/<job_id>',
                'GET  /api/v1/pipeline/characters'
            ]
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'service': 'AURA Full Pipeline Service',
            'version': '1.0.0',
            'status': 'running',
            'docs': '/api/v1/health',
            'endpoints': {
                'health': 'GET /api/v1/health',
                'run_pipeline': 'POST /api/v1/pipeline/run',
                'job_status': 'GET /api/v1/pipeline/status/<job_id>',
                'list_jobs': 'GET /api/v1/pipeline/jobs',
                'cancel_job': 'POST /api/v1/pipeline/cancel/<job_id>',
                'list_characters': 'GET /api/v1/pipeline/characters'
            }
        })
    
    return app


app = create_app()

if __name__ == '__main__':
    port = Config.PORT
    debug = Config.DEBUG
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  AURA Full Pipeline Service                                  ║
║  Version: 1.0.0                                              ║
║  Port: {port}                                                    ║
║  Debug: {debug}                                                 ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Run with gunicorn in production, flask dev server locally
    if os.getenv('FLASK_ENV') == 'production':
        # Gunicorn will handle this
        pass
    else:
        app.run(host='0.0.0.0', port=port, debug=debug)
