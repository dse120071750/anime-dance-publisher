import os
import time
import json
import requests
from typing import List, Dict, Optional

class MinimaxService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.base_url = "https://api.minimax.io/v1/music_generation"
        
        if not self.api_key:
            print("⚠️ Warning: MINIMAX_API_KEY not found.")

    def _load_api_key(self) -> Optional[str]:
        # 1. Check Env Var
        if os.environ.get("MINIMAX_API_KEY"):
            return os.environ.get("MINIMAX_API_KEY")
            
        # 2. Check .env file
        # Handle cases where this script is deep in subdirs
        # We look for .env in current dir, parent, or project root
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Assuming services/ is one level deep, so root is parent
        root_dir = os.path.dirname(current_dir)
        
        candidates = [
            os.path.join(current_dir, ".env"),
            os.path.join(root_dir, ".env"),
            os.path.join(os.path.dirname(root_dir), ".env")
        ]
        
        for env_path in candidates:
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip().startswith("MINIMAX_API_KEY="):
                                # Extract value
                                return line.split("=", 1)[1].strip().strip('"').strip("'")
                except Exception:
                    pass
        return None

    def generate_music(self, prompt: str, lyrics: str, output_path: str, model: str = "music-2.5") -> Optional[str]:
        """
        Generates music via Minimax API with retry logic.
        """
        print(f"      🎵 Minimax Gen ({model})...")
        print(f"         Prompt: {prompt[:50]}...")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        if not lyrics or not lyrics.strip():
            lyrics = "[Instrumental]"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "lyrics": lyrics,
            "audio_setting": {
                "sample_rate": 44100,
                "bitrate": 256000,
                "format": "mp3"
            },
            "output_format": "url"
        }
        
        # Retry Loop
        for attempt in range(3):
            try:
                print(f"         ⏳ Requesting (Attempt {attempt+1}/3)...")
                response = requests.post(self.base_url, headers=headers, json=payload, timeout=300)
                res = response.json()
                
                music_url = None
                if "data" in res and res["data"] and "audio" in res["data"]:
                    music_url = res["data"]["audio"]
                elif "audio_file" in res:
                    music_url = res["audio_file"]
                elif "base_resp" in res and res["base_resp"]["status_code"] != 0:
                     print(f"         ⚠️ API Error: {res['base_resp']['status_msg']}")
                
                if music_url:
                    return self._download_file(music_url, output_path)
                else:
                    print(f"         ⚠️ No audio url found in response: {res}")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"         ❌ Minimax Error (Attempt {attempt+1}): {e}")
                time.sleep(5)
                
        return None

    def _download_file(self, url: str, output_path: str) -> Optional[str]:
        print("         ⬇️ Downloading Audio...")
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=120)
                with open(output_path, "wb") as f:
                    f.write(r.content)
                print(f"         ✅ Saved: {output_path}")
                return output_path
            except Exception as e:
                print(f"         ⚠️ Download failed ({e}), retrying...")
                time.sleep(2)
        return None
