import os
import glob
import sys

# Add path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

try:
    from services.gemini_service import GeminiService
except ImportError:
    from services.gemini_service import GeminiService

from core.cosplay import create_cosplay_version

CHAR_DIR = os.path.join(ROOT, "output", "characters")

def redo_all_cosplays():
    print("🚀 Starting Batch Redo of Cosplay Images (Asian Style)...")
    
    # Find all original anime images (exclude existing cosplay files)
    all_files = glob.glob(os.path.join(CHAR_DIR, "*.png"))
    anime_files = [f for f in all_files if "_cosplay" not in f and "bulma_asian" not in f]
    
    print(f"found {len(anime_files)} anime characters to convert.")
    
    service = GeminiService()
    
    for i, input_path in enumerate(anime_files):
        filename = os.path.basename(input_path)
        base_name = os.path.splitext(filename)[0]
        cosplay_path = os.path.join(CHAR_DIR, f"{base_name}_cosplay.png")
        
        print(f"\n[{i+1}/{len(anime_files)}] Converting {filename} -> Cosplay...")
        
        # We always overwrite here because the user asked to "redo"
        create_cosplay_version(input_path, cosplay_path, service)

if __name__ == "__main__":
    redo_all_cosplays()
