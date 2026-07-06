"""PDF Opportunity Engine — scores every idea across the 11 signals in the spec
and explains why. All scores are estimates derived from public signals."""
import math
import re

from nlp.intent_classifier import classify
from utils.text_cleaner import normalize_keyword, tokenize

WEIGHTS = {
    "search_popularity": 0.12, "trend_growth": 0.10, "buyer_intent": 0.15,
    "pdf_usefulness": 0.12, "printable_fit": 0.07, "marketplace_fit": 0.10,
    "evergreen_value": 0.06, "seasonal_value": 0.04, "competition": 0.09,
    "ease_of_creation": 0.07, "commercial_value": 0.08,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

# (pattern, category, pdf_fit, printable_fit, ease, platforms)
CATEGORY_TABLE = [
    (r"\bplanner|agenda\b", "Planner", 10, 10, 7, ["Etsy", "Shopify", "Gumroad"]),
    (r"\btracker|log\b", "Tracker", 9, 10, 8, ["Etsy", "Gumroad"]),
    (r"\bjournal|diary\b", "Journal", 9, 9, 7, ["Etsy", "Amazon KDP", "Gumroad"]),
    (r"\bworksheet", "Worksheet", 10, 10, 8, ["Teachers Pay Teachers", "Etsy"]),
    (r"\btemplate", "Template", 9, 8, 6, ["Etsy", "Creative Market", "Gumroad"]),
    (r"\bchecklist", "Checklist", 9, 10, 9, ["Etsy", "Gumroad", "Payhip"]),
    (r"\bcalendar", "Calendar", 9, 10, 8, ["Etsy", "Shopify"]),
    (r"\bworkbook", "Workbook", 9, 7, 4, ["Gumroad", "Teachers Pay Teachers", "Payhip"]),
    (r"\bstudy guide|revision|exam|flashcard", "Study Guide", 9, 8, 5, ["Teachers Pay Teachers", "Etsy", "Gumroad"]),
    (r"\bgame|activity|activities|puzzle|coloring", "Kids Activity", 9, 10, 7, ["Etsy", "Teachers Pay Teachers"]),
    (r"\bhomeschool|lesson plan|classroom|teacher", "Teacher Resource", 9, 9, 6, ["Teachers Pay Teachers", "Etsy"]),
    (r"\bbudget|debt|savings|expense|cash envelope|finance", "Budgeting Tool", 9, 9, 7, ["Etsy", "Gumroad", "Shopify"]),
    (r"\bmeal plan|recipe|grocery|pantry", "Meal Planner", 9, 10, 8, ["Etsy", "Gumroad"]),
    (r"\bfitness|workout|gym|running|weight", "Fitness Log", 8, 9, 8, ["Etsy", "Gumroad", "Stan Store"]),
    (r"\bwedding|bridal|bachelorette", "Wedding Planner", 9, 9, 6, ["Etsy", "Shopify"]),
    (r"\bcleaning|chore|declutter", "Cleaning Schedule", 9, 10, 9, ["Etsy", "Gumroad"]),
    (r"\btravel|packing|itinerary|road trip", "Travel Planner", 9, 9, 7, ["Etsy", "Gumroad"]),
    (r"\bself.?care|habit|gratitude|mindfulness|anxiety|adhd|mental", "Wellness Journal", 9, 9, 7, ["Etsy", "Gumroad", "Stan Store"]),
    (r"\binvoice|contract|intake|proposal|onboarding|client", "Business Form", 9, 7, 6, ["Etsy", "Gumroad", "Creative Market"]),
    (r"\bsocial media|content calendar|instagram|tiktok|creator", "Creator Template", 9, 7, 6, ["Stan Store", "Gumroad", "Payhip"]),
    (r"\breal estate|realtor|open house|landlord", "Real Estate Kit", 9, 9, 7, ["Etsy", "Gumroad"]),
    (r"\binvitation|card|label|sticker|sign\b", "Printable Design", 8, 10, 6, ["Etsy", "Creative Market"]),
    (r"\bguide|ebook|handbook|blueprint", "Guide / eBook", 8, 5, 4, ["Gumroad", "Payhip", "Shopify"]),
    (r"\bform\b|\bsheet", "Form / Sheet", 8, 9, 9, ["Etsy", "Gumroad"]),
]

NICHE_PLATFORM_HINTS = [
    (r"teacher|classroom|grade|homeschool|kindergarten", "Teachers Pay Teachers"),
    (r"business|coach|freelance|agency|client", "Gumroad"),
    (r"creator|instagram|tiktok|content", "Stan Store"),
    (r"kids|toddler|children", "Etsy"),
    (r"wedding|party|shower", "Etsy"),
]

SEASONAL_RE = re.compile(
    r"christmas|halloween|easter|valentine|thanksgiving|new year|back to school|"
    r"summer|winter|spring|fall|autumn|advent|graduation|mother'?s day|father'?s day|"
    r"20\d\d", re.I)

NICHE_QUALIFIERS = re.compile(
    r"adhd|homeschool|nurse|teacher|realtor|bride|toddler|senior|small business|"
    r"beginner|couples|kids|christian|vegan|diabetic|postpartum|college", re.I)


def _clamp(x, lo=0.0, hi=10.0):
    return max(lo, min(hi, x))


def detect_category(keyword: str):
    kw = normalize_keyword(keyword)
    for pattern, name, pdf_fit, print_fit, ease, platforms in CATEGORY_TABLE:
        if re.search(pattern, kw):
            platforms = list(platforms)
            for hint_pattern, platform in NICHE_PLATFORM_HINTS:
                if re.search(hint_pattern, kw) and platform not in platforms:
                    platforms.insert(0, platform)
            return {"category": name, "pdf_fit": pdf_fit, "printable_fit": print_fit,
                    "ease": ease, "platforms": platforms[:4]}
    return {"category": "General", "pdf_fit": 5, "printable_fit": 4, "ease": 6,
            "platforms": ["Etsy", "Gumroad"]}


def score_idea(keyword: str, frequency: int = 0, source_count: int = 0,
               best_rank: int = 9, trend: dict = None) -> dict:
    kw = normalize_keyword(keyword)
    intent_info = classify(kw)
    cat = detect_category(kw)
    trend = trend or {"label": "Est. Stable", "slope": 0.0, "estimated": True}

    popularity = _clamp(source_count * 1.5 + min(3.5, math.log1p(max(frequency, 0)) * 1.6)
                        + (1.5 if best_rank <= 2 else 0))
    trend_map = {"Rising": 9.0, "Stable": 6.0, "Declining": 2.5}
    trend_score = trend_map.get(trend.get("label", "").replace("Est. ", ""), 5.5)
    buyer = intent_info["buyer_intent"] * 10

    words = len(tokenize(kw))
    competition_inverse = _clamp({0: 1, 1: 2, 2: 4.5, 3: 6.5}.get(min(words, 4), 8.0)
                                 + (1.5 if NICHE_QUALIFIERS.search(kw) else 0))
    seasonal_hit = bool(SEASONAL_RE.search(kw))
    seasonal_value = 9.0 if seasonal_hit else 3.0
    evergreen_value = 3.5 if seasonal_hit else 8.0

    marketplace_fit = _clamp(5.5 + len(cat["platforms"]) * 1.1
                             + (1.0 if cat["category"] != "General" else -1.0))
    commercial = _clamp(0.55 * buyer + 0.30 * marketplace_fit
                        + (1.2 if cat["printable_fit"] >= 9 else 0))

    subs = {
        "search_popularity": round(popularity, 1),
        "trend_growth": round(trend_score, 1),
        "buyer_intent": round(buyer, 1),
        "pdf_usefulness": float(cat["pdf_fit"]),
        "printable_fit": float(cat["printable_fit"]),
        "marketplace_fit": round(marketplace_fit, 1),
        "evergreen_value": evergreen_value,
        "seasonal_value": seasonal_value,
        "competition": round(competition_inverse, 1),  # higher = easier
        "ease_of_creation": float(cat["ease"]),
        "commercial_value": round(commercial, 1),
    }
    total = round(sum(WEIGHTS[k] * v for k, v in subs.items()) * 10)
    competition_label = ("Low" if competition_inverse >= 7 else
                         "Medium" if competition_inverse >= 4.5 else "High")

    why_bits = []
    if buyer >= 6:
        why_bits.append("searchers use product-style wording, a strong buy signal")
    if cat["category"] != "General":
        why_bits.append(f"{cat['category'].lower()}s translate naturally into printable PDFs")
    if source_count >= 3:
        why_bits.append(f"demand shows up across {source_count} public search sources")
    if trend.get("label") == "Rising":
        why_bits.append("interest is trending upward")
    if competition_label == "Low":
        why_bits.append("long-tail specificity keeps competition manageable")
    if seasonal_hit:
        why_bits.append("seasonal spikes reward early listings")
    why = ("This idea scores well because " + "; ".join(why_bits) + "."
           if why_bits else "A workable idea, though signals are modest — consider a sharper niche angle.")

    return {
        "keyword": kw, "opportunity": int(total), "breakdown": subs,
        "intent": intent_info["intent"], "buyer_intent": intent_info["buyer_intent"],
        "category": cat["category"], "platforms": cat["platforms"],
        "trend_label": trend.get("label", "Est. Stable"),
        "trend_estimated": bool(trend.get("estimated", True)),
        "competition_label": f"{competition_label} (est.)",
        "seasonality": "Seasonal" if seasonal_hit else "Evergreen",
        "frequency": frequency, "source_count": source_count, "why": why,
    }


def enrich_rows(rows, trends: dict = None):
    """Attach scores to fetch_many rows, preserving any extra fields already on
    the row (volume, trend signals, niche, …). trends: optional
    {keyword: trend_dict}; rows carrying trend_label/trend_slope are used too."""
    trends = trends or {}
    out = []
    for row in rows or []:
        trend = trends.get(row["keyword"])
        if trend is None and "trend_label" in row:
            trend = {"label": row.get("trend_label", "Est. Stable"),
                     "slope": row.get("trend_slope", 0.0),
                     "estimated": row.get("estimated", True)}
        scored = score_idea(row["keyword"], frequency=row.get("frequency", 0),
                            source_count=row.get("source_count", 0),
                            best_rank=row.get("best_rank", 9),
                            trend=trend)
        merged = dict(row)
        merged.update(scored)
        merged["sources"] = row.get("sources", [])
        out.append(merged)
    out.sort(key=lambda r: -r["opportunity"])
    from core.title_forge import attach_titles
    return attach_titles(out)
