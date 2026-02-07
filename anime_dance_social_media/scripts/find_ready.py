from services.firestore_service import FirestoreService

fs = FirestoreService()
docs = fs.db.collection('characters').stream()

for d in docs:
    data = d.to_dict()
    assets = data.get('assets', [])
    if assets:
        primary = assets[0]
        if primary.get('dance_video'): # Found one with dance video
            print(f"Found ready: {d.id}")
            print(f"Keys: {list(primary.keys())}")
            break
