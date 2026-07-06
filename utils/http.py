"""Shared HTTP layer: rotating UA, per-domain rate limiting, caching, retries,
JSON/JSONP handling, source-health tracking, and suggestion-string extraction."""
import json
import os
import random
import threading
import time
from urllib.parse import urlparse

from utils.cache import cache
from utils.rate_limiter import limiter

DEFAULT_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

_health_lock = threading.Lock()
SOURCE_HEALTH = {}  # domain -> {ok, fail, last_error, last_ok}


def _record(domain: str, ok: bool, err: str = ""):
    with _health_lock:
        h = SOURCE_HEALTH.setdefault(domain, {"ok": 0, "fail": 0, "last_error": "", "last_ok": None})
        if ok:
            h["ok"] += 1
            h["last_error"] = ""
            h["last_ok"] = time.strftime("%H:%M:%S")
        else:
            h["fail"] += 1
            h["last_error"] = str(err)[:180]


def get_text(url: str, params=None, headers=None, timeout: int = None,
             ttl: int = None, use_cache: bool = True, retries: int = 2):
    """GET a URL politely. Returns response text or None (never raises)."""
    import requests
    cache_key = url + "|" + json.dumps(params or {}, sort_keys=True)
    if use_cache:
        hit = cache.get("http", cache_key)
        if hit is not None:
            return hit
    domain = urlparse(url).netloc
    base_headers = {
        "User-Agent": random.choice(UA_POOL),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json, text/javascript, text/html;q=0.8, */*;q=0.5",
    }
    if headers:
        base_headers.update(headers)
    last_err = ""
    for attempt in range(retries + 1):
        limiter.wait(domain)
        try:
            if attempt:  # fresh identity + growing pause on retry
                base_headers["User-Agent"] = random.choice(UA_POOL)
                time.sleep(0.6 * attempt)
            resp = requests.get(url, params=params, headers=base_headers,
                                timeout=timeout or DEFAULT_TIMEOUT)
            if resp.status_code in (403, 429) and attempt < retries:
                retry_after = resp.headers.get("Retry-After")
                try:
                    time.sleep(min(4.0, float(retry_after)) if retry_after else 1.2)
                except ValueError:
                    time.sleep(1.2)
                last_err = f"HTTP {resp.status_code}"
                continue
            if resp.status_code == 200:
                _record(domain, True)
                if use_cache:
                    cache.set("http", cache_key, resp.text, ttl)
                return resp.text
            last_err = f"HTTP {resp.status_code}"
            if resp.status_code in (403, 404, 410, 451):
                break  # not retryable
        except Exception as exc:  # timeout / conn errors
            last_err = repr(exc)
        time.sleep(0.4 * (attempt + 1))
    _record(domain, False, last_err)
    return None


def get_json(url: str, **kwargs):
    """GET JSON (handles JSONP wrappers). Returns parsed object or None."""
    text = get_text(url, **kwargs)
    if text is None:
        return None
    stripped = text.strip()
    if stripped and stripped[0] not in "{[":  # JSONP: fn( ... )
        start, end = stripped.find("("), stripped.rfind(")")
        if start != -1 and end > start:
            stripped = stripped[start + 1:end]
    try:
        return json.loads(stripped)
    except Exception:
        _record(urlparse(url).netloc, False, "unparseable JSON")
        return None


def opensearch_list(obj):
    """Parse the common OpenSearch suggestion shape: [query, [s1, s2, ...]]."""
    if isinstance(obj, list) and len(obj) > 1 and isinstance(obj[1], list):
        return [s for s in obj[1] if isinstance(s, str)]
    return []


_SUGGEST_KEYS = {"query", "term", "value", "displayName", "k", "key", "phrase",
                 "suggestion", "text", "title", "searchTerm"}


def collect_strings(obj, out=None, max_items=60):
    """Walk arbitrary JSON collecting likely suggestion strings by key name."""
    if out is None:
        out = []
    if len(out) >= max_items:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and k in _SUGGEST_KEYS and 2 < len(v) < 120:
                out.append(v)
            elif k == "sug" and isinstance(v, list):
                out.extend(s for s in v if isinstance(s, str))
            else:
                collect_strings(v, out, max_items)
    elif isinstance(obj, list):
        for item in obj:
            collect_strings(item, out, max_items)
    return out
