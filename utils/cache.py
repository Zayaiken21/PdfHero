"""Simple disk-backed JSON cache with TTL. Safe to fail silently."""
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

DEFAULT_TTL = int(float(os.getenv("CACHE_TTL_HOURS", "6")) * 3600)


class DiskCache:
    def __init__(self, root="data/cache", default_ttl=DEFAULT_TTL):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

    def _path(self, ns: str, key: str) -> Path:
        digest = hashlib.sha1(f"{ns}|{key}".encode("utf-8", "ignore")).hexdigest()
        folder = self.root / ns
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{digest}.json"

    def get(self, ns: str, key: str):
        p = self._path(ns, key)
        if not p.exists():
            return None
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            if obj.get("exp", 0) < time.time():
                p.unlink(missing_ok=True)
                return None
            return obj.get("val")
        except Exception:
            return None

    def set(self, ns: str, key: str, val, ttl=None):
        try:
            p = self._path(ns, key)
            p.write_text(json.dumps({"exp": time.time() + (ttl or self.default_ttl), "val": val}),
                         encoding="utf-8")
        except Exception:
            pass

    def stats(self):
        files = list(self.root.rglob("*.json"))
        return {"entries": len(files), "megabytes": round(sum(f.stat().st_size for f in files) / 1e6, 2)}

    def clear(self):
        for child in self.root.iterdir():
            try:
                shutil.rmtree(child) if child.is_dir() else child.unlink()
            except Exception:
                pass


cache = DiskCache()
