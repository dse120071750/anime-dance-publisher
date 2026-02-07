import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Import services
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from services.gcs_service import GCSService
from services.firestore_service import FirestoreService
from services.instagram_service import InstagramService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/publish', methods=['POST'])
def publish_to_instagram():
    """
    Endpoint to publish a Reel to Instagram.
    Expected JSON:
    {
        "character_id": "...",
        "asset_title": "primary",
        "version": "remix_kpop_watermarked",  # optional: remix_kpop_watermarked, remix_orig_watermarked, remix_structured_watermarked
        "caption": "Check out this dance! #anime #dance"  # optional
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400
    
    char_id = data.get("character_id")
    asset_title = data.get("asset_title", "primary")
    version = data.get("version", "remix_kpop_watermarked")
    custom_caption = data.get("caption")

    if not char_id:
        return jsonify({"error": "character_id is required"}), 400

    try:
        # 1. Initialize services
        gcs = GCSService()
        firestore = FirestoreService()
        instagram = InstagramService()

        # 2. Get character data from Firestore
        char = firestore.get_character(char_id)
        if not char:
            return jsonify({"error": f"Character {char_id} not found"}), 404

        # 3. Find the asset
        asset = next((a for a in char.get("assets", []) if a.get("title") == asset_title), None)
        if not asset:
            return jsonify({"error": f"Asset {asset_title} not found for character {char_id}"}), 404

        # 4. Get the video URI (GCS path)
        gcs_uri = asset.get(version)
        if not gcs_uri:
            # Fallback to standard dance_video if specific remix version is not found
            gcs_uri = asset.get("dance_video")
            logger.warning(f"Version {version} not found. Falling back to dance_video.")

        if not gcs_uri:
            return jsonify({"error": f"No video found for version {version} or dance_video"}), 404

        # 5. Generate a signed URL for Instagram (needs to be public)
        # Instagram prefers a public URL. Signed URLs work if active.
        video_url = gcs.get_signed_url(gcs_uri, expiration_hours=1)
        
        # 6. Prepare caption
        caption = custom_caption or f"{char.get('name')} from {char.get('anime')}! #anime #dance #cosplay"

        # 7. Publish to Instagram
        logger.info(f"Publishing {char_id} ({version}) to Instagram...")
        result = instagram.publish_reel(
            video_url=video_url,
            caption=caption
        )

        if result.get("success"):
            # 8. Log the post in Firestore
            firestore.save_instagram_post(
                char_id=char_id,
                asset_title=asset_title,
                media_url=gcs_uri,
                status="published",
                post_id=result.get("media_id")
            )
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"Error publishing: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/publish_random', methods=['GET', 'POST'])
def publish_random_reel():
    """
    Endpoint for Cloud Scheduler.
    Picks a random character with 'remix_orig_watermarked' and publishes it.
    """
    import random
    try:
        firestore = FirestoreService()
        gcs = GCSService()
        instagram = InstagramService()

        # 1. Get all characters
        characters = firestore.get_all_characters()
        
        # 2. Filter for those with original remix
        eligible_posts = []
        for char in characters:
            for asset in char.get("assets", []):
                if asset.get("remix_orig_watermarked"):
                    eligible_posts.append({
                        "character_id": char["id"],
                        "name": char["name"],
                        "anime": char["anime"],
                        "asset_title": asset["title"],
                        "gcs_uri": asset["remix_orig_watermarked"]
                    })
        
        if not eligible_posts:
            return jsonify({"error": "No characters found with remix_orig_watermarked"}), 404

        # 3. Optional: Filter out recently published ones (last 24-48h)
        # For now, let's just pick a random one
        post = random.choice(eligible_posts)
        
        char_id = post["character_id"]
        asset_title = post["asset_title"]
        gcs_uri = post["gcs_uri"]
        
        # 4. Generate signed URL
        video_url = gcs.get_signed_url(gcs_uri, expiration_hours=1)
        
        # 5. Prepare caption
        caption = f"{post['name']} from {post['anime']}! Remix 💙 #anime #dance #cosplay"

        # 6. Publish
        logger.info(f"🎲 Randomly selected: {char_id} (Asset: {asset_title})")
        result = instagram.publish_reel(video_url=video_url, caption=caption)

        if result.get("success"):
            firestore.save_instagram_post(
                char_id=char_id,
                asset_title=asset_title,
                media_url=gcs_uri,
                status="published",
                post_id=result.get("media_id")
            )
            return jsonify({
                "message": "Random post successful",
                "character": char_id,
                "asset": asset_title,
                **result
            }), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"Error in random publish: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
