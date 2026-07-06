"""Adaptive query reformulation.

Instead of firing one raw query at suggestion engines, we rephrase the seed into
many natural forms real people type — questions, problems, comparisons, buyer
phrasings, and format-specific asks. This pulls far richer, less-duplicated
suggestions from public autocomplete APIs (no bot evasion — just better queries).
"""
from __future__ import annotations

import re
import string

# Question/problem frames — this is what turns "parenting" into the kind of
# real questions PDF buyers search for.
PROBLEM_FRAMES = [
    "how to {s}", "how do i {s}", "why is {s}", "what is the best {s}",
    "best way to {s}", "{s} tips", "{s} for beginners", "{s} step by step",
    "{s} mistakes", "{s} checklist", "{s} guide", "{s} routine",
    "{s} schedule", "{s} plan", "{s} ideas", "{s} examples",
]

# Product/format frames — turns intent into sellable PDF shapes.
FORMAT_FRAMES = [
    "{s} printable", "{s} template", "{s} planner", "{s} tracker",
    "{s} worksheet", "{s} journal", "{s} workbook", "{s} pdf",
    "printable {s}", "editable {s}", "{s} bundle",
]

# Comparison frames surface "x vs y" demand (feature/idea validation).
COMPARE_FRAMES = ["{s} vs", "{s} or", "{s} alternative", "best {s} for"]

_STOP_LEAD = re.compile(r"^(the|a|an|best|top|how to|what is)\s+", re.I)


def _clean_seed(seed: str) -> str:
    seed = (seed or "").strip().lower()
    seed = _STOP_LEAD.sub("", seed)
    return re.sub(r"\s+", " ", seed).strip()


def reformulate(seed: str, depth: str = "standard") -> list[str]:
    """Return an ordered, de-duplicated list of reformulated queries.

    depth: 'quick' (~12), 'standard' (~30), 'deep' (adds a-z + digit tails).
    """
    s = _clean_seed(seed)
    if not s:
        return []
    frames = list(PROBLEM_FRAMES)
    if depth in ("standard", "deep"):
        frames += FORMAT_FRAMES + COMPARE_FRAMES
    queries = [s] + [f.format(s=s) for f in frames]

    if depth == "deep":
        queries += [f"{s} {c}" for c in string.ascii_lowercase]
        queries += [f"{s} {d}" for d in "0123456789"]

    seen, out = set(), []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


# Categories used by automatic discovery, phrased as the problems people search.
DISCOVERY_TOPICS = [
    "budgeting", "meal planning", "adhd focus", "wedding planning",
    "new baby", "potty training", "real estate", "credit repair",
    "small business", "social media", "fitness at home", "weight loss",
    "self care", "productivity", "homeschooling", "teacher lesson",
    "cleaning routine", "travel packing", "gratitude journaling",
    "habit building", "debt payoff", "resume writing", "job interview",
    "side hustle", "digital marketing", "content calendar", "pet care",
    "gardening", "meal prep for busy", "morning routine",
]


def discovery_queries(count: int = 6, audience: str = "",
                      depth: str = "standard") -> tuple[list[str], list[str]]:
    """Pick topics for automatic discovery and reformulate each.
    Returns (queries, topics_used)."""
    import random
    topics = random.sample(DISCOVERY_TOPICS, k=min(count, len(DISCOVERY_TOPICS)))
    if audience:
        topics = [f"{t} for {audience.strip().lower()}" for t in topics]
    queries: list[str] = []
    per = 8 if depth == "quick" else 10
    for t in topics:
        queries += reformulate(t, depth="quick")[:per]
    # de-dup preserving order
    seen, out = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out, topics
