from services.firestore_service import FirestoreService
import json

fs = FirestoreService()
docs = fs.db.collection('characters').stream()

print(f"{'ID':<30} | {'Dance':<7} | {'Cosplay':<7}")
print("-" * 50)

count = 0
for d in docs:
    data = d.to_dict()
    assets = data.get("assets", [])
    has_dance = False
    has_cosplay = False
    
    if assets:
        primary = assets[0]
        has_dance = bool(primary.get("dance_video"))
        has_cosplay = bool(primary.get("cosplay_image"))
        
    print(f"{d.id:<30} | {str(has_dance):<7} | {str(has_cosplay):<7}")
    count += 1

print("-" * 50)
print(f"Total characters: {count}")
