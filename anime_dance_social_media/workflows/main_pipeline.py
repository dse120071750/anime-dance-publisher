import os
import sys
import time
import requests
import fal_client

# MoviePy v2.x Imports
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips
    from moviepy.video.fx.Resize import Resize
except ImportError as e:
    print(f"❌ MoviePy import failed: {e}")
    sys.exit(1)

# Add path for imports
# Add path for imports
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

try:
    from services.gemini_service import GeminiService
except ImportError:
    from services.gemini_service import GeminiService

# Import Kling submission logic
from core.animation import submit_kling_job, load_fal_key, process_active_jobs

# Import Advanced Audio Scoring
try:
    from workflows.audio_pipeline import run_advanced_audio_scoring_pipeline
except ImportError:
    run_advanced_audio_scoring_pipeline = None

OUTPUT_DIR = os.path.join(ROOT, "output", "remixes")
TEMP_DIR = os.path.join(ROOT, "output", "temp")

def ensure_dir(d):
    if not os.path.exists(d): os.makedirs(d)

def generate_outfit_variant(service, base_image_path, outfit_type, output_path):
    """
    Generates a variant of the character in a new outfit using Gemini Image 3.
    It uses the base image as a strong reference for POSE and IDENTITY.
    """
    print(f"   👗 Generating '{outfit_type}' variant for {os.path.basename(base_image_path)}...")
    
    if os.path.exists(output_path):
        print(f"      ✅ Variant exists: {output_path}")
        return output_path, "Existing Variant"

    # Prompt Engineering
    import random
    
    # Jennie Kim / Gentle Monster Inspirations
    styles = [
        "Jennie Kim style high-fashion streetwear, cropped Chanel-style tweed jacket, baggy denim, stylish sunglasses.",
        "Bold Avant-Garde K-Pop outfit, structural black bodice with silver chains, futuristic fashion.",
        "Sexy designer corset top with wide-leg cargo pants, Jennie Kim aesthetic, Y2K influence.",
        "High-end luxury swimsuit, black and white minimalist design, bold sunglasses, gold body chain.",
        "Futuristic silver chrome mini-dress, Gentle Monster aesthetic, cyber-fashion, sleek and sexy."
    ]
    
    selected_style = random.choice(styles)
    
    base_prompt = (
        "PHOTOREALISTIC FASHION PORTRAIT. "
        "Subject: The Asian female cosplayer from the reference image. "
        "Keep her exact face, hair color, and body type. "
        "Keep her pose EXACTLY the same. "
        "Follow the camera angle and posture of the targeted video frame exactly. "
        f"Outfit: {selected_style} "
        "Make it BOLD, ARTISTIC, and SEXY. "
    )
    
    bg_prompt = (
        "Background: A 'Gentle Monster' style futuristic art space. "
        "Minimalist, surreal, abstract geometric shapes, sterile white or metallic environment. "
        "NO OTHER HUMANS. Sole focus on the subject in this art installation."
    )

    full_prompt = f"{base_prompt} {bg_prompt} 8k resolution, masterpiece, editorial photography, wide angle lens. "

    if outfit_type == "swimsuit":
         # Force swimsuit choice if specifically requested, but styled high-fashion
         full_prompt = base_prompt.replace(selected_style, "Sexy high-fashion designer bikini, bold geometric cutouts, Jennie Kim style.") + " " + bg_prompt
    elif outfit_type == "kpop":
         # Apply random bold style
         pass 

    # Retry Loop for Safety
    for attempt in range(2):
        if attempt == 1:
            print("      ⚠️ Retry with softened prompt...")
            full_prompt = full_prompt.replace("sexy", "stylish").replace("Sexier", "Fashionable").replace("bikini", "one-piece swimwear")

        try:
            # Use edit_image for Image-to-Image generation
            success = service.edit_image(
                input_path=base_image_path,
                output_path=output_path,
                prompt=full_prompt
            )
            if success:
                return output_path, full_prompt
        except Exception as e:
            print(f"      ❌ Gen Failed (Attempt {attempt+1}): {e}")
            if "safety" in str(e).lower() or "block" in str(e).lower():
                continue # Retry
    
    return None, None


# Helper: Shake/Zoom Transition
def add_shake_to_start(clip, duration=0.2):
    """
    Applies a 'Zoom Slam' effect. 
    Crucially, it composites the zoomed clip onto a fixed-size canvas 
    matching the original clip to prevent the final video resolution from expanding.
    """
    try:
        w, h = clip.size
        
        # 1. Apply Dynamic Zoom (Scale 1.1x -> 1.0x)
        # We start zoomed in (1.1) and slam down to 1.0
        zoomed_clip = clip.with_effects([Resize(lambda t: 1.0 + 0.1 * max(0, (duration-t)/duration) )])
        
        # 2. Force strict dimensions by compositing
        # "center" position ensures the zoom expands outward equally
        from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
        
        final = CompositeVideoClip([zoomed_clip.with_position("center")], size=(w, h))
        return final.with_duration(clip.duration)

    except Exception as e:
        print(f"Warning: Shake effect failed {e}")
        return clip

def run_remix_pipeline(input_video_path, style_id=None):
    video_name = os.path.splitext(os.path.basename(input_video_path))[0]
    print(f"\n🚀 Starting Remix Pipeline for: {video_name}")
    
    # Try to resolve Character ID for DB updates
    # video_name format usually: dance_CHAR_ID_on_REF
    import re
    from utils.db_utils import get_entry, upsert_asset
    
    char_id = None
    match = re.search(r"dance_(.+)_on_", video_name)
    if match:
        possible_id = match.group(1).replace("_cosplay", "")
        # Validate existance
        entry = get_entry(possible_id)
        if entry:
            char_id = entry["id"]
            print(f"   👤 Linked to DB Entry: {char_id}")
    
    # Refactored Directory Structure: output/remixes/<video_name>/
    PROJECT_DIR = os.path.join(ROOT, "output", "remixes", video_name)
    VARIANTS_DIR = os.path.join(PROJECT_DIR, "variants")
    RESULT_DIR = os.path.join(PROJECT_DIR, "result")
    
    ensure_dir(PROJECT_DIR)
    ensure_dir(VARIANTS_DIR)
    ensure_dir(RESULT_DIR)
    ensure_dir(TEMP_DIR)
    
    # 1. Extract First Frame (Base for consistency)
    base_frame_path = os.path.join(VARIANTS_DIR, f"frame0.png")
    if not os.path.exists(base_frame_path):
        print("   1️⃣ Extracting base frame...")
        clip = VideoFileClip(input_video_path)
        clip.save_frame(base_frame_path, t=0)
        clip.close()
    
    # 2. Generate Variants
    service = GeminiService()
    
    # Define Variants (New Style)
    variants = [
        {"type": "jennie_swimsuit", "path": os.path.join(VARIANTS_DIR, f"jennie_swimsuit.png")},
        {"type": "jennie_kpop", "path": os.path.join(VARIANTS_DIR, f"jennie_kpop.png")}
    ]

    for v in variants:
        out_path, gen_prompt = generate_outfit_variant(service, base_frame_path, v["type"], v["path"])
        if not out_path:
            print("❌ Start aborted due to image gen failure.")
            return
        
        # Update DB: Variant Asset
        if char_id:
            upsert_asset(char_id, {
                "title": v["type"],
                "cosplay_image": out_path,
                "prompt": gen_prompt,
                "motion_ref_video": input_video_path # User wanted this repeated for context
            })

    # 3. Submit Motion Jobs (Kling)
    # We use the ORIGINAL VIDEO as the motion reference for BOTH new images.
    active_jobs = []
    
    variant_videos = {} # Store paths to resulting videos

    print("\n   2️⃣ Submitting Dance Jobs (Motion Transfer)...")
    for v in variants:
        out_video_path = os.path.join(VARIANTS_DIR, f"{v['type']}_dance.mp4")
        variant_videos[v["type"]] = out_video_path
        
        if os.path.exists(out_video_path):
            print(f"      ✅ Video exists: {out_video_path}")
            continue

        job = submit_kling_job(v["path"], input_video_path) # Image=Variant, Video=Reference
        if job:
            job["final_output"] = out_video_path
            job["variant_type"] = v["type"] # Tag for post-processing
            active_jobs.append(job)

    # Wait for jobs
    if active_jobs:
        print(f"   ⏳ Waiting for {len(active_jobs)} videos to generate...")
        process_active_jobs(active_jobs)
        
        # After completion, update DB with video paths
        if char_id:
            for job in active_jobs:
                if os.path.exists(job["final_output"]):
                    v_type = job.get("variant_type")
                    if v_type:
                        upsert_asset(char_id, {
                            "title": v_type,
                            "dance_video": job["final_output"]
                        })
            
            print(f"      ✅ DB Updated with variant dance videos.")

    # 4. Remix / Edit
    print(f"\n   3️⃣ Editing Remix Video...")
    
    # Load clips
    processed_videos = {}
    try:
        # Load Original
        processed_videos["original"] = VideoFileClip(input_video_path)
        # Load New Ones
        for v in variants:
            p = variant_videos[v["type"]]
            if os.path.exists(p):
                processed_videos[v["type"]] = VideoFileClip(p)
            else:
                print(f"      ❌ Missing video for {v['type']}, cannot remix.")
                return

        # FIX: Ensure we don't exceed the shortest video length
        # Kling often generates 5s/10s. If raw input is 20s, we must cap duration.
        min_duration = min(c.duration for c in processed_videos.values())
        duration = min_duration
        print(f"      ⏱️ Remix Duration capped to: {duration:.2f}s (Shortest clip limit)")
        
        # Calculate segments
        seg_duration = duration / 3.0
        
        # 0 -> D/3 : Original
        part1 = processed_videos["original"].subclipped(0, seg_duration)
        
        # D/3 -> 2D/3 : Swimsuit
        part2 = processed_videos["jennie_swimsuit"].subclipped(seg_duration, seg_duration*2)
        part2 = add_shake_to_start(part2) # Apply Trans
        
        # 2D/3 -> D : Kpop
        part3 = processed_videos["jennie_kpop"].subclipped(seg_duration*2, duration)
        part3 = add_shake_to_start(part3) # Apply Trans
        
        final_clip = concatenate_videoclips([part1, part2, part3], method="compose")
        
        final_output_path = os.path.join(RESULT_DIR, f"REMIX_JENNIE_{video_name}.mp4")
        
        if os.path.exists(final_output_path):
             print(f"\n✅ Skip Remixing, file exists: {final_output_path}")
        else:
            final_clip.write_videofile(final_output_path, codec="libx264", audio_codec="aac")
            print(f"\n🎉 REMIX COMPLETE: {final_output_path}")

        # 5. Audio Scoring (Auto Sync & Phonk Gen)
        # 5. Audio Scoring (Auto Sync & Phonk Gen)
        final_scored_path = final_output_path
        expected_scored_path = final_output_path.replace(".mp4", "_structured_scored.mp4")
        
        if os.path.exists(expected_scored_path):
            print(f"\n✅ Skip Audio Scoring, file exists: {expected_scored_path}")
            final_scored_path = expected_scored_path
        elif run_advanced_audio_scoring_pipeline:
            print(f"\n🎵 Starting Advanced Audio Scoring (Style: {style_id if style_id else 'default'})...")
            scored_path = run_advanced_audio_scoring_pipeline(final_output_path, style_id=style_id)
            if scored_path and os.path.exists(scored_path):
                final_scored_path = scored_path
            else:
                print("      ⚠️ Scoring returned no valid path, using original remix.")
        else:
            print("⚠️ Audio scoring module not found, skipping sync.")

        # 6. Watermark (Sticker)
        try: 
            from workflows.watermark_job import add_watermark_to_video
            print("\n🏷️ Applying Watermark...")
            
            # Check if watermarked version already exists
            expected_wm_path = final_scored_path.replace(".mp4", "_watermarked.mp4")
            if os.path.exists(expected_wm_path):
                print(f"✅ Skip Watermarking, file exists: {expected_wm_path}")
                watermarked_path = expected_wm_path
            else:
                watermarked_path = add_watermark_to_video(final_scored_path)
                
            if watermarked_path:
                print(f"\n✨ FINAL DELIVERABLE: {watermarked_path}")
                
                # 7. Move Final Deliverable to Project Root
                import shutil
                project_root_final = os.path.join(PROJECT_DIR, os.path.basename(watermarked_path))
                shutil.copy2(watermarked_path, project_root_final)
                print(f"✅ Final video copied to: {project_root_final}")
                
                return project_root_final
        except ImportError:
            print("⚠️ Watermark module not found.")

        # Cleanup
        for k, c in processed_videos.items():
            c.close()
            
    except Exception as e:
        print(f"❌ Editing Error: {e}")
        import traceback
        traceback.print_exc()

from workflows.alignment_pipeline import align_character_to_video
from services.gemini_service import GeminiService
from core.cosplay import create_cosplay_version
# ... existing ...

def run_primary_dance_generation(char_img, ref_video, char_id=None, reuse_cosplay=False):
    """
    Phase 1: Generates the primary dance video using Kling.
    Handles Cosplay Gen -> Alignment -> Submission.
    """
    print(f"\n🎬 STARTING PRIMARY DANCE GENERATION")
    print(f"   👤 Character: {os.path.basename(char_img)}")
    print(f"   🎥 Reference: {os.path.basename(ref_video)}")
    
    # 0. Ensure Cosplay Version Exists (or Regenerate)
    # If the input is the Anime Image (assumed if not ending in _cosplay.png)
    input_for_alignment = char_img
    
    # Check if we should create a cosplay version
    # Note: char_img is likely output/characters/NAME.png
    basename = os.path.basename(char_img)
    
    if "_cosplay" not in basename:
        service = GeminiService()
        cosplay_path = char_img.replace(".png", "_cosplay.png")
        
        should_generate = True
        if reuse_cosplay and os.path.exists(cosplay_path):
            print(f"   ✨ Reusing existing Cosplay Version: {os.path.basename(cosplay_path)}")
            should_generate = False
            input_for_alignment = cosplay_path
        
        if should_generate:
            print(f"   ✨ Generating/Updating Cosplay Version: {os.path.basename(cosplay_path)}")
            
            try:
                 # Fetch Metadata for better prompting
                 char_name = None
                 anime_name = None
                 if char_id:
                     from utils.db_utils import get_entry
                     entry = get_entry(char_id)
                     if entry:
                         char_name = entry.get("name", char_id)
                         anime_name = entry.get("anime")

                 # Force creation (since this is a REDO pipeline)
                 # Core cosplay function: create_cosplay_version(anime_path, output_path, service, char_name, anime_name)
                 success = create_cosplay_version(char_img, cosplay_path, service, character_name=char_name, anime_name=anime_name)
                 if success:
                     input_for_alignment = cosplay_path
                     # Update DB if ID provided (Cosplay asset)
                     if char_id:
                         from utils.db_utils import upsert_asset
                         upsert_asset(char_id, {"title": "primary", "cosplay_image": cosplay_path})
            except Exception as e:
                print(f"   ⚠️ Cosplay generation failed: {e}. Using original image.")

    # 1. Alignment
    aligned_img, alignment_prompt = align_character_to_video(input_for_alignment, ref_video)
    input_source = aligned_img if aligned_img else input_for_alignment
    
    if char_id and alignment_prompt:
        from utils.db_utils import upsert_asset
        upsert_asset(char_id, {"title": "primary", "prompt": alignment_prompt})
        print(f"   📝 Saved Alignment Prompt to DB.")

    # 2. Kling Submission
    # Ideally we determine output path here to check existence, but process_active_jobs handles it.
    job = submit_kling_job(input_source, ref_video)
    if not job:
        print("❌ Kling Submission Failed.")
        return None, None
        
    # Define expected output path based on standard naming if possible, 
    # or let process_active_jobs determine it. 
    # For consistency with redo_pipeline, we construct it:
    # dance_CHAR_on_REF.mp4
    char_base = os.path.splitext(os.path.basename(char_img))[0].replace("_cosplay", "")
    ref_base = os.path.splitext(os.path.basename(ref_video))[0]
    target_filename = f"dance_{char_base}_cosplay_on_{ref_base}.mp4"
    target_path = os.path.join(ROOT, "output", "dances", target_filename)
    
    job["final_output"] = target_path
    
    print(f"   ⏳ Waiting for Primary Dance Generation...")
    process_active_jobs([job])
    
    if os.path.exists(target_path):
        print(f"   ✅ Primary Dance Ready: {target_path}")
        if char_id:
             from utils.db_utils import upsert_asset
             upsert_asset(char_id, {"title": "primary", "dance_video": target_path})
        return target_path, alignment_prompt
    else:
        print("❌ Primary Dance Generation Failed.")
        return None, None

def run_end_to_end_pipeline(char_img, ref_video, char_id=None, reuse_cosplay=False, style_id=None):
    """
    Orchestrates the full flow: Primary Dance -> Remix -> Deliverable.
    """
    # Phase 1
    dance_path, _ = run_primary_dance_generation(char_img, ref_video, char_id, reuse_cosplay=reuse_cosplay)
    
    if not dance_path:
        return None
        
    # Phase 2 & 3
    final_deliverable = run_remix_pipeline(dance_path, style_id=style_id)
    return final_deliverable

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        # Check if it's an image (start new) or video (remix only)
        if target.endswith(".png") or target.endswith(".jpg"):
             # Usage: full_pipe.py <char_img> <ref_video>
             if len(sys.argv) > 2:
                 run_end_to_end_pipeline(target, sys.argv[2])
             else:
                 print("Need Ref Video for end-to-end")
        else:
             run_remix_pipeline(target)
    else:
        # Default test video (Yor Forger)
        target_video = os.path.join(ROOT, "output", "dances", "dance_yor_forger_1770088212_cosplay_on_3mYs0OYieUs.mp4")
        if os.path.exists(target_video):
            run_remix_pipeline(target_video)

