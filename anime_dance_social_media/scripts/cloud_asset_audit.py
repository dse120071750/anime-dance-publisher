#!/usr/bin/env python3
"""
Cloud Asset Audit - Comprehensive check of local vs cloud assets
"""
import os
import sys
import json
from pathlib import Path
from collections import defaultdict

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.firestore_service import FirestoreService
from services.gcs_service import GCSService

def audit_assets():
    print("=" * 80)
    print("CLOUD ASSET AUDIT REPORT")
    print("=" * 80)
    
    # Initialize services
    fs = FirestoreService()
    gcs = GCSService()
    
    # Paths
    OUTPUT_DIR = ROOT / "output"
    CHARACTERS_DIR = OUTPUT_DIR / "characters"
    DANCES_DIR = OUTPUT_DIR / "dances"
    REMIXES_DIR = OUTPUT_DIR / "remixes"
    
    # 1. LOCAL ASSETS INVENTORY
    print("\n[LOCAL ASSETS INVENTORY]")
    print("-" * 80)
    
    local_chars = list(CHARACTERS_DIR.glob("*.png")) if CHARACTERS_DIR.exists() else []
    local_dances = list(DANCES_DIR.glob("*.mp4")) if DANCES_DIR.exists() else []
    local_remix_dirs = [d for d in REMIXES_DIR.iterdir() if d.is_dir()] if REMIXES_DIR.exists() else []
    
    print(f"Character Images: {len(local_chars)}")
    print(f"Dance Videos: {len(local_dances)}")
    print(f"Remix Directories: {len(local_remix_dirs)}")
    
    # Analyze character pairs
    char_base_names = set()
    for char_file in local_chars:
        name = char_file.stem.replace("_cosplay", "").replace("_anime", "")
        char_base_names.add(name)
    
    print(f"Unique Characters: {len(char_base_names)}")
    
    # 2. CHECK SPECIFIC EXAMPLE: AI HOSHINO
    print("\n[DETAILED CHECK: AI HOSHINO]")
    print("-" * 80)
    
    ai_hoshino_files = {
        "characters": [],
        "dances": [],
        "remixes": [],
        "variants": [],
        "soundtracks": []
    }
    
    for f in local_chars:
        if "ai_hoshino" in f.name.lower():
            ai_hoshino_files["characters"].append(f.name)
    
    for f in local_dances:
        if "ai_hoshino" in f.name.lower():
            ai_hoshino_files["dances"].append(f.name)
    
    # Check remix directory
    ai_hoshino_remix_dir = REMIXES_DIR / "dance_ai_hoshino_1770337530_cosplay_on_AbjwLnB_E_E"
    if ai_hoshino_remix_dir.exists():
        print(f"Remix directory exists: {ai_hoshino_remix_dir.name}")
        
        # Files in root
        for f in ai_hoshino_remix_dir.glob("*.mp4"):
            ai_hoshino_files["remixes"].append(f.name)
        
        # Variants folder
        variants_dir = ai_hoshino_remix_dir / "variants"
        if variants_dir.exists():
            for f in variants_dir.glob("*"):
                ai_hoshino_files["variants"].append(f"variants/{f.name}")
        
        # Result folder (soundtracks)
        result_dir = ai_hoshino_remix_dir / "result"
        if result_dir.exists():
            for f in result_dir.glob("*"):
                if "soundtrack" in f.name.lower() or f.suffix in ['.mp3', '.mp4']:
                    ai_hoshino_files["soundtracks"].append(f"result/{f.name}")
    
    print(f"\nCharacter Assets:")
    for f in sorted(ai_hoshino_files["characters"]):
        print(f"  [OK] {f}")
    
    print(f"\nDance Video:")
    for f in sorted(ai_hoshino_files["dances"]):
        size_mb = (DANCES_DIR / f).stat().st_size / (1024*1024)
        print(f"  [OK] {f} ({size_mb:.1f} MB)")
    
    print(f"\nRemix Files:")
    for f in sorted(ai_hoshino_files["remixes"]):
        print(f"  [OK] {f}")
    
    print(f"\nVariant Outfits:")
    for f in sorted(ai_hoshino_files["variants"]):
        print(f"  [OK] {f}")
    
    print(f"\nSoundtrack Versions:")
    for f in sorted(ai_hoshino_files["soundtracks"]):
        print(f"  [OK] {f}")
    
    # 3. FIRESTORE CHECK
    print("\n[FIRESTORE DATABASE CHECK]")
    print("-" * 80)
    
    try:
        chars_ref = fs.db.collection("characters").stream()
        firestore_chars = []
        firestore_count = 0
        
        for doc in chars_ref:
            data = doc.to_dict()
            firestore_count += 1
            if "hoshino" in data.get("name", "").lower() or "ai_hoshino" in doc.id.lower():
                firestore_chars.append({
                    "id": doc.id,
                    "name": data.get("name"),
                    "anime": data.get("anime"),
                    "assets": data.get("assets", [])
                })
        
        print(f"Total characters in Firestore: {firestore_count}")
        
        if firestore_chars:
            print(f"\nAI Hoshino in Firestore:")
            for char in firestore_chars:
                print(f"  ID: {char['id']}")
                print(f"  Name: {char['name']}")
                print(f"  Anime: {char['anime']}")
                print(f"  Assets: {len(char['assets'])}")
                for i, asset in enumerate(char['assets']):
                    dance = asset.get('dance_video', 'N/A')
                    cosplay = asset.get('cosplay_image', 'N/A')
                    print(f"    Asset {i+1}:")
                    print(f"      Dance: {'[GCS]' if dance.startswith('gs://') else '[LOCAL]' if dance.startswith('C:') else dance[:50]}")
                    print(f"      Image: {'[GCS]' if cosplay.startswith('gs://') else '[LOCAL]' if cosplay.startswith('C:') else cosplay[:50]}")
        else:
            print("\n[WARN] AI Hoshino NOT FOUND in Firestore!")
            
    except Exception as e:
        print(f"[ERROR] querying Firestore: {e}")
    
    # 4. GCS CHECK
    print("\n[GCS BUCKET CHECK]")
    print("-" * 80)
    
    try:
        bucket = gcs.bucket
        blobs = list(bucket.list_blobs(prefix="anime_dance/"))
        
        gcs_chars = [b for b in blobs if "/characters/" in b.name and b.name.endswith('.png')]
        gcs_dances = [b for b in blobs if "/dances/" in b.name and b.name.endswith('.mp4')]
        gcs_remixes = [b for b in blobs if "/remixes/" in b.name and b.name.endswith('.mp4')]
        
        print(f"Characters in GCS: {len(gcs_chars)}")
        print(f"Dances in GCS: {len(gcs_dances)}")
        print(f"Remixes in GCS: {len(gcs_remixes)}")
        
        # Check Ai Hoshino specifically
        ai_hoshino_gcs = {
            "characters": [],
            "dances": [],
            "remixes": []
        }
        
        for b in blobs:
            if "ai_hoshino" in b.name.lower():
                if "/characters/" in b.name:
                    ai_hoshino_gcs["characters"].append(b.name)
                elif "/dances/" in b.name:
                    ai_hoshino_gcs["dances"].append(b.name)
                elif "/remixes/" in b.name:
                    ai_hoshino_gcs["remixes"].append(b.name)
        
        if ai_hoshino_gcs["characters"] or ai_hoshino_gcs["dances"] or ai_hoshino_gcs["remixes"]:
            print(f"\nAI Hoshino in GCS:")
            print(f"  Characters: {len(ai_hoshino_gcs['characters'])}")
            for name in ai_hoshino_gcs['characters'][:5]:
                print(f"    [OK] {name.split('/')[-1]}")
            print(f"  Dances: {len(ai_hoshino_gcs['dances'])}")
            for name in ai_hoshino_gcs['dances'][:5]:
                print(f"    [OK] {name.split('/')[-1]}")
            print(f"  Remixes: {len(ai_hoshino_gcs['remixes'])}")
            for name in ai_hoshino_gcs['remixes'][:10]:
                short_name = name.split('/')[-1]
                if len(short_name) > 60:
                    short_name = short_name[:57] + "..."
                print(f"    ✅ {short_name}")
        else:
            print("\n[WARN] AI Hoshino NOT FOUND in GCS!")
            
    except Exception as e:
        print(f"[ERROR] querying GCS: {e}")
    
    # 5. MISMATCH SUMMARY
    print("\n[MISMATCH SUMMARY]")
    print("-" * 80)
    
    print(f"Local characters: {len(local_chars)}, GCS characters: {len(gcs_chars)}")
    print(f"Local dances: {len(local_dances)}, GCS dances: {len(gcs_dances)}")
    
    if len(local_chars) > len(gcs_chars):
        print(f"  [MISSING] {len(local_chars) - len(gcs_chars)} character images need upload")
    if len(local_dances) > len(gcs_dances):
        print(f"  [MISSING] {len(local_dances) - len(gcs_dances)} dance videos need upload")
    
    # Check for local paths in Firestore
    print("\n[Checking Firestore for local paths...]")
    try:
        chars_ref = fs.db.collection("characters").stream()
        local_path_count = 0
        for doc in chars_ref:
            data = doc.to_dict()
            for asset in data.get("assets", []):
                dance = asset.get("dance_video", "")
                image = asset.get("cosplay_image", "")
                if dance.startswith("C:") or image.startswith("C:"):
                    local_path_count += 1
                    print(f"  [LOCAL PATH] found in {doc.id}")
        
        if local_path_count == 0:
            print("  [OK] All paths are GCS URIs")
        else:
            print(f"  [WARN] {local_path_count} assets still have local paths")
            
    except Exception as e:
        print(f"[ERROR] {e}")
    
    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    audit_assets()
