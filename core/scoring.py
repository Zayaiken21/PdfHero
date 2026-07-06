"""SEO content scoring: score generated titles/descriptions/tags per platform.

Dimensions: keyword placement, title length, description length, readability,
click-through potential, uniqueness, buyer intent, platform fit, search intent
match, semantic richness. Returns /100 plus actionable tips.
"""
from __future__ import annotations

import re

from utils.text_cleaner import clean_text, flesch_reading_ease, tokenize
from nlp.intent_classifier import classify

PLATFORM_RULES = {
    "etsy": {"title_max": 140, "title_ideal": (60, 140), "tags_max": 13,
             "tag_char_max": 20, "desc_ideal": (400, 1200)},
    "gumroad": {"title_max": 90, "title_ideal": (30, 80), "tags_max": 20,
                "tag_char_max": 30, "desc_ideal": (300, 1500)},
    "shopify": {"title_max": 70, "title_ideal": (30, 65), "tags_max": 25,
                "tag_char_max": 30, "desc_ideal": (300, 1500)},
    "ebay": {"title_max": 80, "title_ideal": (40, 80), "tags_max": 15,
             "tag_char_max": 30, "desc_ideal": (200, 1200)},
    "payhip": {"title_max": 90, "title_ideal": (30, 80), "tags_max": 15,
               "tag_char_max": 30, "desc_ideal": (300, 1500)},
}

CTR_WORDS = {
    "printable", "editable", "instant", "download", "bundle", "template",
    "planner", "digital", "easy", "ultimate", "complete", "2025", "2026",
    "guide", "kit", "pack", "pdf",
}
POWER_VERBS = {"organize", "track", "plan", "save", "grow", "boost", "simplify",
               "master", "manage", "achieve"}


def _band(value: float, lo: float, hi: float) -> float:
    """1.0 inside [lo,hi], linear falloff outside."""
    if lo <= value <= hi:
        return 1.0
    if value < lo:
        return max(0.0, value / max(1.0, lo))
    return max(0.0, 1.0 - (value - hi) / max(1.0, hi))


def _uniqueness(text: str, corpus: list[str]) -> float:
    """1.0 = clearly distinct from every corpus item (fuzzy)."""
    if not corpus:
        return 1.0
    target = clean_text(text).lower()
    best = 0.0
    try:
        from rapidfuzz import fuzz  # optional
        for other in corpus:
            best = max(best, fuzz.token_set_ratio(target, clean_text(other).lower()) / 100.0)
    except Exception:
        import difflib
        for other in corpus:
            best = max(best, difflib.SequenceMatcher(
                None, target, clean_text(other).lower()).ratio())
    return max(0.0, 1.0 - best) if best > 0.92 else max(0.0, 1.0 - best * 0.6)


def score_listing(title: str, description: str, tags: list[str],
                  focus_keyword: str, platform: str = "etsy",
                  corpus_titles: list[str] | None = None) -> dict:
    """Score one platform listing. Returns {'score': int, 'dims': {...}, 'tips': [...]}"""
    rules = PLATFORM_RULES.get(platform.lower(), PLATFORM_RULES["etsy"])
    title = title or ""
    description = description or ""
    tags = [t for t in (tags or []) if t]
    kw = (focus_keyword or "").lower().strip()
    kw_tokens = set(tokenize(kw))
    tips: list[str] = []
    dims: dict[str, float] = {}

    # 1. Keyword placement (front-loaded in title, present in first 160 desc chars, in tags)
    t_low, d_low = title.lower(), description.lower()
    place = 0.0
    if kw and kw in t_low:
        place += 0.5 if t_low.index(kw) <= 20 else 0.35
    elif kw_tokens and kw_tokens & set(tokenize(t_low)):
        place += 0.25
    else:
        tips.append(f'Put "{focus_keyword}" near the start of the title.')
    if kw and kw in d_low[:200]:
        place += 0.3
    elif kw:
        tips.append("Mention the focus keyword in the first two sentences of the description.")
    if kw and any(kw in (t or "").lower() for t in tags):
        place += 0.2
    dims["keyword_placement"] = min(1.0, place)

    # 2. Title length
    lo, hi = rules["title_ideal"]
    dims["title_length"] = _band(len(title), lo, hi)
    if len(title) > rules["title_max"]:
        tips.append(f"Title exceeds {platform.title()}'s {rules['title_max']}-char limit — trim it.")
    elif len(title) < lo:
        tips.append("Title is short — add a descriptive modifier (printable, template, bundle).")

    # 3. Description length
    dlo, dhi = rules["desc_ideal"]
    dims["description_length"] = _band(len(description), dlo, dhi)
    if len(description) < dlo:
        tips.append("Description is thin — expand features, use-cases, and what's included.")

    # 4. Readability
    fre = flesch_reading_ease(description) if description else 0.0
    dims["readability"] = _band(fre, 50, 85)
    if fre and fre < 45:
        tips.append("Sentences read as complex — shorten them for buyers skimming on mobile.")

    # 5. CTR heuristics
    words = set(tokenize(t_low))
    hits = len(words & CTR_WORDS)
    has_number = bool(re.search(r"\d", title))
    dims["ctr_potential"] = min(1.0, hits * 0.28 + (0.16 if has_number else 0.0))
    if hits == 0:
        tips.append("Add a click word buyers scan for: printable, editable, instant download, bundle.")

    # 6. Uniqueness vs other titles in the project
    dims["uniqueness"] = _uniqueness(title, corpus_titles or [])
    if dims["uniqueness"] < 0.4:
        tips.append("This title is very close to another one in the project — differentiate it.")

    # 7. Buyer intent language
    res = classify(f"{title} {description[:300]}")
    verbs = len(set(tokenize(d_low)) & POWER_VERBS)
    dims["buyer_intent"] = min(1.0, res["buyer_intent"] * 0.8 + verbs * 0.08)

    # 8. Platform fit (tag count + tag length discipline)
    fit = 1.0
    if len(tags) > rules["tags_max"]:
        fit -= 0.3
        tips.append(f"{platform.title()} allows {rules['tags_max']} tags — trim the extras.")
    over = [t for t in tags if len(t) > rules["tag_char_max"]]
    if over:
        fit -= min(0.4, 0.1 * len(over))
        tips.append(f"{len(over)} tag(s) exceed {rules['tag_char_max']} chars for {platform.title()}.")
    if not tags:
        fit = 0.2
        tips.append("No tags supplied — tags drive marketplace search visibility.")
    dims["platform_fit"] = max(0.0, fit)

    # 9. Search intent match (transactional/commercial listings sell PDFs)
    dims["intent_match"] = 1.0 if res["intent"] in ("transactional", "commercial") else 0.55

    # 10. Semantic richness (distinct meaningful tokens across title+desc)
    vocab = set(tokenize(t_low)) | set(tokenize(d_low))
    dims["semantic_richness"] = min(1.0, len(vocab) / 120.0)
    if dims["semantic_richness"] < 0.35:
        tips.append("Vocabulary is narrow — cover formats, audiences, and use-cases naturally.")

    weights = {"keyword_placement": .16, "title_length": .09, "description_length": .09,
               "readability": .08, "ctr_potential": .12, "uniqueness": .10,
               "buyer_intent": .12, "platform_fit": .12, "intent_match": .07,
               "semantic_richness": .05}
    score = round(sum(dims[k] * w for k, w in weights.items()) * 100)
    return {"score": max(0, min(100, score)), "dims": {k: round(v, 2) for k, v in dims.items()},
            "tips": tips[:6], "platform": platform}


def score_all_platforms(listing: dict, focus_keyword: str) -> dict:
    """Score the AI listing against every platform's rules."""
    titles = listing.get("seo_titles") or [""]
    desc_map = listing.get("platform_descriptions") or {}
    tag_map = listing.get("marketplace_tags") or {}
    long_desc = listing.get("long_description", "")
    out = {}
    for platform in PLATFORM_RULES:
        out[platform] = score_listing(
            titles[0], desc_map.get(platform) or long_desc,
            tag_map.get(platform) or listing.get("tags", []),
            focus_keyword, platform, corpus_titles=titles[1:])
    return out
