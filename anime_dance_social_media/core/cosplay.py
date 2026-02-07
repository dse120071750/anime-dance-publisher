import os
import sys

# Add path for imports
# Add path for imports
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

try:
    from services.gemini_service import GeminiService
except ImportError:
    from services.gemini_service import GeminiService

def create_cosplay_version(input_path, output_path, service=None, character_name=None, anime_name=None):
    """
    Converts an anime image into a photorealistic 1990s cosplay photo.
    """
    if not os.path.exists(input_path):
        print(f"❌ Input image not found: {input_path}")
        return False

    print(f"📸 Creating Cosplay Version: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")

    if service is None:
        service = GeminiService()

    # Step 1: Analyze the Anime Image to get details
    print("      🧠 Analyzing image for scene and outfit details...")
    
    context_info = ""
    if character_name and anime_name:
        context_info = f"This is {character_name} from {anime_name}."
    elif character_name:
        context_info = f"This is {character_name}."
        
    analysis_prompt = (
        f"Analyze this anime image in detail. {context_info} "
        "1. Describe the OUTFIT (colors, cuts, accessories) in detail. "
        "2. Describe the HAIR (style, color). "
        "3. Suggest a SIGNATURE REAL-WORLD LOCATION that fits this anime's aesthetic and this character. "
        "4. VISUAL ANALYSIS: Pose and composition."
    )
    
    description = service.generate_text(prompt=analysis_prompt, context_files=[input_path])
    
    if not description:
        description = "A female anime character in a costume." # Fallback
        print("      ⚠️ Analysis failed, using fallback.")
    else:
        print(f"      ✅ Analysis Complete: {description[:100]}...")

    # Step 2: Construct the Generation Prompt
    # We combine the specific details with the style constraints
    
    subject_prompt = "A GORGEOUS, STUNNINGLY BEAUTIFUL Real Asian Female Model."
    if character_name:
        subject_prompt = f"A GORGEOUS, STUNNINGLY BEAUTIFUL Real Asian Female Model cosplaying as {character_name}."

    instruction = (
        f"Using this analysis: '{description}', "
        "transform this image into a High-Budget CINEMATIC COSPLAY PHOTOGRAPH. "
        f"SUBJECT: {subject_prompt} "
        "She must have a beautiful face, refined features, and professional makeup. "
        "OUTFIT: A High-End faithful Cosplay Costume. Do NOT modernize it. "
        "Keep the exact anime design, but use REALISTIC EXPENSIVE MATERIALS (real leather, silk, metal armor, velvet). "
        "It must look like a $5000 movie costume, not a cheap halloween outfit. "
        "BACKGROUND: Place her in the SIGNATURE LOCATION mentioned in the analysis. "
        "Render it as a real, photorealistic place with depth and atmosphere. "
        "LIGHTING: Professional Cinematic Outdoor Lighting. Golden hour sun, soft fill lighting, rim light. "
        "STYLE: 8k Masterpiece, Shot on Sony A7R IV, 85mm portrait lens. "
        "NO ANIME FACES. NO CARTOON TEXTURES. PURE PHOTOREALISM."
    )

    if service is None:
        service = GeminiService()
    
    # Use edit_image for structure preservation
    success = service.edit_image(
        input_path=input_path,
        output_path=output_path,
        prompt=instruction
    )
    
    if success:
        print(f"   🎉 Cosplay saved: {output_path}")
        return True
    else:
        print("   ❌ Cosplay generation failed.")
        return False

if __name__ == "__main__":
    # Test block
    import sys
    if len(sys.argv) > 2:
        c_name = sys.argv[3] if len(sys.argv) > 3 else None
        a_name = sys.argv[4] if len(sys.argv) > 4 else None
        create_cosplay_version(sys.argv[1], sys.argv[2], character_name=c_name, anime_name=a_name)
    else:
        print("Usage: python cosplay.py <input_image> <output_image> [character_name] [anime_name]")
