"""Storage for SOS alerts submitted by the companion mobile app.

Each alert (a survivor pressing the SOS button in the app) carries several
fields (name, phone, self-reported health condition, GPS location) plus two
photos (front + back camera). A single flat file per victim doesn't cleanly
hold that - and we need to tell one victim's report apart from another's -
so this uses a small local SQLite database (stdlib, no extra dependency,
no server to run) with one row per alert. The photos themselves are still
written to disk under SOS_DIR (same pattern as VICTIM_DIR/FIRE_DIR) and the
database row just stores their paths, so large image bytes never sit inside
the DB.

NOTE: this module only provides the *storage* side (save/list/get). Nothing
in this project currently calls save_sos_report() yet - that happens once a
network receiver (e.g. a small HTTP endpoint the mobile app POSTs to) is
wired up to accept incoming SOS submissions from the field. The dashboard
UI already polls list_sos_reports() and will show alerts as soon as
something starts calling save_sos_report().
"""

import os
import sqlite3
import threading
import datetime

from ConstantsCenter.constants import SOS_DIR, SOS_DB_PATH

_lock = threading.Lock()


def _get_conn():
    os.makedirs(SOS_DIR, exist_ok=True)
    db_dir = os.path.dirname(SOS_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(SOS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sos_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                health_condition TEXT,
                latitude REAL,
                longitude REAL,
                front_image_path TEXT,
                back_image_path TEXT,
                created_at TEXT NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def save_sos_report(name=None, phone=None, health_condition=None,
                     latitude=None, longitude=None,
                     front_image_bytes=None, back_image_bytes=None):
    """Inserts one SOS alert and returns its new row id.

    front_image_bytes / back_image_bytes, if given, are raw image bytes
    (e.g. straight from an HTTP upload) - they get written to SOS_DIR and
    the resulting file paths are stored alongside the rest of the report.
    """
    init_db()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    front_path = None
    back_path = None
    os.makedirs(SOS_DIR, exist_ok=True)
    if front_image_bytes:
        front_path = os.path.join(SOS_DIR, f"sos_{ts}_front.jpg")
        with open(front_path, "wb") as f:
            f.write(front_image_bytes)
    if back_image_bytes:
        back_path = os.path.join(SOS_DIR, f"sos_{ts}_back.jpg")
        with open(back_path, "wb") as f:
            f.write(back_image_bytes)

    with _lock, _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO sos_reports
               (name, phone, health_condition, latitude, longitude,
                front_image_path, back_image_path, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, phone, health_condition, latitude, longitude,
             front_path, back_path,
             datetime.datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def list_sos_reports(limit=None):
    """Newest-first list of SOS alerts as plain dicts - safe to call from
    the GUI thread on a timer, same as list_victim_captures/list_fire_captures."""
    init_db()
    with _lock, _get_conn() as conn:
        query = "SELECT * FROM sos_reports ORDER BY id DESC"
        if limit:
            rows = conn.execute(query + " LIMIT ?", (limit,)).fetchall()
        else:
            rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def get_sos_report(report_id):
    init_db()
    with _lock, _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sos_reports WHERE id = ?", (report_id,)
        ).fetchone()
    return dict(row) if row else None


def mark_acknowledged(report_id, acknowledged=True):
    """Lets the operator mark a report as handled - not wired to any UI
    button yet, but ready for when that's wanted."""
    init_db()
    with _lock, _get_conn() as conn:
        conn.execute(
            "UPDATE sos_reports SET acknowledged = ? WHERE id = ?",
            (1 if acknowledged else 0, report_id),
        )
