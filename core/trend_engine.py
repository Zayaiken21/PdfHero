"""Trend engine: automatic PDF-niche discovery, keyword expansion, and
Google Trends signals (via pytrends when available; labeled estimates otherwise).
"""
from __future__ import annotations

import random
import string

from utils.cache import cache
from utils.rate_limiter import limiter

CATEGORY_SEEDS = [
    "planner", "tracker", "journal", "worksheet", "template", "checklist",
    "form", "calendar", "workbook", "study guide", "printable game",
    "kids activity", "homeschool packet", "teacher resource", "budget template",
    "debt payoff sheet", "meal planner", "fitness log", "wedding planner",
    "business template", "client intake form", "social media planner",
    "real estate checklist", "cleaning schedule", "travel planner",
    "self care journal", "habit tracker",
]

MODIFIERS = [
    "printable", "template", "pdf", "digital download", "editable", "bundle",
    "for beginners", "for kids", "for teachers", "for small business",
    "weekly", "monthly", "2026", "free", "aesthetic", "minimalist",
]

QUESTION_PREFIXES = ["how to make", "best", "free", "printable", "editable"]


def expand_keyword(seed: str, letters: bool = True, modifiers: bool = True,
                   questions: bool = False, max_terms: int = 60) -> list[str]:
    """Build the query fan-out list for a seed keyword."""
    seed = (seed or "").strip().lower()
    queries = [seed]
    if modifiers:
        queries += [f"{seed} {m}" for m in MODIFIERS]
        queries += [f"{m} {seed}" for m in ("printable", "editable", "free")]
    if letters:
        queries += [f"{seed} {c}" for c in string.ascii_lowercase]
        queries += [f"{seed} {d}" for d in "012345"]
    if questions:
        queries += [f"{p} {seed}" for p in QUESTION_PREFIXES]
    seen, out = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:max_terms]


def discover_seeds(count: int = 6, audience: str = "") -> list[str]:
    """Pick category seeds for automatic discovery, optionally audience-flavored."""
    picks = random.sample(CATEGORY_SEEDS, k=min(count, len(CATEGORY_SEEDS)))
    if audience:
        picks = [f"{p} for {audience.strip().lower()}" for p in picks]
    return picks


def _pytrends_signal(keyword: str, geo: str = "") -> dict | None:
    try:
        from pytrends.request import TrendReq
    except Exception:
        return None
    try:
        limiter.wait("trends.google.com")
        py = TrendReq(hl="en-US", tz=0, timeout=(4, 12))
        py.build_payload([keyword], timeframe="today 12-m", geo=geo or "")
        df = py.interest_over_time()
        if df is None or df.empty or keyword not in df:
            return None
        series = df[keyword].astype(float)
        mean_interest = float(series.mean())
        recent = float(series.tail(8).mean())
        prior = float(series.iloc[-16:-8].mean()) if len(series) >= 16 else mean_interest
        slope = 0.0 if prior == 0 else (recent - prior) / max(prior, 1.0)
        if slope > 0.15:
            label = "Rising"
        elif slope < -0.15:
            label = "Declining"
        else:
            label = "Stable"
        top_region = ""
        try:
            reg = py.interest_by_region(resolution="COUNTRY", inc_low_vol=False)
            if reg is not None and not reg.empty and keyword in reg:
                top_region = str(reg[keyword].astype(float).idxmax())
        except Exception:
            top_region = ""
        return {"trend_label": label, "trend_interest": round(mean_interest, 1),
                "trend_slope": round(slope, 3), "estimated": False,
                "top_region": top_region}
    except Exception:
        return None


def trend_signal(keyword: str, geo: str = "", country_name: str = "") -> dict:
    """Cached 24h Google Trends signal; graceful labeled estimate on failure."""
    key = f"{geo}:{keyword.lower()}"
    hit = cache.get("trend", key)
    if hit:
        return hit
    sig = _pytrends_signal(keyword, geo=geo)
    if sig is None:
        sig = {"trend_label": "Est. Stable", "trend_interest": 20.0,
               "trend_slope": 0.0, "estimated": True,
               "top_region": country_name or "—"}
        cache.set("trend", key, sig, ttl=3 * 3600)
    else:
        if not sig.get("top_region"):
            sig["top_region"] = country_name or "Worldwide"
        cache.set("trend", key, sig, ttl=24 * 3600)
    return sig


def attach_trends(rows: list[dict], top_n: int = 12, geo: str = "",
                  country_name: str = "", progress_cb=None) -> list[dict]:
    """Fetch real trend signals for the top rows only (Trends rate limits hard);
    remaining rows get the estimate label."""
    for i, row in enumerate(rows):
        if i < top_n:
            sig = trend_signal(row.get("keyword", ""), geo=geo, country_name=country_name)
        else:
            sig = {"trend_label": "Est. Stable", "trend_interest": 18.0,
                   "trend_slope": 0.0, "estimated": True,
                   "top_region": country_name or "—"}
        row.update(sig)
        if progress_cb:
            progress_cb(i + 1, len(rows), row.get("keyword", ""))
    return rows
