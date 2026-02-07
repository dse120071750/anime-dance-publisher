import os
import time
import sys
import json
import logging
import concurrent.futures
from typing import List, Optional, Union

# Try to use standard google.genai
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: `google-genai` library not found. Please install it.")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class GeminiService:
    def __init__(self):
        self.api_keys = self._load_api_keys()
        if not self.api_keys:
            print("⚠️ Warning: No Google API Keys found. GeminiService may fail.")
        
        self.key_index = 0
        
        # Default Models as requested
        self.text_model = "gemini-3-pro-preview"
        self.image_model = "gemini-3-pro-image-preview"

    def _load_api_keys(self) -> List[str]:
        """Loads rotation keys from env or file."""
        # Check env var first
        keys_str = os.environ.get("GOOGLE_ROTATION_KEYS", "")
        if keys_str:
            return [k.strip() for k in keys_str.split(",") if k.strip()]
            
        # Check .env file fallback
        env_path = os.path.join(ROOT, "..", ".env") # Depending on structure
        if not os.path.exists(env_path):
            env_path = os.path.join(os.path.dirname(ROOT), ".env")
            
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        if line.startswith("GOOGLE_ROTATION_KEYS="):
                            val = line.split("=", 1)[1].strip().strip('"')
                            return [k.strip() for k in val.split(",") if k.strip()]
            except: pass
            
        return []

    def get_client(self, api_key: Optional[str] = None):
        key = api_key or self.api_keys[self.key_index]
        return genai.Client(api_key=key)

    def _rotate_key(self):
        if not self.api_keys: return
        self.key_index = (self.key_index + 1) % len(self.api_keys)
        print(f"      🔄 Rotating to Gemini Key Index: {self.key_index} (Ends: ...{self.api_keys[self.key_index][-4:]})")

    def generate_text(self, prompt: str, context_files: List[str] = [], model: str = None) -> Optional[str]:
        """
        Generates text (or analysis) using rotation keys.
        Supports uploading files (images/videos) as context.
        """
        target_model = model or self.text_model
        
        # Prepare contents
        contents = [prompt]
        
        # Note: For large files (video), we might need to use the File API separately if the client doesn't auto-handle it well with local paths in this SDK version.
        # But separate File API calls are safer for reuse.
        
        # Simple implementation: Let's assume context_files are paths.
        # For brevity/robustness with rotation, we might need to upload per key or share?
        # Files are usually project-scoped if using Cloud, but with API keys they are often bound to the key/project.
        # SAFE APPROACH: Re-upload or use client helper if valid.
        
        # Since we rotate keys, we must re-upload content if we switch keys, essentially.
        
        for attempt in range(len(self.api_keys) * 2):
            try:
                client = self.get_client()
                
                # Check file inputs
                # If it's a simple image, send bytes. If video, use Upload API.
                final_contents = []
                uploaded_files = []
                
                # Helper to handle inputs
                for path in context_files:
                    if not os.path.exists(path): continue
                    
                    mime = "application/octet-stream"
                    if path.endswith(".mp4"): mime = "video/mp4"
                    elif path.endswith(".png"): mime = "image/png"
                    elif path.endswith(".jpg"): mime = "image/jpeg"
                    elif path.endswith(".mp3"): mime = "audio/mp3"
                    
                    # For Video/Audio, safer to use files.upload
                    if "video" in mime or "audio" in mime:
                        print(f"      📤 Uploading {os.path.basename(path)} to Gemini...")
                        f_obj = client.files.upload(file=path)
                        
                        # Wait for processing
                        while f_obj.state.name == "PROCESSING":
                            time.sleep(2)
                            f_obj = client.files.get(name=f_obj.name)
                        
                        if f_obj.state.name == "FAILED":
                            raise Exception("File processing failed")
                            
                        uploaded_files.append(f_obj)
                        final_contents.append(f_obj)
                    else:
                        # Small images -> inline bytes
                        with open(path, "rb") as f:
                            b = f.read()
                        final_contents.append(types.Part.from_bytes(data=b, mime_type=mime))
                
                final_contents.append(prompt)
                
                print(f"      🧠 Gemini Text Gen ({target_model})...")
                response = client.models.generate_content(
                    model=target_model,
                    contents=final_contents
                )
                
                if response.text:
                    return response.text.strip()
                    
            except Exception as e:
                print(f"      ⚠️ Gemini Error (Key {self.key_index}): {e}")
                if "429" in str(e) or "403" in str(e):
                    self._rotate_key()
                    continue
                else:
                    # Logic: If it's a file upload error, maybe retry same key?
                    # If it's a model error, maybe break?
                    time.sleep(1)
                    self._rotate_key()
        
        return None

    def generate_image(self, prompt: str, output_path: str, model: str = None) -> bool:
        """
        Generates an image using gemini-3-pro-image-preview.
        """
        target_model = model or self.image_model
        
        for attempt in range(len(self.api_keys) * 2):
            try:
                client = self.get_client()
                print(f"      🎨 Gemini Image Gen ({target_model})...")
                
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio="9:16") # Defaulting to vertical for this project
                    )
                )
                
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            with open(output_path, "wb") as f:
                                f.write(part.inline_data.data)
                            print(f"      ✅ Image Saved: {output_path}")
                            return True
                            
                print("      ⚠️ No image data in response.")
                
            except Exception as e:
                print(f"      ⚠️ Gemini Image Error (Key {self.key_index}): {e}")
                self._rotate_key()
                time.sleep(1)
                
        return False

    def edit_image(self, input_path: str, output_path: str, prompt: str) -> bool:
        """
        Edits (or regenerates based on) an image using gemini-3-pro-image-preview.
        """
        if not os.path.exists(input_path):
            print(f"      ❌ Input file not found: {input_path}")
            return False
            
        target_model = self.image_model
        
        # Read image
        try:
            with open(input_path, "rb") as f:
                img_bytes = f.read()
            mime = "image/png" if input_path.lower().endswith(".png") else "image/jpeg"
        except Exception as e:
            print(f"      ⚠️ Read Error: {e}")
            return False

        contents = [types.Part.from_bytes(data=img_bytes, mime_type=mime), prompt]
        
        for attempt in range(len(self.api_keys) * 2):
            try:
                client = self.get_client()
                print(f"      🎨 Gemini Image Edit ({target_model})...")
                
                response = client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio="9:16")
                    )
                )
                
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            with open(output_path, "wb") as f:
                                f.write(part.inline_data.data)
                            print(f"      ✅ Edit Saved: {output_path}")
                            return True
                            
                print(f"      ⚠️ No inline data in edit response. (Attempt {attempt})")
                try:
                    print(f"      DEBUG Response Parts: {response.candidates[0].content.parts}")
                    if response.text:
                         print(f"      DEBUG Response Text: {response.text}")
                except:
                    print(f"      DEBUG Full Response: {response}")
                
            except Exception as e:
                print(f"      ⚠️ Gemini Edit Error (Key {self.key_index}): {e}")
                
                if "429" in str(e) or "403" in str(e):
                    self._rotate_key()
                time.sleep(1)
                
        return False
