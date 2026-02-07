import os
import sys
import argparse
import random
import glob

# Add root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from workflows.character_gen import generate_characters
from workflows.main_pipeline import run_end_to_end_pipeline
from utils.db_utils import get_entry

def run_batch_new_chars(count=20, style_id="kpop_dance", limit_refs=1):
    """
    Sequential Workflow:
    1. Resumes: Finds characters in DB who have a cosplay image but no dance video and processes them.
    2. Generates New: Brainstorms characters one-by-one and immediately triggers the full pipeline.
    """
    print(f"\n🚀 STARTING STREAMLINED WORKFLOW")
    print(f"🎵 Music Style ID: {style_id}")
    
    from utils.db_utils import load_db, get_entry
    from workflows.character_gen import generate_new_targets_list, generate_characters
    import random
    
    db = load_db()
    
    # --- 1. RESUME PENDING DANCES ---
    print("\n🔍 Scanning for pending dances in database...")
    pending_chars = []
    for entry in db:
        char_id = entry.get("id")
        primary_asset = next((a for a in entry.get("assets", []) if a.get("title") == "primary"), None)
        if primary_asset:
            cosplay_img = primary_asset.get("cosplay_image")
            dance_vid = primary_asset.get("dance_video")
            
            if cosplay_img and os.path.exists(cosplay_img) and not dance_vid:
                pending_chars.append((char_id, cosplay_img))
    
    if pending_chars:
        print(f"   📋 Found {len(pending_chars)} characters awaiting dance generation.")
        REF_DIR = os.path.join(ROOT, "temp_process_kling")
        ref_videos = glob.glob(os.path.join(REF_DIR, "*.mp4"))
        
        for char_id, char_img in pending_chars:
            if not ref_videos: break
            ref_video = random.choice(ref_videos)
            print(f"\n🎬 [RESUME] Processing: {char_id} on {os.path.basename(ref_video)}")
            try:
                run_end_to_end_pipeline(char_img=char_img, ref_video=ref_video, char_id=char_id, reuse_cosplay=True, style_id=style_id)
            except Exception as e:
                print(f"   ❌ Error resuming {char_id}: {e}")

    # --- 2. GENERATE NEW CHARACTERS SEQUENTIALLY ---
    if count > 0:
        print(f"\n🧠 Brainstorming {count} NEW characters (18yo Asian cute style)...")
        service = GeminiService()
        existing_names = {entry.get('name') for entry in db}
        
        # We can get the list first to avoid repeated service calls, or one by one. 
        # User wants: Gen 1 -> Dance 1 -> Gen 2 -> Dance 2.
        
        # Brainstorm a list of targets first to stay organized
        targets = generate_new_targets_list(service, existing_names, count)
        
        if not targets:
            print("❌ No new characters brainstormed. Finishing.")
            return

        REF_DIR = os.path.join(ROOT, "temp_process_kling")
        ref_videos = glob.glob(os.path.join(REF_DIR, "*.mp4"))

        for name, anime in targets:
            print(f"\n✨ Starting Full Sequence for: {name} ({anime})")
            
            # Phase A: Character + Cosplay Generation
            # We pass a list with 1 item to generate_characters
            char_ids = generate_characters(target_list=[(name, anime)])
            
            if not char_ids:
                print(f"   ⚠️ Generation failed for {name}. skipping to next.")
                continue
                
            char_id = char_ids[0]
            entry = get_entry(char_id)
            primary_asset = next((a for a in entry.get("assets", []) if a.get("title") == "primary"), None)
            char_img = primary_asset.get("anime_image") if primary_asset else None
            
            # Phase B: Pipeline Execution
            if char_img and os.path.exists(char_img) and ref_videos:
                ref_video = random.choice(ref_videos)
                print(f"   🎬 [MAIN PIPELINE] Triggering: {char_id} on {os.path.basename(ref_video)}")
                try:
                    run_end_to_end_pipeline(
                        char_img=char_img,
                        ref_video=ref_video,
                        char_id=char_id,
                        reuse_cosplay=True,
                        style_id=style_id
                    )
                except Exception as e:
                    print(f"   ❌ Pipeline Error for {char_id}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch New Characters Workflow")
    parser.add_argument("--count", type=int, default=20, help="Number of new characters to generate")
    parser.add_argument("--style_id", default="kpop_dance", help="Music style ID from music_styles_db.json")
    
    args = parser.parse_args()
    
    from services.gemini_service import GeminiService
    run_batch_new_chars(
        count=args.count,
        style_id=args.style_id
    )
