import os
import sys

# Add path
# Add path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)

try:
    from services.gemini_service import GeminiService
except ImportError:
    from services.gemini_service import GeminiService

# Paths
CHAR_DIR = os.path.join(ROOT, "characters")
TARGET_IMAGE = os.path.join(CHAR_DIR, "bulma_1770088477.png")
OUTPUT_IMAGE = os.path.join(CHAR_DIR, "bulma_asian_cosplay_test.png")

def main():
    if not os.path.exists(TARGET_IMAGE):
        print(f"❌ Target image not found: {TARGET_IMAGE}")
        return

    print(f"📸 Converting {os.path.basename(TARGET_IMAGE)} to Real-Life Asian Cosplay (Edit Mode)...")

    instruction = (
        "Turn this anime image into a PHOTOREALISTIC 1990s COSPLAY PHOTO. "
        "Subject: A real ASIAN female cosplayer (Japanese/Korean facial features). "
        "Maintain the EXACT pose, composition, background elements, and character outfit details. "
        "Change ONLY the rendering style: replace anime textures with realistic skin, real fabric (cloth, denim, latex), "
        "real hair, and real metal. "
        "The Background must be transformed into a REAL realistic location (photorealistic textures, depth of field), matching the anime scene. "
        "Aesthetic: 1990s Fujifilm disposable camera style, film grain, flash photography, slightly imperfect 'candid' look. "
        "Do NOT change the face shape to be anime-like; it must look like a real Asian person."
    )

    service = GeminiService()
    
    # Use edit_image to preserve structure but change style/identity slightly (Asian features)
    success = service.edit_image(
        input_path=TARGET_IMAGE,
        output_path=OUTPUT_IMAGE,
        prompt=instruction
    )
    
    if success:
        print(f"   🎉 Cosplay saved: {OUTPUT_IMAGE}")
    else:
        print("   ❌ Cosplay generation failed.")

if __name__ == "__main__":
    main()
