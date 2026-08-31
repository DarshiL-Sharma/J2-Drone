

import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
db.collection("calls").document("test_from_python").set({"status": "hello from laptop"})

print("Sent! Check Firebase console.")