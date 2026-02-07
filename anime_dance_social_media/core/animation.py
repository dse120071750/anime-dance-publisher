import os
import sys
import fal_client
import requests
import time
import shutil
import traceback

# Add current dir to path
# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

try:
    from services.gemini_service import GeminiService
except ImportError:
    # Try alternate or just fail, but structure should be correct now
    # If run as module, this might fail, but sys.path fixes it for scripts
    from services.gemini_service import GeminiService

# Try imports
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
except ImportError:
    try:
        from moviepy.editor import VideoFileClip
    except ImportError:
        print("❌ MoviePy not found. Please install it: pip install moviepy")
        sys.exit(1)

# Temp dir for operations
TEMP_TRIM_DIR = os.path.join(ROOT, "output", "temp")

def load_fal_key():
    key = os.environ.get("FAL_AI_KEY")
    if key: return key
    env_path = os.path.join(ROOT, "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith("FAL_AI_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"')
    return None

def swap_first_frame(video_path, char_ref_path, output_frame_path):
    """
    Extracts first frame of video, uses Gemini to create a prompt combining pose + char + bg,
    then generates a swapped image using Gemini Image.
    """
    print(f"   📸 Creating Swapped Reference Frame for: {video_path}")
    
    # 1. Extract Frame
    try:
        clip = VideoFileClip(video_path)
        if not os.path.exists(TEMP_TRIM_DIR): os.makedirs(TEMP_TRIM_DIR)
        temp_first_frame = os.path.join(TEMP_TRIM_DIR, f"first_{os.path.basename(video_path)}.png")
        
        clip.save_frame(temp_first_frame, t=0)
        clip.close()
    except Exception as e:
        print(f"      ❌ Error extracting frame: {e}")
        return None, None

    # 2. Init Service
    try:
        service = GeminiService()
    except Exception as e:
        print(f"      ❌ Error init GeminiService: {e}")
        return None, None

    # 3. Generate Prompt
    is_cosplay = "_cosplay" in os.path.basename(char_ref_path)
    style_instruction = (
        "PHOTOREALISTIC 1990s COSPLAY PHOTO. "
        "The subject must look like a REAL HUMAN in a costume." 
        if is_cosplay else 
        "High quality anime style (2D/2.5D)."
    )
    
    bg_instruction = (
        "The background must MATCH Image 2 (The Character Reference) content/scene. "
        "CRITICAL: The background must be rendered as a REAL PHOTOGRAPH, not anime. "
        "It must look like a real location photographed on 1990s film (grain, depth of field)."
    )

    instruction = (
        "You are an expert art director + Character Designer. "
        "Image 1 is the POSE AND FRAMING REFERENCE (posture, camera angle, zoom level). "
        "Image 2 is the CHARACTER AND BACKGROUND REFERENCE. "
        "Write a detailed image generation prompt to generate a new image where:\n"
        "1. The Subject is the CHARACTER from Image 2 (Same face, same outfit, same hair).\n"
        "2. The Background involves the SAME SCENE as Image 2 but rendered as a PHOTO.\n"
        "3. The Pose/Action matches Image 1 EXACTLY.\n"
        "4. The Camera Angle, Framing, and Field of View MUST match Image 1 EXACTLY (e.g. if Image 1 is a close-up, output a close-up).\n"
        f"5. The Art Style is: {style_instruction}\n"
        "Output ONLY the prompt description text."
    )
    
    print("      🧠 Generating Prompt with Gemini...")
    context_images = [temp_first_frame]
    if os.path.exists(char_ref_path):
        context_images.append(char_ref_path)
        
    try:
        prompt = service.generate_text(instruction, context_files=context_images)
        if not prompt:
            print("      ❌ Failed to generate prompt.")
            return None, None
            
        # Enforce Constraints
        prompt += f" {style_instruction} {bg_instruction}" 
        prompt += " Match the EXACT camera angle, framing, crop,  character posture , and composition of reference image_1. Do not zoom out if image_1 is a close-up."
    except Exception as e:
        print(f"      ❌ Error generating prompt: {e}")
        return None, None

    # 4. Generate Image
    print("      🎨 Generating Swapped Image...")
    try:
        # Note: GeminiService.generate_image currently only takes a prompt in my simplistic implementation.
        # But 'edit_image' takes input path.
        # Wait, swap_first_frame needs Img2Img or ControlNet equivalent.
        # Ideally we use `edit_image` starting from the POSE (first frame) and prompting the CHARACTER?
        # OR starting from Character and prompting Pose?
        # The prompt implies we are generating NEW image.
        # Let's use `edit_image` on the POSE FRAME (temp_first_frame) using the Generated Prompt.
        
        success = service.edit_image(
            input_path=temp_first_frame,
            output_path=output_frame_path,
            prompt=prompt
        )
        
        if success:
            print(f"      ✅ Swapped Frame Ready: {output_frame_path}")
            return output_frame_path, prompt
        else:
            print(f"      ❌ Failed to generate swapped image.")
            return None, None
    except Exception as e:
        print(f"      ❌ Error generating image: {e}")
        return None, None


def submit_kling_job(final_image_path, video_path):
    """
    Submits a job to Kling and returns the request_handle (or dict with request_id).
    Does NOT wait for completion.
    """
    print(f"\n🚀 Submitting Kling Job: {os.path.basename(video_path)} with {os.path.basename(final_image_path)}")
    
    # Setup Auth
    fal_key = load_fal_key()
    if not fal_key: return None
    os.environ["FAL_KEY"] = fal_key
    
    # Init Gemini
    try:
        service = GeminiService()
    except:
        service = None

    upload_video_path = video_path
    temp_trim_path = None

    try:
        # Check Trim logic
        orientation = "video" # Default, will be overridden if needed
        clip = VideoFileClip(video_path)
        duration = clip.duration
        
        max_duration = 15.0 # User requested limit to avoid upload errors
        
        if duration > max_duration:
            print(f"   ⚠️ Video duration {duration:.2f}s exceeds limit {max_duration}s. Trimming...")
            if not os.path.exists(TEMP_TRIM_DIR): os.makedirs(TEMP_TRIM_DIR)
            temp_trim_path = os.path.join(TEMP_TRIM_DIR, f"trim_{os.path.basename(video_path)}.mp4")
            
            # Use safe subclip
            sub = clip.subclipped(0, max_duration)
            sub.write_videofile(temp_trim_path, codec="libx264", audio_codec="aac", logger=None)
            sub.close()
            upload_video_path = temp_trim_path
        else:
            upload_video_path = video_path
            
        clip.close()

        # Generate Prompt
        video_prompt = "an anime girl dancing with still camera."
        if service:
            analysis_instruction = (
                "Describe this image in 1 sentence for a text-to-video generator. "
                "Focus on the subject and the setting. "
                "Add dynamic keywords suitable for a dance video (e.g., 'character dancing', 'cinematic lighting', '4k'). "
                "If there are background elements (trains, trees, lights), mention them moving slightly. "
                "Keep it under 30 words."
            )
            try:
                gen_prompt = service.generate_text(analysis_instruction, context_files=[final_image_path])
                if gen_prompt: video_prompt = gen_prompt.strip()
            except: pass

        # Upload
        print(f"   📤 Uploading Swapped Frame... {final_image_path}")
        image_url = fal_client.upload_file(final_image_path)
        print(f"   📤 Uploading Video... {upload_video_path}")
        video_url = fal_client.upload_file(upload_video_path)
        
        print("   ⏳ Waiting 2s for upload...")
        time.sleep(2)

        # Submit Async
        print(f"   📡 Sending Request to FAL...")
        handler = fal_client.submit(
            "fal-ai/kling-video/v2.6/pro/motion-control",
            arguments={
                "image_url": image_url,
                "video_url": video_url,
                "character_orientation": orientation,
                "prompt": video_prompt
            }
        )
        
        return {
            "handler": handler,
            "video_path": video_path,
            "temp_trim": temp_trim_path,
            "prompt": video_prompt
        }

    except Exception as e:
        print(f"❌ Submission Failed: {e}")
        return None

# NOTE: The original process_kling_video is REMOVED to force using the new batch flow, 
# or aliased to a synchronous wrapper if needed. For now I replace it with these components.

def process_active_jobs(job_list):
    """
    Waits for a list of jobs to finish and downloads results.
    """
    for job in job_list:
        handler = job["handler"]
        out_path = job["final_output"]
        
        print(f"   ⏳ Waiting for result: {os.path.basename(out_path)}...")
        try:
            # Iterating events helps keep connection alive usually, or just .get()
            result = None
            try:
                for event in handler.iter_events(with_logs=True):
                    if isinstance(event, fal_client.InProgress):
                        pass
            except:
                pass
            
            # Get final result
            result = handler.get()
            
            if result and "video" in result and "url" in result["video"]:
                download_url = result["video"]["url"]
                print(f"      ✅ Generated! Downloading...")
                resp = requests.get(download_url)
                if resp.status_code == 200:
                    with open(out_path, "wb") as f:
                        f.write(resp.content)
                    print(f"      💾 Saved: {out_path}")
                else:
                    print(f"      ❌ Download error: {resp.status_code}")
            else:
                print(f"      ❌ API Error: {result}")
        
        except Exception as e:
            print(f"      ❌ Exception waiting for job: {e}")
            
        # Cleanup temp trim if it exists
        if job.get("temp_trim") and os.path.exists(job["temp_trim"]):
            try: os.remove(job["temp_trim"])
            except: pass

if __name__ == "__main__":
    print("Please use run_batch_kling.py to execute the batch.")
