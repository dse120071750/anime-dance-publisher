import os
import sys
import glob

# Add root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from moviepy import VideoFileClip, AudioFileClip
from workflows.audio_pipeline import (
    analyze_dance_structure, 
    generate_structured_music, 
    simple_merge
)
from workflows.watermark_job import add_watermark_to_video


REMIXES_DIR = os.path.join(ROOT, "output", "remixes")

def process_remix_folder(folder_path, style_id="kpop_dance"):
    """
    Process a single remix folder:
    1. Find existing watermarked video (no regeneration)
    2. Extract original audio -> orig_music.mp3
    3. Generate K-Pop music -> generated_kpop_music.mp3
    4. Create [orig_soundtrack] and [kpop_soundtrack] versions
    """
    folder_name = os.path.basename(folder_path)
    result_dir = os.path.join(folder_path, "result")
    
    if not os.path.exists(result_dir):
        print(f"   ⚠️ No result folder in {folder_name}")
        return
    
    # Find the EXISTING watermarked video (the final output)
    watermarked_video = None
    base_remix = None
    
    for f in os.listdir(result_dir):
        if f.startswith("REMIX_JENNIE_") and f.endswith("_structured_scored_watermarked.mp4"):
            watermarked_video = os.path.join(result_dir, f)
        elif f.startswith("REMIX_JENNIE_") and f.endswith(".mp4"):
            if "_scored" not in f and "_watermarked" not in f and "[" not in f:
                base_remix = os.path.join(result_dir, f)
    
    if not watermarked_video or not os.path.exists(watermarked_video):
        print(f"   ⚠️ No watermarked video found in {folder_name}")
        return
    
    if not base_remix or not os.path.exists(base_remix):
        print(f"   ⚠️ No base remix found in {folder_name}")
        return
    
    base_name = os.path.splitext(os.path.basename(watermarked_video))[0].replace("_structured_scored_watermarked", "")
    
    # --- EXTRACT ORIGINAL AUDIO ---
    orig_audio_path = os.path.join(result_dir, "orig_music.mp3")
    if not os.path.exists(orig_audio_path):
        print(f"   🎵 Extracting original audio from base remix...")
        try:
            clip = VideoFileClip(base_remix)
            if clip.audio:
                clip.audio.write_audiofile(orig_audio_path)
                print(f"   ✅ Saved: orig_music.mp3")
            clip.close()
        except Exception as e:
            print(f"   ❌ Audio extraction failed: {e}")
    
    # --- 1. ORIGINAL SOUNDTRACK VERSION ---
    orig_output = os.path.join(result_dir, f"[orig_soundtrack]_{base_name}_watermarked.mp4")
    
    if os.path.exists(orig_output):
        print(f"   ✅ [orig_soundtrack] already exists")
    elif os.path.exists(orig_audio_path):
        print(f"   🎵 Creating [orig_soundtrack]...")
        simple_merge(watermarked_video, orig_audio_path, orig_output)
        if os.path.exists(orig_output):
            print(f"   ✅ Created: {os.path.basename(orig_output)}")
    
    # --- GENERATE K-POP MUSIC ---
    kpop_audio_path = os.path.join(result_dir, "generated_kpop_music.mp3")
    
    if not os.path.exists(kpop_audio_path):
        print(f"   🎶 Generating K-Pop music...")
        try:
            from utils.db_utils import get_music_style
            style_obj = get_music_style(style_id)
            if not style_obj:
                style_obj = {"description": "High energy K-Pop dance music", "gemini_analysis_prompt": "Analyze for K-Pop hits."}
            
            # Analyze dance structure from base remix
            sections, bpm, _ = analyze_dance_structure(base_remix, analysis_instruction=style_obj.get("gemini_analysis_prompt"))
            
            # Generate K-Pop music
            temp_audio = generate_structured_music(sections, bpm, result_dir, style_description=style_obj.get("description"))
            
            if temp_audio and os.path.exists(temp_audio):
                # Rename to consistent name
                os.rename(temp_audio, kpop_audio_path)
                print(f"   ✅ Saved: generated_kpop_music.mp3")
        except Exception as e:
            print(f"   ❌ K-Pop generation failed: {e}")
    
    # --- 2. K-POP SOUNDTRACK VERSION ---
    kpop_output = os.path.join(result_dir, f"[kpop_soundtrack]_{base_name}_watermarked.mp4")
    
    if os.path.exists(kpop_output):
        print(f"   ✅ [kpop_soundtrack] already exists")
    elif os.path.exists(kpop_audio_path):
        print(f"   🎶 Creating [kpop_soundtrack]...")
        simple_merge(watermarked_video, kpop_audio_path, kpop_output)
        if os.path.exists(kpop_output):
            print(f"   ✅ Created: {os.path.basename(kpop_output)}")


def run_batch_soundtrack_remix(style_id="kpop_dance"):
    """
    Scan all remix folders and create dual soundtrack versions.
    """
    print(f"\n🚀 BATCH DUAL SOUNDTRACK REMIX")
    print(f"🎵 Style ID: {style_id}")
    print(f"📂 Scanning: {REMIXES_DIR}")
    
    # Find all remix folders (directories starting with 'dance_')
    remix_folders = [
        os.path.join(REMIXES_DIR, d) 
        for d in os.listdir(REMIXES_DIR) 
        if os.path.isdir(os.path.join(REMIXES_DIR, d)) and d.startswith("dance_")
    ]
    
    print(f"   📋 Found {len(remix_folders)} remix folders")
    
    for folder in remix_folders:
        print(f"\n📁 Processing: {os.path.basename(folder)}")
        process_remix_folder(folder, style_id=style_id)
    
    print(f"\n🎉 BATCH COMPLETE")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch Dual Soundtrack Remix")
    parser.add_argument("--style_id", default="kpop_dance", help="Music style ID")
    args = parser.parse_args()
    
    run_batch_soundtrack_remix(style_id=args.style_id)
