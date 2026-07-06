"""Project persistence — per-user, backed by SQLite (core/db.py)."""
from __future__ import annotations

import time

from core import db
from utils.text_cleaner import slugify


def save_project(user_id: int, name: str, ptype: str, seed: str, rows: list[dict],
                 listing: dict | None = None, notes: str = "") -> dict:
    slug = slugify(name) or f"project-{int(time.time())}"
    project = {
        "name": name, "slug": slug, "type": ptype, "seed": seed,
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "rows": rows or [], "listing": listing or {}, "notes": notes,
    }
    return db.save_project_db(user_id, project)


def load_project(user_id: int, slug: str) -> dict | None:
    return db.load_project_db(user_id, slug)


def list_projects(user_id: int) -> list[dict]:
    return db.list_projects_db(user_id)


def delete_project(user_id: int, slug: str) -> bool:
    return db.delete_project_db(user_id, slug)


def delete_all_projects(user_id: int) -> int:
    return db.delete_all_projects_db(user_id)
