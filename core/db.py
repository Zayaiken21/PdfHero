"""SQLite multi-user storage — each workspace (user) sees only their own data.

Tables:
  users(id, username UNIQUE, salt, pin_hash, created)
  projects(id, user_id, name, slug, type, seed, created, data JSON)
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager

from core.config import DATA_DIR

DB_PATH = DATA_DIR / "app.db"


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            created TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            type TEXT, seed TEXT, created TEXT,
            data TEXT NOT NULL,
            UNIQUE(user_id, slug))""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id)")
        _migrate(con)


def _migrate(con):
    """Additive, safe migrations for existing databases (keeps current users)."""
    cols = [r[1] for r in con.execute("PRAGMA table_info(users)").fetchall()]
    if "device_id" not in cols:
        con.execute("ALTER TABLE users ADD COLUMN device_id TEXT DEFAULT ''")


def _hash(pin: str, salt: str) -> str:
    return hashlib.sha256((salt + pin).encode()).hexdigest()


def login_or_register(username: str, pin: str) -> tuple[dict | None, str]:
    """Returns (user, message). Creates the workspace if it doesn't exist."""
    username = (username or "").strip().lower()
    pin = (pin or "").strip()
    if len(username) < 2:
        return None, "Workspace name needs at least 2 characters."
    if len(pin) < 4:
        return None, "PIN needs at least 4 characters."
    init_db()
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row:
            if _hash(pin, row["salt"]) != row["pin_hash"]:
                return None, "Wrong PIN for this workspace."
            return {"id": row["id"], "username": row["username"]}, "Welcome back."
        salt = secrets.token_hex(8)
        cur = con.execute(
            "INSERT INTO users(username, salt, pin_hash, created) VALUES(?,?,?,?)",
            (username, salt, _hash(pin, salt), time.strftime("%Y-%m-%d %H:%M")))
        return {"id": cur.lastrowid, "username": username}, "Workspace created."


# ── PDF Hero account system ──────────────────────────────────────────
# Unique workspace names, sign-in vs create as separate strict flows, and
# recovery that ONLY works from the device that owns the workspace.
import re as _re

USERNAME_RE = _re.compile(r"^[a-z0-9_.]{2,24}$")


def username_taken(username: str) -> bool:
    init_db()
    with _conn() as con:
        return con.execute("SELECT 1 FROM users WHERE username=?",
                           ((username or "").strip().lower(),)).fetchone() is not None


def register_user(username: str, pin: str, device_id: str = "") -> tuple[dict | None, str]:
    """Create a NEW workspace. Fails if the name exists — names are unique."""
    username = (username or "").strip().lower()
    pin = (pin or "").strip()
    if not USERNAME_RE.match(username):
        return None, "Workspace names are 2–24 characters: letters, numbers, _ or . only."
    if len(pin) < 4:
        return None, "PIN needs at least 4 characters."
    init_db()
    with _conn() as con:
        if con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            return None, "That name is already taken — workspace names are unique. Pick another, or sign in."
        salt = secrets.token_hex(8)
        cur = con.execute(
            "INSERT INTO users(username, salt, pin_hash, created, device_id) VALUES(?,?,?,?,?)",
            (username, salt, _hash(pin, salt), time.strftime("%Y-%m-%d %H:%M"),
             device_id or ""))
        return ({"id": cur.lastrowid, "username": username},
                "Workspace created. This device is now its recovery key.")


def login_user(username: str, pin: str, device_id: str = "") -> tuple[dict | None, str]:
    """Sign in to an EXISTING workspace only — never silently creates one."""
    username = (username or "").strip().lower()
    pin = (pin or "").strip()
    if not username or not pin:
        return None, "Enter your workspace name and PIN."
    init_db()
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return None, "No workspace with that name. Create one in the Create tab."
        if _hash(pin, row["salt"]) != row["pin_hash"]:
            return None, "Wrong PIN for this workspace."
        # first successful sign-in from a device binds it if none is bound yet
        if device_id and not (row["device_id"] or ""):
            con.execute("UPDATE users SET device_id=? WHERE id=?", (device_id, row["id"]))
        return {"id": row["id"], "username": row["username"]}, "Welcome back."


def recover_usernames_by_device(device_id: str) -> list[str]:
    """Workspace names registered to THIS device only. Empty elsewhere — strict."""
    if not device_id:
        return []
    init_db()
    with _conn() as con:
        rows = con.execute("SELECT username FROM users WHERE device_id=? ORDER BY username",
                           (device_id,)).fetchall()
    return [r["username"] for r in rows]


def reset_pin_with_device(username: str, device_id: str, new_pin: str) -> tuple[bool, str]:
    """Set a new PIN — allowed ONLY from the workspace's bound device."""
    username = (username or "").strip().lower()
    new_pin = (new_pin or "").strip()
    if len(new_pin) < 4:
        return False, "New PIN needs at least 4 characters."
    if not device_id:
        return False, "This browser has no device key — recovery isn't available here."
    init_db()
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return False, "No workspace with that name."
        if not (row["device_id"] or "") or row["device_id"] != device_id:
            return False, ("Recovery is locked to the device this workspace was created on. "
                           "This device doesn't match, so the PIN can't be reset here.")
        salt = secrets.token_hex(8)
        con.execute("UPDATE users SET salt=?, pin_hash=? WHERE id=?",
                    (salt, _hash(new_pin, salt), row["id"]))
    return True, "PIN updated — sign in with the new PIN."


def change_pin(user_id: int, old_pin: str, new_pin: str) -> tuple[bool, str]:
    new_pin = (new_pin or "").strip()
    if len(new_pin) < 4:
        return False, "New PIN needs at least 4 characters."
    init_db()
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return False, "Workspace not found."
        if _hash((old_pin or "").strip(), row["salt"]) != row["pin_hash"]:
            return False, "Current PIN is wrong."
        salt = secrets.token_hex(8)
        con.execute("UPDATE users SET salt=?, pin_hash=? WHERE id=?",
                    (salt, _hash(new_pin, salt), user_id))
    return True, "PIN changed."


def device_binding(user_id: int) -> str:
    init_db()
    with _conn() as con:
        row = con.execute("SELECT device_id FROM users WHERE id=?", (user_id,)).fetchone()
    return (row["device_id"] or "") if row else ""


def delete_all_projects_db(user_id: int) -> int:
    """Wipe every project for one workspace. Returns how many were removed."""
    init_db()
    with _conn() as con:
        cur = con.execute("DELETE FROM projects WHERE user_id=?", (user_id,))
        return cur.rowcount


def save_project_db(user_id: int, project: dict) -> dict:
    init_db()
    with _conn() as con:
        con.execute("""INSERT INTO projects(user_id, name, slug, type, seed, created, data)
                       VALUES(?,?,?,?,?,?,?)
                       ON CONFLICT(user_id, slug) DO UPDATE SET
                         name=excluded.name, data=excluded.data""",
                    (user_id, project["name"], project["slug"], project.get("type", ""),
                     project.get("seed", ""), project.get("created", ""),
                     json.dumps(project, ensure_ascii=False)))
    return project


def load_project_db(user_id: int, slug: str) -> dict | None:
    init_db()
    with _conn() as con:
        row = con.execute("SELECT data FROM projects WHERE user_id=? AND slug=?",
                          (user_id, slug)).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["data"])
    except Exception:
        return None


def list_projects_db(user_id: int) -> list[dict]:
    init_db()
    out = []
    with _conn() as con:
        rows = con.execute("""SELECT name, slug, type, created, data FROM projects
                              WHERE user_id=? ORDER BY id DESC""", (user_id,)).fetchall()
    for row in rows:
        try:
            data = json.loads(row["data"])
        except Exception:
            data = {}
        out.append({"name": row["name"], "slug": row["slug"], "type": row["type"],
                    "created": row["created"],
                    "keywords": len(data.get("rows", [])),
                    "has_listing": bool(data.get("listing"))})
    return out


def delete_project_db(user_id: int, slug: str) -> bool:
    init_db()
    with _conn() as con:
        cur = con.execute("DELETE FROM projects WHERE user_id=? AND slug=?", (user_id, slug))
        return cur.rowcount > 0
