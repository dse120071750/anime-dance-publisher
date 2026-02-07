
import sys
import os

# Set root
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT)

print("🚀 Verifying Imports...")

try:
    print("   ...Services")
    from services.gemini_service import GeminiService
    from services.minimax_service import MinimaxService
    print("      ✅ Services OK")

    print("   ...Core")
    from core.animation import submit_kling_job
    from core.cosplay import create_cosplay_version
    print("      ✅ Core OK")

    print("   ...Workflows")
    from workflows.main_pipeline import run_remix_pipeline
    from workflows.character_gen import generate_creative_prompt
    from workflows.audio_pipeline import run_advanced_audio_scoring_pipeline
    from workflows.watermark_job import add_watermark_to_video
    print("      ✅ Workflows OK")

    print("   ...Utils")
    from utils.batch_utils import redo_all_cosplays
    print("      ✅ Utils OK")

    print("\n🎉 ALL IMPORTS VERIFIED SUCCESSFULLY!")

except Exception as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    sys.exit(1)
