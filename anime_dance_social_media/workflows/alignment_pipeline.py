
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from core.animation import swap_first_frame

def align_character_to_video(character_image_path, reference_video_path):
    """
    Pipeline to align a character image to the pose of the first frame of a reference video.
    Returns the path to the aligned image.
    """
    if not os.path.exists(character_image_path):
        print(f"❌ Alignment Failed: Character image not found: {character_image_path}")
        return None
        
    if not os.path.exists(reference_video_path):
        print(f"❌ Alignment Failed: Reference video not found: {reference_video_path}")
        return None

    # Define Output Path
    # We store aligned images in a 'temp/aligned' folder or similar to avoid clutter
    TEMP_ALIGN_DIR = os.path.join(ROOT, "temp_process_kling", "aligned_inputs")
    if not os.path.exists(TEMP_ALIGN_DIR):
        os.makedirs(TEMP_ALIGN_DIR)
        
    char_basename = os.path.basename(character_image_path).replace(".png", "")
    ref_basename = os.path.basename(reference_video_path).replace(".mp4", "")
    
    aligned_filename = f"aligned_{char_basename}_on_{ref_basename}.png"
    aligned_path = os.path.join(TEMP_ALIGN_DIR, aligned_filename)
    
    print(f"\n🧘 STARTING ALIGNMENT PIPELINE")
    print(f"   👤 Character: {char_basename}")
    print(f"   🎥 Reference: {ref_basename}")
    
    # Check if already exists? (Optional caching)
    # User might want to force redo if they are running a redo pipeline, so maybe skipping cache check is safer or provide flag.
    # We will overwrite.
    
    swapped_path, prompt = swap_first_frame(reference_video_path, character_image_path, aligned_path)
    
    if swapped_path and os.path.exists(swapped_path):
        print(f"   ✅ Alignment Success: {aligned_path}")
        return aligned_path, prompt
    else:
        print("   ❌ Alignment Failed.")
        return None, None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python alignment_pipeline.py <char_img> <ref_video>")
    else:
        align_character_to_video(sys.argv[1], sys.argv[2])
