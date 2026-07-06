"""JSON export — full project including listings and score breakdowns."""
import json


def to_bytes(project: dict):
    clean = {k: v for k, v in project.items() if k not in ("log",)}
    data = json.dumps(clean, ensure_ascii=False, indent=1).encode("utf-8")
    return data, "application/json", f"{project.get('slug','project')}.json"
