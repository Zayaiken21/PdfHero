"""Source registry + parallel fan-out with progress, dedupe, and rank aggregation."""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from importlib import import_module

from utils.text_cleaner import normalize_keyword

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "12"))

SOURCES = {
    "google":     {"module": "scrapers.google_suggest",     "label": "Google",     "group": "Search"},
    "bing":       {"module": "scrapers.bing_suggest",       "label": "Bing",       "group": "Search"},
    "duckduckgo": {"module": "scrapers.duckduckgo_suggest", "label": "DuckDuckGo", "group": "Search"},
    "yahoo":      {"module": "scrapers.yahoo_suggest",      "label": "Yahoo",      "group": "Search"},
    "youtube":    {"module": "scrapers.youtube_suggest",    "label": "YouTube",    "group": "Content"},
    "pinterest":  {"module": "scrapers.pinterest_suggest",  "label": "Pinterest",  "group": "Content"},
    "amazon":     {"module": "scrapers.amazon_suggest",     "label": "Amazon",     "group": "Shopping"},
    "etsy":       {"module": "scrapers.etsy_suggest",       "label": "Etsy",       "group": "Shopping"},
    "ebay":       {"module": "scrapers.ebay_suggest",       "label": "eBay",       "group": "Shopping"},
    "walmart":    {"module": "scrapers.walmart_suggest",    "label": "Walmart",    "group": "Shopping"},
}

DEFAULT_SOURCES = ["google", "bing", "duckduckgo", "youtube"]
BROWSER_TREND_SOURCES = ["google", "bing", "duckduckgo", "yahoo"]  # "Browser Search Trends"
SHOPPING_SOURCES = ["amazon", "etsy", "ebay", "walmart"]


def fetch(source: str, query: str, **kwargs):
    """Fetch suggestions from one source. Never raises; returns a deduped list."""
    info = SOURCES.get(source)
    if not info:
        return []
    try:
        mod = import_module(info["module"])
        raw = mod.fetch(query, **kwargs) or []
    except Exception:
        return []
    out, seen = [], set()
    for s in raw:
        if not isinstance(s, str):
            continue
        key = normalize_keyword(s)
        if key and key not in seen:
            seen.add(key)
            out.append(s.strip())
    return out


def fetch_many(queries, sources=None, progress=None, lang="en", country="us"):
    """Fan a list of queries across sources in parallel (rate-limited per domain).

    Returns rows: {keyword, sources, source_count, frequency, best_rank},
    sorted by breadth then frequency.
    """
    sources = sources or DEFAULT_SOURCES
    tasks = [(src, q) for q in queries for src in sources]
    merged = {}
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch, src, q, lang=lang, country=country): (src, q)
                   for src, q in tasks}
        for fut in as_completed(futures):
            src, q = futures[fut]
            suggestions = fut.result() or []
            for rank, kw in enumerate(suggestions):
                key = normalize_keyword(kw)
                if not key or len(key) < 3:
                    continue
                row = merged.setdefault(key, {"keyword": key, "sources": set(),
                                              "frequency": 0, "best_rank": 99})
                row["sources"].add(src)
                row["frequency"] += 1
                row["best_rank"] = min(row["best_rank"], rank)
            done += 1
            if progress:
                progress(done, len(tasks), f"{SOURCES[src]['label']} · {q}")
    rows = []
    for row in merged.values():
        row["sources"] = sorted(row["sources"])
        row["source_count"] = len(row["sources"])
        rows.append(row)
    rows.sort(key=lambda r: (-r["source_count"], -r["frequency"], r["best_rank"]))
    return rows


def per_source_panel(query: str, sources=None, lang="en", country="us"):
    """{source_label: [suggestions]} — used by the Browser Search Trends panel."""
    sources = sources or BROWSER_TREND_SOURCES
    panel = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch, src, query, lang=lang, country=country): src
                   for src in sources}
        for fut in as_completed(futures):
            src = futures[fut]
            panel[SOURCES[src]["label"]] = fut.result() or []
    return panel
