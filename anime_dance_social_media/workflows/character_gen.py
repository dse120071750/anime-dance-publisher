import os
import sys
import json
import time
import re
from datetime import datetime

# Add path
# Add path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

try:
    from services.gemini_service import GeminiService
except ImportError:
    from services.gemini_service import GeminiService

from core.cosplay import create_cosplay_version

# Configuration
CHAR_DIR = os.path.join(ROOT, "output", "characters")
DB_FILE = os.path.join(CHAR_DIR, "character_db.json")

# Target Characters (Name, Anime)
TARGETS = [
    # 1980s
    ("Lum Invader", "Urusei Yatsura"),
    ("Nausicaä", "Nausicaä of the Valley of the Wind"),
    ("Bulma", "Dragon Ball"),
    # 1990s
    ("Usagi Tsukino (Sailor Moon)", "Sailor Moon"),
    ("Motoko Kusanagi", "Ghost in the Shell"),
    ("Faye Valentine", "Cowboy Bebop"),
    ("Rei Ayanami", "Neon Genesis Evangelion"),
    ("Sakura Kinomoto", "Cardcaptor Sakura"),
    # 2000s
    ("Kagome Higurashi", "Inuyasha"),
    ("Saber", "Fate/stay night"),
    ("Haruhi Suzumiya", "The Melancholy of Haruhi Suzumiya"),
    ("Yoko Littner", "Tengen Toppa Gurren Lagann"),
    ("C.C.", "Code Geass"),
    # 2010s
    ("Makise Kurisu", "Steins;Gate"),
    ("Mikoto Misaka", "A Certain Scientific Railgun"),
    ("Zero Two", "Darling in the Franxx"),
    ("Violet Evergarden", "Violet Evergarden"),
    ("Mai Sakurajima", "Rascal Does Not Dream of Bunny Girl Senpai"),
    # 2020s
    ("Marin Kitagawa", "My Dress-Up Darling"),
    ("Frieren", "Frieren: Beyond Journey's End"),
    ("Yor Forger", "Spy x Family")
]

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def generate_creative_prompt(service, name, anime):
    print(f"🧠 Brainstorming concept for {name}...")
    
    instruction = (
        f"You are a creative Anime Art Director. Your task is to design a unique, high-quality image concept for '{name}' from the anime '{anime}'.\n"
        "SUBJECT DESCRIPTION: The character must be depicted as a STUNNINGLY BEAUTIFUL 18-year-old Asian female with a 'cute', youthful, and elegant aesthetic.\n"
        "STYLE: Makoto Shinkai (highly detailed, atmospheric lighting, vibrant colors, 'perfect scenario' vibe, masterpiece).\n"
        "CONSTRAINT 1: Full Body Shot. The character MUST be standing firmly on the ground. FEET/SHOES MUST BE FULLY VISIBLE. No floating (unless flying character, but prefer grounded for dance).\n"
        "CONSTRAINT 2: Aspect Ratio 9:16 (Vertical).\n"
        "TASK:\n"
        "1. Invent a unique, elegant, or stylish OUTFIT for them (modern, traditional, or haute couture, fitting their personality but fresh).\n"
        "2. Design a scenic BACKGROUND (outdoors, cityscape, nature, or fantasy) that fits the Shinkai aesthetic.\n"
        "3. Provide the accurate Japanese name of the character and the official Japanese title of the anime.\n"
        "4. Write a strict Image Generation PROMPT incorporating these details.\n\n"
        "Response must be VALID JSON with keys: 'outfit', 'background', 'name_jp', 'anime_jp', 'prompt'."
    )
    
    try:
        # Use generate_text
        raw_response = service.generate_text(instruction)
        if not raw_response: return None
        
        # cleanup json
        json_str = raw_response.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        return data
    except Exception as e:
        print(f"   ⚠️ Failed to generate concept: {e}")
        return None

def generate_new_targets_list(service, existing_names, count):
    print(f"🧠 Brainstorming {count} NEW popular anime characters...")
    prompt = (
        f"List {count} popular female anime characters that are NOT in this list: {list(existing_names)}.\n"
        "Focus on visually distinct, popular characters from 1990s-2020s.\n"
        "Return ONLY a JSON list of objects: [{\"name\": \"Character Name\", \"anime\": \"Anime Title\"}, ...]"
    )
    try:
        resp = service.generate_text(prompt)
        if resp:
            text = resp.replace("```json", "").replace("```", "").strip()
            # Find list bracket if needed
            import re
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return [(item["name"], item["anime"]) for item in data]
    except Exception as e:
        print(f"   ⚠️ Failed to generate list: {e}")
    return []

def generate_characters(count=0, target_list=None):
    if not os.path.exists(CHAR_DIR):
        os.makedirs(CHAR_DIR)
        
    from utils.db_utils import load_db, register_character, upsert_asset
    db = load_db()
    service = GeminiService()
    
    existing_names = {entry.get('name') for entry in db}
    
    targets_to_process = []
    
    if target_list:
        targets_to_process = target_list
    elif count > 0:
        targets_to_process = generate_new_targets_list(service, existing_names, count)
        if not targets_to_process:
            print("⚠️ Could not generate new targets. Aborting.")
            return []
    else:
        # Legacy Mode
        targets_to_process = TARGETS
        
    generated_ids = []
    
    for name, anime in targets_to_process:
        if name in existing_names:
            print(f"   ⏭️ Skipping {name} (Already in DB)")
            continue

        print(f"\n✨ Processing: {name} ({anime})")
        
        # 1. Generate Concept
        concept = generate_creative_prompt(service, name, anime)
        if not concept:
            continue
            
        # 2. Generate Image (Anime)
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        timestamp = int(time.time())
        char_id = f"{clean_name}_{timestamp}"
        filename = f"{char_id}.png"
        output_path = os.path.join(CHAR_DIR, filename)
        
        prompt = concept.get('prompt', '')
        prompt += " (Makoto Shinkai style, masterpiece, 8k, highly detailed, full body, feet visible, grounded, 9:16 aspect ratio)"
        
        if service.generate_image(prompt=prompt, output_path=output_path):
            print(f"   🎉 Generated Anime: {output_path}")
            
            # 3. Generate Cosplay Version
            cosplay_filename = f"{char_id}_cosplay.png"
            cosplay_path = os.path.join(CHAR_DIR, cosplay_filename)
            cosplay_success = False
            try:
                # Pass Metadata for accurate cosplay
                cosplay_success = create_cosplay_version(
                    output_path, 
                    cosplay_path, 
                    service, 
                    character_name=name, 
                    anime_name=anime
                )
            except Exception as e:
                print(f"   ⚠️ Cosplay generation skipped/failed: {e}")
            
            # 4. Update DB via Utilities
            register_character(
                char_id=char_id,
                name=name,
                anime=anime,
                metadata={
                    "name_jp": concept.get('name_jp'),
                    "anime_jp": concept.get('anime_jp')
                },
                prompts={
                    "full_prompt": prompt,
                    "outfit_desc": concept.get('outfit'),
                    "background_desc": concept.get('background')
                }
            )
            
            upsert_asset(char_id, {
                "title": "primary",
                "anime_image": output_path,
                "cosplay_image": cosplay_path if cosplay_success else None
            })
            
            generated_ids.append(char_id)
            # Add to local set to avoid dupes in same run
            existing_names.add(name)
            
        else:
            print("   ❌ Image generation failed.")
            
    return generated_ids

if __name__ == "__main__":
    generate_characters()
