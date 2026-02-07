from services.firestore_service import FirestoreService
import json

fs = FirestoreService()
docs = fs.db.collection('characters').limit(5).stream()

for d in docs:
    data = d.to_dict()
    print(f"ID: {d.id}")
    print(f"Name: {data.get('name')}")
    assets = data.get('assets', [])
    if assets:
        print(f"First Asset Keys: {list(assets[0].keys())}")
        print(f"Dance Video: {assets[0].get('dance_video')}")
        print(f"Cosplay Image: {assets[0].get('cosplay_image')}")
    print("-" * 30)
