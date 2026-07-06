"""PDF Hero — niche taxonomy + live niche demand ranking.

Consistency rule: every automatic discovery flow pulls its queries from ONE
theme at a time, so results never mix unrelated categories (pets stay with
pets, money stays with money).

Demand ranking is built from REAL public autocomplete signals: how many search
engines are actively suggesting a theme's probe phrases right now, how many
distinct suggestions come back, and how high the phrase ranks. Rankings are
cached briefly so repeat scans render instantly.
"""
from __future__ import annotations

from utils.cache import cache

# theme -> icon, probe phrases (demand test), seed phrases (deep dive)
THEMES: dict[str, dict] = {
    "Money & Budgeting": {
        "icon": "💰",
        "probes": ["budget planner printable", "debt payoff tracker"],
        "seeds": ["budget planner", "debt payoff tracker", "savings challenge",
                  "bill tracker", "expense sheet"],
    },
    "Pets": {
        "icon": "🐾",
        "probes": ["pet care planner", "dog training checklist"],
        "seeds": ["pet care planner", "dog training log", "puppy schedule",
                  "pet sitter form", "pet health record"],
    },
    "Kids & Learning": {
        "icon": "🎒",
        "probes": ["kids activity printable", "learning worksheet"],
        "seeds": ["kids activity pages", "alphabet worksheet", "chore chart for kids",
                  "reading log for kids", "kids reward chart"],
    },
    "Teachers & Classroom": {
        "icon": "🍎",
        "probes": ["teacher planner printable", "classroom worksheet"],
        "seeds": ["teacher planner", "lesson plan template", "classroom newsletter",
                  "grade tracker", "sight words worksheet"],
    },
    "Health & Fitness": {
        "icon": "💪",
        "probes": ["workout planner printable", "fitness tracker pdf"],
        "seeds": ["workout log", "meal and fitness planner", "weight loss tracker",
                  "gym planner", "walking challenge"],
    },
    "Food & Meal Prep": {
        "icon": "🍽️",
        "probes": ["meal planner printable", "grocery list template"],
        "seeds": ["meal planner", "grocery list", "recipe card template",
                  "pantry inventory", "freezer meal plan"],
    },
    "Weddings & Events": {
        "icon": "💍",
        "probes": ["wedding planner printable", "party planning checklist"],
        "seeds": ["wedding planning checklist", "wedding budget sheet",
                  "seating chart template", "baby shower games", "party planner"],
    },
    "Small Business": {
        "icon": "💼",
        "probes": ["small business planner", "invoice template pdf"],
        "seeds": ["invoice template", "client intake form", "order form template",
                  "business planner", "price list template"],
    },
    "Content Creators": {
        "icon": "📱",
        "probes": ["content calendar template", "social media planner"],
        "seeds": ["content calendar", "social media planner", "youtube script template",
                  "brand kit template", "engagement tracker"],
    },
    "Real Estate": {
        "icon": "🏡",
        "probes": ["real estate checklist", "open house sign in sheet"],
        "seeds": ["open house sign in sheet", "home buying checklist",
                  "moving checklist", "landlord forms", "realtor marketing template"],
    },
    "Productivity & ADHD": {
        "icon": "🧠",
        "probes": ["adhd planner printable", "daily planner pdf"],
        "seeds": ["adhd daily planner", "habit tracker", "brain dump template",
                  "time blocking planner", "routine chart"],
    },
    "Wellness & Self-Care": {
        "icon": "🌿",
        "probes": ["self care journal printable", "gratitude journal pdf"],
        "seeds": ["self care checklist", "gratitude journal", "anxiety journal",
                  "mood tracker", "sleep tracker"],
    },
    "Home & Cleaning": {
        "icon": "🧹",
        "probes": ["cleaning schedule printable", "home organization checklist"],
        "seeds": ["cleaning schedule", "declutter checklist", "home maintenance log",
                  "laundry room printable", "household binder"],
    },
    "Travel": {
        "icon": "✈️",
        "probes": ["travel planner printable", "packing list template"],
        "seeds": ["packing list", "travel itinerary template", "road trip planner",
                  "travel budget sheet", "vacation countdown"],
    },
    "Job & Career": {
        "icon": "📄",
        "probes": ["resume template pdf", "job application tracker"],
        "seeds": ["resume template", "job application tracker", "interview prep sheet",
                  "cover letter template", "career planner"],
    },
    "Faith & Mindfulness": {
        "icon": "🕊️",
        "probes": ["prayer journal printable", "bible study worksheet"],
        "seeds": ["prayer journal", "bible study guide", "scripture writing plan",
                  "devotional journal", "meditation journal"],
    },
}


def theme_names() -> list[str]:
    return list(THEMES.keys())


def theme_icon(name: str) -> str:
    return THEMES.get(name, {}).get("icon", "⚡")


def theme_queries(name: str, per_seed: int = 6, max_queries: int = 26) -> list[str]:
    """Build a query fan-out that stays INSIDE one theme, so every result in the
    run belongs to the same niche."""
    from core.query_forge import reformulate
    spec = THEMES.get(name)
    if not spec:
        return []
    queries: list[str] = []
    for seed in spec["seeds"]:
        queries.append(seed)
        queries += reformulate(seed, depth="quick")[1:per_seed]
    seen, out = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:max_queries]


def _probe_theme(name: str, gl: str, hl: str) -> dict:
    """Live demand probe for one theme across two fast public sources."""
    from scrapers import fetch
    spec = THEMES[name]
    suggestions: set[str] = set()
    engines_hit = 0
    best_rank = 99
    for probe in spec["probes"]:
        for src in ("google", "bing"):
            got = fetch(src, probe, lang=hl, country=gl) or []
            if got:
                engines_hit += 1
                best_rank = min(best_rank, 0)
            for i, s in enumerate(got):
                suggestions.add(s.lower())
                if i == 0:
                    best_rank = 0
    score = len(suggestions) * 2 + engines_hit * 5 + (8 if best_rank == 0 else 0)
    sample = sorted(suggestions)[:6]
    return {"name": name, "icon": spec["icon"], "score": score,
            "suggestions": len(suggestions), "sample": sample}


def rank_themes(country: str = "United States", limit: int = 10,
                progress_cb=None, ttl_hours: float = 6.0) -> list[dict]:
    """Rank every theme by live search-suggestion demand for a country.
    Cached so a repeat scan is instant; progress reflects real fetches only."""
    from core import geo as geo_mod
    g = geo_mod.resolve(country)
    cache_key = f"{g['gl']}"
    hit = cache.get("theme-rank", cache_key)
    if hit:
        if progress_cb:
            progress_cb(len(THEMES), len(THEMES), "loaded from fresh cache")
        return hit[:limit]

    ranked: list[dict] = []
    names = theme_names()
    for i, name in enumerate(names):
        try:
            ranked.append(_probe_theme(name, g["gl"], g["hl"]))
        except Exception:
            ranked.append({"name": name, "icon": theme_icon(name), "score": 0,
                           "suggestions": 0, "sample": []})
        if progress_cb:
            progress_cb(i + 1, len(names), name)
    ranked.sort(key=lambda t: -t["score"])
    for i, t in enumerate(ranked, 1):
        t["rank"] = i
    cache.set("theme-rank", cache_key, ranked, ttl=int(ttl_hours * 3600))
    return ranked[:limit]


def match_theme(text: str) -> str:
    """Best-effort mapping of an arbitrary phrase to a theme (for grouping)."""
    low = (text or "").lower()
    best, best_hits = "", 0
    for name, spec in THEMES.items():
        hits = sum(1 for seed in spec["seeds"] for w in seed.split() if w in low)
        if hits > best_hits:
            best, best_hits = name, hits
    return best
