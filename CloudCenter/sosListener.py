from google.cloud import firestore

class SOSListener:
    def __init__(self, on_sos_active, credentials_path="CloudCenter/firebase-key.json"):
        self.db = firestore.Client.from_service_account_json(credentials_path)
        self.on_sos_active = on_sos_active
        self._seen_ids = set()

    def start(self):
        query = self.db.collection("sos_alerts").where("status", "==", "active")
        self._watch = query.on_snapshot(self._on_snapshot)

    def _on_snapshot(self, col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name not in ("ADDED", "MODIFIED"):
                continue
            doc = change.document
            if doc.id in self._seen_ids:
                continue
            data = doc.to_dict()
            lat, lng = data.get("lat"), data.get("lng")
            if lat is None or lng is None:
                continue
            self._seen_ids.add(doc.id)
            self.on_sos_active(sos_id=doc.id, lat=lat, lng=lng,
                                message=data.get("message", ""))

    def stop(self):
        if hasattr(self, "_watch"):
            self._watch.unsubscribe()