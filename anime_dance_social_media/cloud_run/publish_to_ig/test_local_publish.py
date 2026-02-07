import sys
from pathlib import Path
import os
import json

# Add current dir to path
sys.path.append(str(Path(__file__).parent))

from main import app

def test_publish():
    print("🚀 Starting Test Publish to Instagram via Cloud Run logic...")
    
    # Use Flask's test client
    with app.test_client() as client:
        payload = {
            "character_id": "bulma_1770089530",
            "asset_title": "primary",
            "version": "remix_kpop_watermarked",
            "caption": "Bulma's K-pop Dance Remix! 💙 #Bulma #DragonBall #AnimeDance #Kpop"
        }
        
        print(f"   📤 Sending request for Bulma ({payload['version']})...")
        response = client.post('/publish', json=payload)
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {json.dumps(response.get_json(), indent=2)}")

if __name__ == "__main__":
    test_publish()
