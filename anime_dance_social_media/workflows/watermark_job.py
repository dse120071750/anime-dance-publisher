import os
import sys
import json
import logging

try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.VideoClip import ImageClip, TextClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
except ImportError as e:
    print(f"❌ MoviePy import failed: {e}")
    sys.exit(1)

# Add path for common tools
# Add path for common tools
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

try:
    from services.gemini_service import GeminiService
except ImportError:
    from services.gemini_service import GeminiService

CHARACTER_DB_PATH = os.path.join(ROOT, "output", "characters", "character_db.json")

def load_character_db():
    if os.path.exists(CHARACTER_DB_PATH):
        with open(CHARACTER_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def get_character_info(video_filename):
    """
    Heuristic to find character in DB based on filename.
    """
    db = load_character_db()
    video_filename = video_filename.lower()
    
    # Sort DB by name length descending to match longest possible names first
    sorted_db = sorted(db, key=lambda x: len(x["id"]), reverse=True)
    
    for char in sorted_db:
        # Check by ID parts (often in filename as snake_case)
        id_core = char["id"].split("_17")[0] 
        if id_core in video_filename:
            return char
        
        # Check by exact name match (simplified)
        clean_name = char["name"].lower().replace(" ", "_")
        if clean_name in video_filename:
            return char
            
    return None

def generate_watermark_icon(service, character_info, output_path):
    """
    Generates a 'Nanobanana' style sticker icon for the watermark.
    """
    char_name = character_info["name"]
    anime_name = character_info["anime"]
    name_jp = character_info.get("name_jp", f"(Find accurate Japanese characters for {char_name})")
    anime_jp = character_info.get("anime_jp", f"(Find accurate Japanese title for {anime_name})")

    print(f"   🎨 Generating Watermark Icon for {char_name}...")
    
    prompt = (
        f"A cute, high-quality Chibi Sticker of {char_name}. "
        f"Include a significant mascot/creature/mech from {anime_name} standing next to them. "
        f"CRITICAL: At the bottom of the sticker, include a SOLID BLACK RECTANGULAR BANNER. "
        f"Inside that black banner, render the following text in multiple lines of crisp, bold WHITE font:\n"
        f"Line 1: {char_name.upper()}\n"
        f"Line 2: {name_jp}\n"
        f"Line 3: {anime_jp}\n"
        "Style: Nanobanana style, vector flat color, strong thick white die-cut outline around the entire sticker (including the black banner). "
        "Expression: Winking or Happy. "
        "Composition: Character + Mascot + 3-line Black Text Banner at bottom. "
        "Background: SOLID LIME GREEN (Hex: #00FF00). Critical for chroma keying. " 
        "High contrast, vibrant colors. "
    )
    
    # We try generation
    if not os.path.exists(output_path):
        success = service.generate_image(
            prompt=prompt,
            output_path=output_path
        )
        return success
    return True

def generate_name_sticker(service, character_info, output_path):
    """
    Generates an elegant typography logo of the character's name.
    """
    char_name = character_info["name"]
    anime_name = character_info["anime"]
    name_jp = character_info.get("name_jp", f"(Find accurate Japanese characters for {char_name})")
    anime_jp = character_info.get("anime_jp", f"(Find accurate Japanese title for {anime_name})")

    print(f"   🎨 Generating Name Sticker for {char_name}...")
    
    prompt = (
        f"An elegant, high-end typography logo layout for '{char_name.upper()}'. "
        "The text must be professionally rendered in three distinct horizontal lines:\n"
        f"Line 1: {char_name.upper()} (Elegant Bold Font)\n"
        f"Line 2: {name_jp} (Beautiful Japanese Calligraphy)\n"
        f"Line 3: {anime_jp} (Stylized Japanese Anime Title)\n"
        "Style: Minimalist black or dark navy text. Clean, sophisticated luxury branding aesthetic. "
        "Reference: High-end fashion or cinematic title typography. "
        "Background: SOLID LIME GREEN (Hex: #00FF00). Critical for chroma keying. "
        "Outline: Delicate white die-cut border around the letters for visibility. "
    )
    
    if not os.path.exists(output_path):
        return service.generate_image(prompt=prompt, output_path=output_path)
    return True

def apply_chroma_key(input_path):
    """
    Removes lime green background using OpenCV.
    """
    try:
        import cv2
        import numpy as np
        
        print(f"   ✂️ Removing background (Chroma Key): {os.path.basename(input_path)}")
        output_path = input_path.replace(".png", "_transparent.png")
        
        img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
        if img is None: return input_path
             
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            
        hsv = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2HSV)
        
        # Lime Green Range
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        
        mask = cv2.inRange(hsv, lower_green, upper_green)
        img[mask > 0, 3] = 0
        
        cv2.imwrite(output_path, img)
        return output_path
    except Exception as e:
        print(f"      ⚠️ Transparency failed: {e}")
        return input_path

def add_watermark_to_video(video_path, character_info=None):
    print(f"\n🏷️ Adding Watermark to: {os.path.basename(video_path)}")
    
    if not character_info:
        character_info = get_character_info(os.path.basename(video_path))
        
    if not character_info:
        print("   ⚠️ Could not identify character from filename. Skipping watermark.")
        return None

    char_name = character_info["name"]
    anime_name = character_info["anime"]
    
    print(f"   ✨ Identified: {char_name} ({anime_name})")
    
    # 1. Chibi Sticker (Bottom Left)
    service = GeminiService()
    chibi_filename = f"icon_{character_info['id'].split('_17')[0]}.png"
    chibi_path = os.path.join(os.path.dirname(video_path), chibi_filename)
    
    if os.path.exists(chibi_path): os.remove(chibi_path)
    if generate_watermark_icon(service, character_info, chibi_path):
        chibi_path = apply_chroma_key(chibi_path)
    else:
        chibi_path = None

    # 2. Name Sticker (Top Right)
    name_filename = f"name_{character_info['id'].split('_17')[0]}.png"
    name_path = os.path.join(os.path.dirname(video_path), name_filename)
    
    if os.path.exists(name_path): os.remove(name_path)
    if generate_name_sticker(service, character_info, name_path):
        name_path = apply_chroma_key(name_path)
    else:
        name_path = None

    try:
        clip = VideoFileClip(video_path)
        video_w, video_h = clip.size
        watermarks = [clip]

        # Add Chibi (Bottom Left)
        if chibi_path:
            wm_chibi = ImageClip(chibi_path).with_duration(clip.duration)
            target_w = video_w * 0.36
            wm_chibi = wm_chibi.resized(width=target_w)
            
            # Pos: Bottom Left
            padding = 20
            w, h = wm_chibi.size
            wm_chibi = wm_chibi.with_position((padding, video_h - h - padding))
            watermarks.append(wm_chibi)

        # Add Name (Top Right)
        if name_path:
            wm_name = ImageClip(name_path).with_duration(clip.duration)
            target_w = video_w * 0.30 # Slightly smaller
            wm_name = wm_name.resized(width=target_w)
            
            # Pos: Top Right
            padding = 20
            w, h = wm_name.size
            wm_name = wm_name.with_position((video_w - w - padding, padding))
            watermarks.append(wm_name)
        
        final = CompositeVideoClip(watermarks)
        
        output_path = video_path.replace(".mp4", "_watermarked.mp4")
        final.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        print(f"   🎉 Dual Watermarked Video: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"   ❌ Watermark application failed: {e}")
        return None

if __name__ == "__main__":
    test_target = r"C:\Users\gasil\.gemini\antigravity\playground\primordial-hubble\anime_dance_social_media\output_remix_tests\REMIX_JENNIE_dance_asuka_langley_1770088188_cosplay_on__rTwiQYvaYI_structured_scored.mp4"
    if len(sys.argv) > 1:
        test_target = sys.argv[1]
        
    add_watermark_to_video(test_target)
