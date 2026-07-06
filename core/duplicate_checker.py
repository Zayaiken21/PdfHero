"""Duplicate detection: exact -> normalized -> fuzzy (RapidFuzz, difflib fallback)
-> optional semantic. Works on keywords, titles, tags, phrases, URLs.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from utils.text_cleaner import normalize_keyword

FUZZY_THRESHOLD = 88  # 0-100 (lower = more aggressive de-dup)


def _singular(word: str) -> str:
    for suf, rep in (("ies", "y"), ("ses", "s"), ("es", ""), ("s", "")):
        if len(word) > 3 and word.endswith(suf):
            return word[: -len(suf)] + rep
    return word


def canonical_key(text: str) -> str:
    """Word-order- and plural-insensitive key so 'budget planners' and
    'planner budget' collapse to the same thing."""
    toks = [_singular(w) for w in normalize_keyword(text).split()]
    return " ".join(sorted(t for t in toks if t))


def _fuzzy_ratio(a: str, b: str) -> float:
    try:
        from rapidfuzz import fuzz
        return float(fuzz.token_set_ratio(a, b))
    except Exception:
        import difflib
        return difflib.SequenceMatcher(None, a, b).ratio() * 100.0


def normalize_url(url: str) -> str:
    try:
        parts = urlsplit((url or "").strip().lower())
        host = parts.netloc.replace("www.", "")
        return f"{host}{parts.path}".rstrip("/")
    except Exception:
        return (url or "").strip().lower()


def dedupe_strings(items: list[str], fuzzy: bool = True,
                   threshold: int = FUZZY_THRESHOLD) -> list[str]:
    """Order-preserving dedupe of plain strings."""
    kept: list[str] = []
    seen_norm: set[str] = set()
    for item in items or []:
        item = (item or "").strip()
        if not item:
            continue
        norm = canonical_key(item)
        if norm in seen_norm:
            continue
        if fuzzy and any(_fuzzy_ratio(norm, canonical_key(k)) >= threshold for k in kept):
            continue
        seen_norm.add(norm)
        kept.append(item)
    return kept


def dedupe_rows(rows: list[dict], key: str = "keyword", fuzzy: bool = True,
                threshold: int = FUZZY_THRESHOLD) -> list[dict]:
    """Dedupe row dicts on `key`, merging sources/frequency into the survivor."""
    kept: list[dict] = []
    norms: list[str] = []
    for row in rows or []:
        value = (row.get(key) or "").strip()
        if not value:
            continue
        norm = canonical_key(value)
        match_idx = -1
        if norm in norms:
            match_idx = norms.index(norm)
        elif fuzzy:
            for i, existing in enumerate(norms):
                if _fuzzy_ratio(norm, existing) >= threshold:
                    match_idx = i
                    break
        if match_idx >= 0:
            survivor = kept[match_idx]
            survivor["frequency"] = int(survivor.get("frequency", 0)) + int(row.get("frequency", 0))
            merged = sorted(set(survivor.get("sources", [])) | set(row.get("sources", [])))
            survivor["sources"] = merged
            survivor["source_count"] = len(merged)
            continue
        norms.append(norm)
        kept.append(dict(row))
    return kept


def find_dupe_groups(items: list[str], threshold: int = FUZZY_THRESHOLD) -> list[list[str]]:
    """Return groups of near-duplicate strings (for the Analytics page)."""
    groups: list[list[str]] = []
    assigned: set[int] = set()
    norms = [canonical_key(i or "") for i in (items or [])]
    for i, a in enumerate(norms):
        if i in assigned or not a:
            continue
        group = [items[i]]
        for j in range(i + 1, len(norms)):
            if j in assigned or not norms[j]:
                continue
            if a == norms[j] or _fuzzy_ratio(a, norms[j]) >= threshold:
                group.append(items[j])
                assigned.add(j)
        if len(group) > 1:
            assigned.add(i)
            groups.append(group)
    return groups


def semantic_dupes(items: list[str], threshold: float = 0.9) -> list[list[str]]:
    """Optional semantic grouping if sentence-transformers is installed; else []."""
    try:
        from sentence_transformers import SentenceTransformer, util
        model = SentenceTransformer("all-MiniLM-L6-v2")
        emb = model.encode(items, convert_to_tensor=True, show_progress_bar=False)
        sims = util.cos_sim(emb, emb)
        groups, assigned = [], set()
        for i in range(len(items)):
            if i in assigned:
                continue
            group = [items[i]]
            for j in range(i + 1, len(items)):
                if j not in assigned and float(sims[i][j]) >= threshold:
                    group.append(items[j])
                    assigned.add(j)
            if len(group) > 1:
                assigned.add(i)
                groups.append(group)
        return groups
    except Exception:
        return []
