"""
altitudeSync.py

Pushes live drone status (altitude, armed state, etc.) to Firestore on a
background thread so a Firestore round-trip (100-300ms) never blocks the
flight-command loop in Commands.py.

Reuses the same firebase-key.json / firebase_admin pattern as
CloudCenter/cloudTesting.py. If cloudTesting.py has already called
firebase_admin.initialize_app() in the same process, this will detect
that (via firebase_admin._apps) and skip re-initializing, so the two
files are safe to use together.
"""

import os  # ADDED
import queue
import threading
import time

import firebase_admin
from firebase_admin import credentials, firestore

# ADDED: resolve firebase-key.json next to THIS file (CloudCenter/),
# instead of a bare relative path — a bare "firebase-key.json" resolves
# against the process's current working directory, which changes
# depending on whether you launch main.py from the project root or run
# this file directly. This makes it work the same either way.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_KEY_PATH = os.path.join(_THIS_DIR, "firebase-key.json")


class AltitudeSync:
    def __init__(self, key_path=_DEFAULT_KEY_PATH, collection="drone_status", document="live"):  # CHANGED default
        # Avoid "app already exists" error if another module (e.g.
        # cloudTesting.py) already initialized the default Firebase app.
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()
        self.doc_ref = self.db.collection(collection).document(document)

        self._queue = queue.Queue()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def push(self, **fields):
        """Queue a non-blocking Firestore update. Safe to call from the flight loop."""
        fields["updated_at"] = time.time()
        self._queue.put(fields)

    def _run(self):
        while True:
            fields = self._queue.get()
            try:
                self.doc_ref.set(fields, merge=True)
            except Exception as e:
                print(f"[AltitudeSync] Firestore push failed: {e}")