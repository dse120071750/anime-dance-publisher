import os
import sys
import json
import shutil
import re
import time

# Add root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from core.animation import submit_kling_job, process_active_jobs, swap_first_frame
from workflows.main_pipeline import run_remix_pipeline
from utils.db_utils import load_db, upsert_asset, get_entry

# Dirs
CHAR_DIR = os.path.join(ROOT, "output", "characters")
DANCE_DIR = os.path.join(ROOT, "output", "dances")
REMIX_DIR = os.path.join(ROOT, "output", "remixes")
TEMP_REFERENCE_DIR = os.path.join(ROOT, "temp_process_kling")
DB_FILE = os.path.join(CHAR_DIR, "character_db.json")

import argparse
import glob
import random

def redo_project(project_identifier, redo_anime=False, swap_ref=False, same_ref=False):
    """
    project_identifier: e.g. 'dance_nezuko_kamado_1770088087_cosplay_on_g0kdIC8DCSs'
    """
    print(f"\n🔄 STARTING TOTAL REDO: {project_identifier}")
    
    # 1. Parse IDs
    basename = os.path.basename(project_identifier).replace(".mp4", "")
    match = re.search(r"dance_(.+)_on_(.+)", basename)
    if not match:
        print("❌ Could not parse project identifier. Expected format: 'dance_CHAR_ID_on_REF_ID'")
        return
    
    char_id_full = match.group(1) # e.g. nezuko_kamado_1770088087_cosplay
    ref_id = match.group(2)      # e.g. g0kdIC8DCSs
    
    from utils.db_utils import get_entry, upsert_asset
    # Strip _cosplay for DB lookup if present
    db_lookup_id = char_id_full.replace("_cosplay", "")
    entry = get_entry(db_lookup_id)
    if not entry:
        print(f"❌ Entry not found in DB for {char_id_full}. Cannot redo effectively.")
        return

    # 2. Locate Assets (Using DB Paths where possible)
    # Find Primary Asset
    assets_data = entry.get("assets", [])
    primary_asset = {}
    if isinstance(assets_data, list):
         primary_asset = next((a for a in assets_data if a.get("title") == "primary"), {})
    elif isinstance(assets_data, dict):
         primary_asset = assets_data # Old format fallback
         
    char_img = primary_asset.get("cosplay_image") or os.path.join(CHAR_DIR, f"{char_id_full}.png")
    base_char_img = primary_asset.get("anime_image") or char_img.replace("_cosplay.png", ".png")
    
    ref_video = os.path.join(TEMP_REFERENCE_DIR, f"{ref_id}.mp4")
    target_dance_video = os.path.join(DANCE_DIR, f"{basename}.mp4")
    target_remix_folder = os.path.join(REMIX_DIR, basename)

    from services.gemini_service import GeminiService
    service = GeminiService()

    # 3. Phase -1: Redo Anime Image
    if redo_anime:
        print(f"\n   🎨 PHASE -1: Regenerating Anime Image...")
        from workflows.character_gen import generate_creative_prompt
        concept = generate_creative_prompt(service, entry["name"], entry["anime"])
        if concept:
            prompt = concept['prompt'] + " (Makoto Shinkai style, masterpiece, 8k, highly detailed, full body, feet visible, grounded, 9:16 aspect ratio)"
            if service.generate_image(prompt=prompt, output_path=base_char_img):
                print(f"      ✅ Anime Image Redone: {base_char_img}")
                # Update DB (Prompts in root, Asset image in primary)
                # We need to manually update prompt in root entry then asset
                # Assuming update_entry still works for root fields or we use db_utils internal?
                from utils.db_utils import update_entry as update_root
                update_root(entry["id"], {
                    "metadata.name_jp": concept.get("name_jp"),
                    "metadata.anime_jp": concept.get("anime_jp"),
                    "prompts.full_prompt": prompt
                })
                upsert_asset(entry["id"], {
                    "title": "primary",
                    "anime_image": base_char_img
                })
            else:
                print(f"      ❌ Anime generation failed.")
        else:
            print(f"      ❌ Failed to generate new concept.")

    # 4. Phase 0: Redo Cosplay Image
    print(f"\n   👗 PHASE 0: Regenerating Cosplay Image...")
    # Refresh base path from DB
    entry = get_entry(db_lookup_id) or entry
    # Re-fetch primary asset
    assets_data = entry.get("assets", [])
    if isinstance(assets_data, list):
         primary_asset = next((a for a in assets_data if a.get("title") == "primary"), {})
    
    base_char_img = primary_asset.get("anime_image") or base_char_img
    
    if os.path.exists(base_char_img):
        from core.cosplay import create_cosplay_version
        if create_cosplay_version(base_char_img, char_img, service):
            print(f"      ✅ Cosplay Image Redone: {char_img}")
            upsert_asset(entry["id"], {"title": "primary", "cosplay_image": char_img})
        else:
            print(f"      ⚠️ Cosplay Image Redo Failed, using existing one.")
    else:
        print(f"      ⚠️ Base anime image not found at {base_char_img}, skipping cosplay redo.")

    # 5. Cleanup Old Work
    print(f"\n   🧹 Cleaning up old dance/remix assets...")
    if os.path.exists(target_dance_video):
        os.remove(target_dance_video)
        print(f"      🗑️ Deleted Dance Video: {target_dance_video}")
    
    if os.path.exists(target_remix_folder):
        shutil.rmtree(target_remix_folder)
        print(f"      🗑️ Deleted Remix Folder: {target_remix_folder}")

    # 6. Reference Management
    import random
    import glob
    
    # Defaults
    final_ref_video = ref_video
    
    if swap_ref:
        if same_ref:
            print("⚠️ Warning: Both --swap_ref and --same_ref passed. DEFAULTING TO SWAP.")
            
        if os.path.exists(ref_video):
            print(f"      🗑️ Deleting Old Reference Video: {ref_video}")
            try:
                os.remove(ref_video)
            except Exception as e:
                print(f"      ⚠️ Failed to delete reference: {e}")
                
        # Always pick a new random reference since we deleted the old one
        print(f"   🎲 Picking a NEW random reference dance...")
        candidates = glob.glob(os.path.join(TEMP_REFERENCE_DIR, "*.mp4"))
        
        if not candidates:
            print("❌ No other reference videos found in temp directory!")
            return

        new_ref_path = random.choice(candidates)
        new_ref_id = os.path.basename(new_ref_path).replace(".mp4", "")
        print(f"      ✨ Selected New Reference: {new_ref_id}")
        
        final_ref_video = new_ref_path
        
        # Update target paths for the NEW pairing
        new_basename = f"dance_{char_id_full}_on_{new_ref_id}"
        target_dance_video = os.path.join(DANCE_DIR, f"{new_basename}.mp4")
        target_remix_folder = os.path.join(REMIX_DIR, new_basename)
        
        # Update DB with new reference
        upsert_asset(entry["id"], {"title": "primary", "motion_ref_video": final_ref_video})
        
    elif same_ref:
        print(f"   🔄 Redoing with SAME Reference: {os.path.basename(ref_video)}")
        # Check if it actually exists (it might have been deleted if user made a mistake previously)
        if not os.path.exists(ref_video):
            # Try root fallback
            ref_video_root = os.path.join(ROOT, f"{ref_id}.mp4")
            if os.path.exists(ref_video_root):
                ref_video = ref_video_root
                final_ref_video = ref_video
            else:
                print(f"❌ Original motion reference missing: {ref_video}")
                return
        else:
            final_ref_video = ref_video
            
    else:
        # Default behavior (same as same_ref essentially, but let's be explicit)
        if not os.path.exists(ref_video):
            ref_video_root = os.path.join(ROOT, f"{ref_id}.mp4")
            if os.path.exists(ref_video_root):
                ref_video = ref_video_root
        final_ref_video = ref_video

    # Ensure DB is updated with the used ref_video (idempotent)
    if os.path.exists(final_ref_video):
        upsert_asset(entry["id"], {"title": "primary", "motion_ref_video": final_ref_video})


    # 7. Delegate to Main Pipeline (End-to-End)
    print(f"\n🚀 Delegating generation to Main Pipeline...")
    
    from workflows.main_pipeline import run_end_to_end_pipeline
    
    # We pass the paths we resolved/cleaned up above
    deliverable_path = run_end_to_end_pipeline(char_img, final_ref_video, char_id=entry["id"])
    
    if deliverable_path and os.path.exists(deliverable_path):
        upsert_asset(entry["id"], {"title": "primary", "DELIVERABLE": deliverable_path})
        print(f"      ✅ DELIVERABLE Path Saved to DB.")
        print(f"\n✨ TOTAL REDO COMPLETE. Result: {os.path.basename(deliverable_path)}")
    else:
        print("\n❌ Redo Failed during main pipeline execution.")

def loop_all_projects():
    print("\n🔄 STARTING LOOP MODE: Processing all unfinished characters...")
    
    # Reload DB
    db = load_db()
    
    # Also scan output directory for existing dance videos
    # Filename format: dance_CHAR_ID_cosplay_on_REF_ID.mp4
    dance_dir = os.path.join(ROOT, "output", "dances")
    existing_dances_map = {} # char_id -> [video_path1, video_path2, ...]
    
    if os.path.exists(dance_dir):
        files = glob.glob(os.path.join(dance_dir, "dance_*.mp4"))
        for f in files:
            basename = os.path.basename(f)
            # Try to match the ID from DB
            for entry in db:
                cid = entry["id"]
                if f"dance_{cid}_" in basename:
                    if cid not in existing_dances_map:
                        existing_dances_map[cid] = []
                    existing_dances_map[cid].append(f)
                    # Don't break, might match multiple files or multiple IDs (unlikely but safe)
    
    from workflows.main_pipeline import run_remix_pipeline, run_end_to_end_pipeline
    
    for entry in db:
        char_id = entry["id"]
        name = entry.get("name", char_id)
        print(f"\n🔍 Checking: {name} ({char_id})")
        
        # 1. Check for Deliverable
        assets = entry.get("assets", [])
        primary_asset = next((a for a in assets if a.get("title") == "primary"), None)
        
        # We process anyway to ensure registration, but skip remix if done
        is_done = False
        if primary_asset and primary_asset.get("DELIVERABLE"):
            print(f"   ✅ Finished! Deliverable found: {os.path.basename(primary_asset['DELIVERABLE'])}")
            is_done = True

        # 2. Register Found Files
        found_files = existing_dances_map.get(char_id, [])
        if found_files:
            print(f"   📂 Found {len(found_files)} matches on disk.")
            for i, fpath in enumerate(found_files):
                # Check if this exact file is already registered in ANY asset
                is_registered = False
                for asset in assets:
                    if asset.get("dance_video") == fpath:
                        is_registered = True
                        break
                
                if not is_registered:
                    # Attempt to resolve Reference Video from filename
                    # dance_{char_id}_cosplay_on_{ref_id}.mp4
                    ref_video_path = None
                    basename = os.path.basename(fpath)
                    match_ref = re.search(r"dance_.+_on_(.+)\.mp4", basename)
                    if match_ref:
                        ref_id = match_ref.group(1)
                        # Check temp dir for ref_id.mp4
                        possible_ref = os.path.join(TEMP_REFERENCE_DIR, f"{ref_id}.mp4")
                        if os.path.exists(possible_ref):
                            ref_video_path = possible_ref
                    
                    # Decide where to put it
                    if primary_asset and not primary_asset.get("dance_video"):
                        # Fill primary
                        upsert_asset(char_id, {
                            "title": "primary",
                            "dance_video": fpath,
                            # Register found Ref video, or fallback to existing, or None
                            "motion_ref_video": ref_video_path if ref_video_path else (primary_asset.get("motion_ref_video") if primary_asset else None),
                            "prompt": primary_asset.get("prompt") if primary_asset else None
                        })
                        print(f"   📝 Registered to PRIMARY: {os.path.basename(fpath)}")
                        if ref_video_path:
                            print(f"      🔗 Linked Motion Ref: {os.path.basename(ref_video_path)}")
                        
                        # Update local Ref
                        primary_asset["dance_video"] = fpath
                    else:
                        # Add as alternate
                        alt_title = f"alternate_{i+1}"
                        upsert_asset(char_id, {
                            "title": alt_title,
                            "dance_video": fpath,
                            "motion_ref_video": ref_video_path
                        })
                        print(f"   📝 Registered as {alt_title}: {os.path.basename(fpath)}")

            if dance_video_to_process:
                print(f"   🚀 Triggering REMIX Pipeline for PRIMARY: {os.path.basename(dance_video_to_process)}")
                deliverable = run_remix_pipeline(dance_video_to_process)
                
                if deliverable and os.path.exists(deliverable):
                    upsert_asset(char_id, {"title": "primary", "DELIVERABLE": deliverable})
                    print("   ✅ Deliverable Saved.")
            else:
                print("   ⚠️ No primary dance video found/registered. Skipping.")

def batch_process_redo_folder(folder_path):
    print(f"\n📂 BATCH REDO: Processing files in {folder_path}")
    if not os.path.exists(folder_path):
        print(f"❌ Folder not found: {folder_path}")
        return

    files = glob.glob(os.path.join(folder_path, "*.mp4"))
    from workflows.main_pipeline import run_end_to_end_pipeline

    processed_chars = set()

    for fpath in files:
        basename = os.path.basename(fpath)
        print(f"\n📄 Processing: {basename}")
        
        # Regex: dance_(CHAR_ID)_cosplay_on_(REF_ID).mp4
        # Note: CHAR_ID might contain underscores.
        # But we know the suffix is _cosplay_on_REF_ID.mp4
        # So we can split by "_cosplay_on_"
        
        if "_cosplay_on_" not in basename:
            print(f"   ⚠️ Skipping, filename format mismatch.")
            continue
            
        parts = basename.split("_cosplay_on_")
        if len(parts) != 2:
             print(f"   ⚠️ Skipping, filename structure error.")
             continue
             
        # prefix: dance_{char_id}
        prefix = parts[0]
        char_id = prefix.replace("dance_", "")
        
        # suffix: {ref_id}.mp4
        ref_id = parts[1].replace(".mp4", "")
        
        # Construct Paths
        char_img_path = os.path.join(CHAR_DIR, f"{char_id}.png")
        # Support potential timestamped names if needed, but exact ID is safer. 
        # Usually char_id matches exactly.
        
        ref_video_path = os.path.join(TEMP_REFERENCE_DIR, f"{ref_id}.mp4")
        
        if not os.path.exists(char_img_path):
             print(f"   ❌ Character Image not found: {char_img_path}")
             continue
             
        if not os.path.exists(ref_video_path):
             print(f"   ❌ Reference Video not found: {ref_video_path}")
             continue
             
        print(f"   ✅ Found Inputs:")
        print(f"      Char: {char_id}")
        print(f"      Ref:  {ref_id}")
        
        should_reuse = char_id in processed_chars
        print(f"   🚀 Triggering End-to-End Redo (Reuse Cosplay: {should_reuse})...")
        
        # Trigger Pipeline
        # This will:
        # 1. Regenerate Alignment (Cosplay Photo) - ONLY ONCE
        # 2. Regenerate Kling Video (Dance)
        # 3. Regenerate Remix
        res = run_end_to_end_pipeline(char_img_path, ref_video_path, char_id=char_id, reuse_cosplay=should_reuse)
        
        processed_chars.add(char_id)
        
        if res:
            print(f"   ✨ Batch Item Complete: {os.path.basename(res)}")
        else:
            print(f"   ❌ Batch Item Failed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Total Redo Pipeline")
    parser.add_argument("project", nargs='?', help="Project identifier or video path (Optional if --loop used)")
    parser.add_argument("--redo_anime", action="store_true", help="Regenerate the original anime base image")
    parser.add_argument("--swap_ref", action="store_true", help="Delete old reference and pick a random new one")
    parser.add_argument("--same_ref", action="store_true", help="Keep the existing reference video (Do not delete/swap)")
    parser.add_argument("--loop", action="store_true", help="Loop through all DB characters and finish processing")
    parser.add_argument("--batch", help="Path to folder containing videos to batch redo")
    
    args = parser.parse_args()
    
    if args.batch:
        batch_process_redo_folder(args.batch)
    elif args.loop:
        loop_all_projects()
    elif args.project:
        redo_project(args.project, redo_anime=args.redo_anime, swap_ref=args.swap_ref, same_ref=args.same_ref)
    else:
        parser.print_help()
