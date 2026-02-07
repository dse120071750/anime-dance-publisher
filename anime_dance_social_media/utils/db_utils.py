import os
import json
import shutil
from datetime import datetime

# Root Constants
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAR_DIR = os.path.join(ROOT, "output", "characters")
DB_FILE = os.path.join(CHAR_DIR, "character_db.json")
MUSIC_DB_FILE = os.path.join(ROOT, "utils", "music_styles_db.json")

def load_db():
    """Load the character database."""
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading DB: {e}")
        return []

def save_db(db):
    """Save the character database safely."""
    if not os.path.exists(CHAR_DIR):
        os.makedirs(CHAR_DIR)
    
    # Backup before save
    if os.path.exists(DB_FILE):
        shutil.copy2(DB_FILE, DB_FILE + ".bak")
        
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error saving DB: {e}")

def get_entry(char_id):
    """Fetch an entry by its ID or part of its ID."""
    db = load_db()
    for entry in db:
        if char_id in entry.get("id", ""):
            return entry
    return None

def load_music_styles():
    """Load the music styles database."""
    if not os.path.exists(MUSIC_DB_FILE):
        return []
    try:
        with open(MUSIC_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading Music DB: {e}")
        return []

def get_music_style(style_id):
    """Fetch a music style by its ID."""
    db = load_music_styles()
    for entry in db:
        if style_id == entry.get("id"):
            return entry
    return None

def update_entry(char_id, updates):
    """
    Update a specific entry in the DB.
    'updates' should be a dict of key-values.
    Supports nested updates if keys are like 'assets.cosplay_image'
    """
    db = load_db()
    found = False
    for entry in db:
        if char_id == entry.get("id") or (char_id in entry.get("id", "") and len(char_id) > 10):
            found = True
            for key, value in updates.items():
                if "." in key:
                    parts = key.split(".")
                    curr = entry
                    for p in parts[:-1]:
                        if p not in curr: curr[p] = {}
                        curr = curr[p]
                    curr[parts[-1]] = value
                else:
                    entry[key] = value
            break
    
    if found:
        save_db(db)
        return True
    return False

def upsert_asset(char_id, asset_data):
    """
    Upserts an asset entry into the 'assets' list.
    asset_data must have a 'title' field (e.g., 'primary', 'jennie_swimsuit').
    """
    db = load_db()
    
    # Fuzzy Search for Entry
    target_entry = None
    for entry in db:
        if char_id == entry.get("id") or (char_id in entry.get("id", "") and len(char_id) > 10):
            target_entry = entry
            break
            
    if not target_entry:
        print(f"⚠️ upsert_asset: Entry not found for {char_id}. Creating new entry...")
        target_entry = {"id": char_id, "name": char_id, "anime": "Unknown", "assets": []}
        db.append(target_entry)
        
    # Ensure assets is a list
    if "assets" not in target_entry:
        target_entry["assets"] = []
    elif isinstance(target_entry["assets"], dict):
        # Migration on the fly
        old_assets = target_entry["assets"]
        # Basic migration of old flat structure to 'primary'
        new_asset = {"title": "primary"}
        new_asset.update(old_assets)
        target_entry["assets"] = [new_asset]
        
    assets_list = target_entry["assets"]
    title = asset_data.get("title", "primary")
    
    # Find existing asset by title
    found_asset = None
    for asset in assets_list:
        if asset.get("title") == title:
            found_asset = asset
            break
            
    if found_asset:
        found_asset.update(asset_data)
    else:
        # If title missing in data, ensure it's set
        if "title" not in asset_data: asset_data["title"] = title
        assets_list.append(asset_data)
        
    save_db(db)
    return True

def register_character(char_id, name, anime, metadata=None, assets=None, prompts=None):
    """Create or update a full character registry."""
    db = load_db()
    
    entry = next((e for e in db if e.get("id") == char_id), None)
    if not entry:
        entry = {"id": char_id, "name": name, "anime": anime, "assets": []}
        db.append(entry)
    
    if metadata: 
        if "metadata" not in entry: entry["metadata"] = {}
        entry["metadata"].update(metadata)
    
    # Handle Assets
    if assets:
        # if assets passed as dict but seems to be a single asset object (has keys like anime_image etc)
        # we treat it as 'primary' or merge into primary
        if isinstance(assets, dict):
            # If it's the old flat dict style, wrap it
            upsert_asset_logic = True
             # Check if we should use the new helper or doing it manually
             # Let's just update the in-memory entry and rely on save_db later? 
             # No, easier to just use the logic we just wrote, but we are inside a logic block.
             # Let's just structure it correctly here.
             
            if "assets" not in entry: entry["assets"] = []
            elif isinstance(entry["assets"], dict):
                 # Migrate
                 entry["assets"] = [{"title": "primary", **entry["assets"]}]
            
            # Now merge 'assets' arg into 'primary'
            # Find primary
            prim = next((a for a in entry["assets"] if a.get("title") == "primary"), None)
            if not prim:
                prim = {"title": "primary"}
                entry["assets"].append(prim)
            prim.update(assets)

        elif isinstance(assets, list):
            entry["assets"] = assets
        
    if prompts:
        if "prompts" not in entry: entry["prompts"] = {}
        entry["prompts"].update(prompts)
        
    entry["last_updated"] = datetime.now().isoformat()
    save_db(db)
    return entry

def migrate_db():
    """Migrate the old flat DB format to the new structured format."""
    db = load_db()
    updated = False
    
    for entry in db:
        changed = False
        # 1. Nest flat assets if they exist at top level (Oldest migration)
        if "file_path" in entry:
            # This is the VERY old flat format
            assets = {
                "anime_image": entry.get("file_path"),
                "cosplay_image": entry.get("cosplay_path")
            }
            # ... (rest of old migration logic omitted for brevity as we are past this)
            
        # 2. Convert 'assets' Dict to List (Current migration)
        if "assets" in entry and isinstance(entry["assets"], dict):
            print(f"📦 Migrating assets dict to list for: {entry.get('name')}")
            old_assets = entry["assets"]
            
            # The keys might be mixed (some primary, some variants flattened)
            # We need to disentangle them if possible, or just dump them all in primary for now
            # User wants specificity.
            
            primary_asset = {"title": "primary"}
            
            # Extract specific keys for primary
            for k in ["anime_image", "cosplay_image", "motion_ref_video", "primary_dance_video", "remix_folder"]:
                if k in old_assets:
                    primary_asset[k] = old_assets[k]
                    
            # Check for flattened variants like "jennie_swimsuit_image"
            variants = {}
            for k, v in old_assets.items():
                if "_image" in k and k not in ["anime_image", "cosplay_image"]:
                    # e.g. jennie_swimsuit_image
                    variant_name = k.replace("_image", "")
                    if variant_name not in variants: variants[variant_name] = {"title": variant_name}
                    variants[variant_name]["cosplay_image"] = v
                elif "_dance" in k and "primary" not in k:
                    # e.g. jennie_swimsuit_dance
                    variant_name = k.replace("_dance", "")
                    if variant_name not in variants: variants[variant_name] = {"title": variant_name}
                    variants[variant_name]["dance_video"] = v

            # Construct new list
            new_list = [primary_asset]
            for v in variants.values():
                # Copy motion ref from primary if missing? User asked for it.
                if "motion_ref_video" in primary_asset:
                    v["motion_ref_video"] = primary_asset["motion_ref_video"]
                new_list.append(v)
                
            entry["assets"] = new_list
            changed = True
            
        if changed:
            updated = True
        
    if updated:
        print("✅ DB Schema Migration Complete (Assets -> List).")
        save_db(db)

if __name__ == "__main__":
    migrate_db()
