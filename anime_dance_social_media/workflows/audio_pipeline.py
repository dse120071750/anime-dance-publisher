import os
import sys
import json
import time

# Add path
# Add path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

# Import AI Services
try:
    from services.gemini_service import GeminiService
    from services.minimax_service import MinimaxService
except ImportError:
    from services.gemini_service import GeminiService
    from services.minimax_service import MinimaxService

# Imports for MoviePy
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.audio.AudioClip import CompositeAudioClip
    from moviepy.audio.fx.AudioFadeOut import AudioFadeOut
except ImportError:
    try:
        from moviepy import *
    except:
        pass

# Initialize Services
gemini = GeminiService()
minimax = MinimaxService()

# --- 1. VISUAL STRUCTURE ANALYSIS ---
def analyze_dance_structure(video_path, analysis_instruction=None):
    print(f"\n   👁️ [Step 1] Analyzing Dance Structure & Sections...")
    
    default_instruction = (
        "Analyze the dance video precisely. Determine the BPM and break the choreography down into musical sections based on energy."
        "For each section, specify the Start Time, End Time, Tag (Intro, Verse, Build, Drop/Chorus), and a detailed description of the beat/music that should accompany it."
        "The 'First Hard Beat' or 'Drop' must align with the most energetic move."
    )
    
    prompt = analysis_instruction if analysis_instruction else default_instruction
    prompt += (
        "\n\nReturn ONLY valid JSON in this format:\n"
        "{\n"
        "  \"bpm\": 128,\n"
        "  \"sections\": [\n"
        "    {\"start\": 0.0, \"end\": 2.5, \"tag\": \"Intro\", \"beat_desc\": \"melodic sequence\"},\n"
        "    {\"start\": 2.5, \"end\": 10.0, \"tag\": \"Chorus\", \"beat_desc\": \"high energy drop\"}\n"
        "  ]\n"
        "}"
    )
    
    bpm = 120
    sections = []
    
    try:
        # Pass video path directly, service handles upload
        text_response = gemini.generate_text(prompt, context_files=[video_path])
        
        if text_response:
            text = text_response.replace("```json", "").replace("```", "")
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                bpm = data.get("bpm", 120)
                sections = data.get("sections", [])
                print(f"      ✅ Structure Found: {bpm} BPM, {len(sections)} Sections")
                for s in sections:
                    print(f"         - {s['start']}s -> {s['end']}s : [{s['tag']}] {s['beat_desc']}")
    except Exception as e:
        print(f"      ❌ Analysis Error: {e}")
        sections = [{"start": 0, "end": 15, "tag": "Chorus", "beat_desc": "High energy beat"}]

    # Return None for the third arg as we don't pass file objects around anymore
    return sections, bpm, None

# --- 2. CONSTRUCT PROMPT & GENERATE ---
def generate_structured_music(sections, bpm, output_dir, style_description=None):
    print(f"\n   🎵 [Step 2] Generating Structured Music ({bpm} BPM)...")
    
    full_lyrics = ""
    prompt_desc = f"A high-quality track at {bpm} BPM. Structure: "
    
    if not sections:
        sections = [{"tag": "Chorus", "beat_desc": "High energy beat"}]

    for s in sections:
        tag = s.get("tag", "Verse").capitalize()
        desc = s.get("beat_desc", "")
        start = s.get("start", 0)
        end = s.get("end", 0)
        
        full_lyrics += f"[{tag}] ({start}s-{end}s)\n(Instrumental: {desc})\n"
        prompt_desc += f"[{tag} {start}-{end}s] {desc}; "
        
    if style_description:
        prompt_desc += f" {style_description}"
    else:
        prompt_desc += " Japanese Phonk style, high energy drift phonk, melodic cowbells, anime racing aesthetic, clean production."
    
    print(f"      📝 Prompt: {prompt_desc[:150]}...")
    
    out_path = os.path.join(output_dir, "generated_structured_music.mp3")
    result_path = minimax.generate_music(prompt_desc, full_lyrics, out_path)
    
    return result_path

# --- 3. MERGE ---
def smart_sync_merge(video_path, audio_path, video_file_path_for_reuse=None):
    print(f"\n   ⚖️ [Step 3] Smart Sync & Merge...")
    
    # Audio Drop
    print("      ...Finding Audio Drop...")
    aud_ms = 0
    try:
        p_aud = "Identify timestamp (ms) of the main Beat Drop/Chorus start. JSON: {\"timestamp_ms\": 1000}"
        res_a = gemini.generate_text(p_aud, context_files=[audio_path])
        if res_a:
            import re
            match = re.search(r"\{.*\}", res_a, re.DOTALL)
            if match:
                aud_ms = json.loads(match.group(0))["timestamp_ms"]
                print(f"      👂 Audio Drop detected at {aud_ms}ms")
    except Exception as e:
        print(f"      ⚠️ Audio Analysis Failed: {e}")

    # Video Drop
    print("      ...Finding Video Drop...")
    vis_ms = 0
    try:
        # Use video_path directly
        p_vid = "Identify timestamp (ms) of the main energetic Dance Drop or First Hard Hit. JSON: {\"timestamp_ms\": 2000}"
        res_v = gemini.generate_text(p_vid, context_files=[video_path])
        if res_v:
             import re
             match = re.search(r"\{.*\}", res_v, re.DOTALL)
             if match:
                vis_ms = json.loads(match.group(0))["timestamp_ms"]
                print(f"      👁️ Video Drop detected at {vis_ms}ms")
    except: pass
    
    offset = (vis_ms - aud_ms) / 1000.0
    print(f"      👉 Sync Offset: {offset:.3f}s")
    
    # Merge
    out_path = video_path.replace(".mp4", "_structured_scored.mp4")
    try:
        vid = VideoFileClip(video_path)
        aud = AudioFileClip(audio_path)
        
        final_audio = aud
        if offset > 0:
            final_audio = CompositeAudioClip([aud.with_start(offset)])
        elif offset < 0:
            trim = abs(offset)
            if trim >= aud.duration:
                trim = aud.duration - 0.1
            final_audio = aud.subclipped(trim, aud.duration)
            
        # Handle Short Audio Loop
        target_dur = vid.duration
        if final_audio.duration < target_dur:
            try:
                from moviepy.audio.AudioClip import concatenate_audioclips
                loops = int(target_dur / final_audio.duration) + 1
                final_audio = concatenate_audioclips([final_audio] * (loops + 1))
            except: pass

        # Final Trim
        final_audio = final_audio.subclipped(0, min(target_dur, final_audio.duration))
        try:
            final_audio = final_audio.with_effects([AudioFadeOut(duration=1.0)])
        except: pass
        
        vid.with_audio(final_audio).write_videofile(out_path, codec="libx264", audio_codec="aac")
        print(f"   🎉 FINAL: {out_path}")
        return out_path
        
    except Exception as e:
        print(f"      ❌ Merge Failed: {e}")
        return None

def simple_merge(video_path, audio_path, output_path=None):
    """
    Merge audio onto video directly WITHOUT offset detection.
    Just trims/loops audio to match video duration.
    """
    print(f"\n   🎵 Simple Merge (No Offset Detection)...")
    
    if not output_path:
        output_path = video_path.replace(".mp4", "_simple_scored.mp4")
    
    try:
        vid = VideoFileClip(video_path)
        aud = AudioFileClip(audio_path)
        
        target_dur = vid.duration
        final_audio = aud
        
        # Loop if too short
        if aud.duration < target_dur:
            try:
                from moviepy.audio.AudioClip import concatenate_audioclips
                loops = int(target_dur / aud.duration) + 1
                final_audio = concatenate_audioclips([aud] * loops)
            except: pass
        
        # Trim to match
        final_audio = final_audio.subclipped(0, min(target_dur, final_audio.duration))
        
        # Fade out
        try:
            final_audio = final_audio.with_effects([AudioFadeOut(duration=1.0)])
        except: pass
        
        vid.with_audio(final_audio).write_videofile(output_path, codec="libx264", audio_codec="aac")
        print(f"   ✅ Simple Merge Complete: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"   ❌ Simple Merge Failed: {e}")
        return None


def run_advanced_audio_scoring_pipeline(target_video_path, style_id=None):
    from utils.db_utils import get_music_style
    
    # Default to kpop_dance if none provided, or if provided style doesn't exist
    style_obj = None
    if style_id:
        style_obj = get_music_style(style_id)
    
    if not style_obj:
        style_obj = get_music_style("kpop_dance")

    if not style_obj:
        # Fallback if DB is missing or logic fails
        style_obj = {
            "description": "High energy K-Pop dance music",
            "gemini_analysis_prompt": "Analyze the dance for K-Pop choreography hits."
        }
    
    # 1. Structure Analysis (Dynamic Instruction)
    sections, bpm, _ = analyze_dance_structure(
        target_video_path, 
        analysis_instruction=style_obj.get("gemini_analysis_prompt")
    )
    
    if sections:
        # 2. Generate Music (Dynamic Style)
        out_dir = os.path.dirname(target_video_path)
        aud_path = generate_structured_music(
            sections, 
            bpm, 
            out_dir, 
            style_description=style_obj.get("description")
        )
        
        if aud_path:
            # 3. Sync & Merge
            return smart_sync_merge(target_video_path, aud_path)
    return None

if __name__ == "__main__":
    target = r"C:\Users\gasil\.gemini\antigravity\playground\primordial-hubble\anime_dance_social_media\output_remix_tests\REMIX_JENNIE_dance_asuka_langley_1770088188_cosplay_on__rTwiQYvaYI.mp4"
    if len(sys.argv) > 1: target=sys.argv[1]
    run_advanced_audio_scoring_pipeline(target)
