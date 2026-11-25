"""Theo dõi trạng thái từng video: rendered -> approved -> uploaded."""
import sqlite3
from datetime import datetime
from .config import ROOT

DB = ROOT / "studio.db"


def conn():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY, title TEXT, status TEXT,
        path TEXT, youtube_id TEXT, created_at TEXT)""")
    return c


def add(vid: str, title: str, path: str):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO videos VALUES (?,?,?,?,?,?)",
                  (vid, title, "rendered", path, None, datetime.now().isoformat(timespec="seconds")))


def set_status(vid: str, status: str, youtube_id: str | None = None):
    with conn() as c:
        c.execute("UPDATE videos SET status=?, youtube_id=COALESCE(?, youtube_id) WHERE id=?",
                  (status, youtube_id, vid))


def get(vid: str):
    with conn() as c:
        return c.execute("SELECT * FROM videos WHERE id=?", (vid,)).fetchone()


def all_videos():
    with conn() as c:
        return c.execute("SELECT id, status, title, youtube_id FROM videos ORDER BY created_at DESC").fetchall()
