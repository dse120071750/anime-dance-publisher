"""
Pipeline Executor - Wraps batch workflow for Cloud Run execution
"""
import os
import sys
import time
import random
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

# Add project root to path
ROOT = Path(__file__).parent.parent.parent.parent  # up to anime_dance_social_media
sys.path.insert(0, str(ROOT))

from config import Config, PipelineConfig
from services.job_tracker import JobTracker

# Import workflows
from workflows.character_gen import generate_characters, generate_new_targets_list
from workflows.main_pipeline import run_end_to_end_pipeline
from services.gemini_service import GeminiService
from utils.db_utils import load_db, get_entry


class PipelineExecutor:
    """
    Executes the full pipeline: Character Gen → 3 Dances → Remixes → Cloud Upload
    """
    
    def __init__(self, job_id: str, config: PipelineConfig):
        self.job_id = job_id
        self.config = config
        self.tracker = JobTracker(job_id)
        
        # Setup directories
        Config.ensure_dirs()
        self.output_dir = Config.OUTPUT_DIR
        self.temp_dir = Config.TEMP_DIR
        self.ref_dir = Config.REFERENCE_DIR
        
        # Load reference videos
        self.reference_videos = self._load_references()
        
        # Results tracking
        self.results = []
    
    def _load_references(self) -> List[str]:
        """Load reference videos from mounted directory"""
        if self.config.reference_videos:
            return self.config.reference_videos
        
        # Look in reference directory
        ref_files = []
        if os.path.exists(self.ref_dir):
            ref_files = [
                os.path.join(self.ref_dir, f)
                for f in os.listdir(self.ref_dir)
                if f.endswith('.mp4')
            ]
        
        # Fallback to temp_process_kling if mounted
        if not ref_files:
            fallback_dir = os.path.join(ROOT, 'temp_process_kling')
            if os.path.exists(fallback_dir):
                ref_files = [
                    os.path.join(fallback_dir, f)
                    for f in os.listdir(fallback_dir)
                    if f.endswith('.mp4')
                ]
        
        return ref_files
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute the full pipeline
        
        Returns:
            Dict with execution results
        """
        print(f"\n{'='*60}")
        print(f"🚀 PIPELINE EXECUTOR STARTED")
        print(f"   Job ID: {self.job_id}")
        print(f"   Config: {self.config.to_dict()}")
        print(f"{'='*60}\n")
        
        if not self.reference_videos:
            raise ValueError("No reference videos found. Please mount reference videos.")
        
        print(f"📂 Found {len(self.reference_videos)} reference videos")
        
        try:
            self.tracker.update_status('running', 'Starting pipeline execution')
            
            # Phase 1: Resume any pending characters (from previous runs)
            self._resume_pending_characters()
            
            # Phase 2: Generate new characters
            if self.config.count > 0:
                self._generate_new_characters()
            
            # Mark complete
            self.tracker.update_status('completed', 'Pipeline completed successfully')
            
            return {
                'success': True,
                'job_id': self.job_id,
                'total_characters': len(self.results),
                'results': self.results
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ PIPELINE FAILED: {error_msg}")
            self.tracker.update_status('failed', error_msg)
            self.tracker.add_error(error_msg)
            raise
    
    def _resume_pending_characters(self):
        """Resume characters that have cosplay but no dance"""
        print("\n🔍 Checking for pending characters...")
        
        db = load_db()
        pending = []
        
        for entry in db:
            char_id = entry.get('id')
            assets = entry.get('assets', [])
            primary = next((a for a in assets if a.get('title') == 'primary'), None)
            
            if primary:
                cosplay = primary.get('cosplay_image')
                dance = primary.get('dance_video')
                
                # Check if local files exist
                if cosplay and os.path.exists(cosplay) and not dance:
                    pending.append((char_id, cosplay, entry.get('name', char_id)))
        
        if not pending:
            print("   No pending characters found")
            return
        
        print(f"   Found {len(pending)} pending characters")
        
        for char_id, cosplay_img, name in pending:
            if self._is_cancelled():
                return
            
            print(f"\n🎬 [RESUME] Processing: {name}")
            self.tracker.update_progress(
                current_character=name,
                current_stage='dance_generation (resumed)'
            )
            
            # Generate 3 dance versions with different refs
            self._generate_dance_versions(char_id, cosplay_img, is_resume=True)
    
    def _generate_new_characters(self):
        """Generate new characters with full pipeline"""
        print(f"\n🧠 Generating {self.config.count} new characters...")
        
        # Get existing names
        db = load_db()
        existing_names = {e.get('name') for e in db}
        
        # Brainstorm new targets
        service = GeminiService()
        targets = generate_new_targets_list(service, existing_names, self.config.count)
        
        if not targets:
            print("⚠️ No new characters brainstormed")
            return
        
        print(f"   Brainstormed {len(targets)} characters: {[t[0] for t in targets]}")
        
        for i, (name, anime) in enumerate(targets):
            if self._is_cancelled():
                return
            
            print(f"\n{'='*60}")
            print(f"✨ CHARACTER {i+1}/{len(targets)}: {name} ({anime})")
            print(f"{'='*60}")
            
            self.tracker.update_progress(
                current_character=name,
                current_stage='character_generation',
                completed=i,
                percent_complete=int((i / self.config.count) * 100)
            )
            
            # Phase A: Generate character + cosplay
            char_ids = generate_characters(target_list=[(name, anime)])
            
            if not char_ids:
                print(f"   ⚠️ Character generation failed for {name}")
                self.tracker.add_error(f"Character generation failed: {name}")
                continue
            
            char_id = char_ids[0]
            entry = get_entry(char_id)
            
            if not entry:
                print(f"   ⚠️ Failed to get entry for {char_id}")
                continue
            
            # Get character image
            primary_asset = next(
                (a for a in entry.get('assets', []) if a.get('title') == 'primary'),
                None
            )
            char_img = primary_asset.get('anime_image') if primary_asset else None
            
            if not char_img or not os.path.exists(char_img):
                print(f"   ⚠️ Character image not found for {char_id}")
                continue
            
            # Phase B: Generate 3 dance versions
            print(f"\n🎬 Generating 3 dance versions for {name}...")
            self._generate_dance_versions(char_id, char_img, is_resume=False)
            
            # Track result
            result = {
                'character_id': char_id,
                'name': name,
                'anime': anime,
                'status': 'completed'
            }
            self.results.append(result)
            self.tracker.add_character_result(result)
            self.tracker.update_progress(completed=i+1)
    
    def _generate_dance_versions(self, char_id: str, char_img: str, is_resume: bool = False):
        """
        Generate 3 dance versions with different reference videos
        """
        # Pick 3 random references (or as many as available)
        num_versions = min(3, len(self.reference_videos))
        refs = random.sample(self.reference_videos, num_versions)
        
        dances_generated = []
        
        for i, ref_video in enumerate(refs):
            if self._is_cancelled():
                return
            
            ref_name = os.path.basename(ref_video)
            stage = f'dance_generation_v{i+1}'
            
            print(f"\n   🎵 Dance Version {i+1}/{num_versions}: Using {ref_name}")
            self.tracker.update_progress(current_stage=stage)
            
            try:
                # Run full pipeline (dance + remix + watermark + soundtracks)
                deliverable = run_end_to_end_pipeline(
                    char_img=char_img,
                    ref_video=ref_video,
                    char_id=char_id,
                    reuse_cosplay=True,
                    style_id=self.config.style_id
                )
                
                if deliverable and os.path.exists(deliverable):
                    print(f"   ✅ Deliverable: {os.path.basename(deliverable)}")
                    dances_generated.append({
                        'version': i+1,
                        'reference': ref_name,
                        'deliverable': deliverable
                    })
                else:
                    print(f"   ⚠️ No deliverable for version {i+1}")
                    
            except Exception as e:
                print(f"   ❌ Error in dance version {i+1}: {e}")
                self.tracker.add_error(f"Dance v{i+1} failed for {char_id}: {e}")
        
        print(f"\n   📊 Generated {len(dances_generated)}/{num_versions} dance versions")
        
        # If this was a new character, run soundtrack remix batch
        if not is_resume and dances_generated and self.config.create_soundtracks:
            self._create_soundtrack_versions(char_id, dances_generated[0]['deliverable'])
    
    def _create_soundtrack_versions(self, char_id: str, deliverable_path: str):
        """Create dual soundtrack versions (kpop/orig)"""
        print(f"\n🎶 Creating soundtrack versions...")
        self.tracker.update_progress(current_stage='soundtrack_generation')
        
        try:
            from workflows.batch_soundtrack_remix import process_remix_folder
            
            # Find remix folder from deliverable path
            remix_dir = os.path.dirname(deliverable_path)
            if os.path.basename(remix_dir) == 'result':
                remix_dir = os.path.dirname(remix_dir)
            
            if os.path.exists(remix_dir):
                process_remix_folder(remix_dir, style_id=self.config.style_id)
            else:
                print(f"   ⚠️ Remix folder not found: {remix_dir}")
                
        except Exception as e:
            print(f"   ⚠️ Soundtrack generation failed: {e}")
            self.tracker.add_error(f"Soundtrack failed for {char_id}: {e}")
    
    def _is_cancelled(self) -> bool:
        """Check if job has been cancelled"""
        job = self.tracker.get_job()
        return job and job.get('status') == 'cancelled'
    
    def cleanup(self):
        """Clean up temporary files"""
        print("\n🧹 Cleaning up temporary files...")
        try:
            # Keep output but clean temp
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                os.makedirs(self.temp_dir, exist_ok=True)
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️ Cleanup error: {e}")
