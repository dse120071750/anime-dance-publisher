import os
import subprocess

# Config
ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT, "temp_process_kling")
CHANNEL_URL = "https://www.youtube.com/@_purple_lee/shorts"

def download_channel():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print(f"🚀 Downloading Shorts from {CHANNEL_URL}...")
    print(f"📂 Output Directory: {OUTPUT_DIR}")

    # yt-dlp command
    # -i: Ignore errors
    # --yes-playlist: Download all
    # -o: Output template
    # -S: Format selection (prefer 1080 vertical?) usually shorts are vertical.
    # --recode-video mp4: Ensure MP4 container
    # --postprocessor-args: Force H.264/AAC for compatibility with Kling
    
    cmd = [
        "yt-dlp",
        "--ignore-errors",
        "--yes-playlist",
        "-o", os.path.join(OUTPUT_DIR, "%(id)s.%(ext)s"),
        "-S", "res:1080,ext:mp4:m4a",
        "--recode-video", "mp4", 
        "--postprocessor-args", "VideoConvertor:-c:v libx264 -c:a aac",
        CHANNEL_URL
    ]

    try:
        subprocess.run(cmd, check=True)
        print("✅ Download complete.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Download failed: {e}")

if __name__ == "__main__":
    download_channel()
