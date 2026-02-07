import json
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(ROOT, "characters", "character_db.json")

def clean_database():
    print(f"🧹 Cleaning database: {DB_FILE}")
    
    if not os.path.exists(DB_FILE):
        print("❌ Database not found.")
        return

    with open(DB_FILE, 'r') as f:
        data = json.load(f)

    to_keep = []
    removed_count = 0
    
    # Animes to remove
    BANNED_ANIMES = ["Digimon", "Pokemon"]

    for entry in data:
        anime = entry.get("anime", "")
        if anime in BANNED_ANIMES:
            print(f"   ❌ Removing: {entry['name']} ({anime})")
            
            # Delete Files
            file_path = entry.get("file_path")
            cosplay_path = entry.get("cosplay_path")
            
            # 1. Main Anime Image
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"      🗑️ Deleted: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"      ⚠️ Error deleting {file_path}: {e}")
            
            # 2. Cosplay Image (explicit link)
            if cosplay_path and os.path.exists(cosplay_path):
                try:
                    os.remove(cosplay_path)
                    print(f"      🗑️ Deleted: {os.path.basename(cosplay_path)}")
                except Exception as e:
                    print(f"      ⚠️ Error deleting {cosplay_path}: {e}")

            # 3. Check for implicit cosplay file if not linked
            # (e.g. if file_path is 'name.png', check for 'name_cosplay.png')
            if file_path:
                base_name = os.path.splitext(file_path)[0]
                implicit_cosplay = f"{base_name}_cosplay.png"
                if os.path.exists(implicit_cosplay):
                    try:
                        os.remove(implicit_cosplay)
                        print(f"      🗑️ Deleted (Implicit): {os.path.basename(implicit_cosplay)}")
                    except Exception as e:
                        print(f"      ⚠️ Error deleting {implicit_cosplay}: {e}")

            removed_count += 1
        else:
            to_keep.append(entry)

    # Save Update DB
    with open(DB_FILE, 'w') as f:
        json.dump(to_keep, f, indent=2)

    print(f"\n✅ Clean up complete. Removed {removed_count} characters. Remaining: {len(to_keep)}")

if __name__ == "__main__":
    clean_database()
