"""Rule-based search + buyer intent classification. Deterministic and explainable."""
from utils.text_cleaner import tokenize

TRANSACTIONAL = {"buy", "purchase", "download", "printable", "template", "pdf", "planner",
                 "tracker", "journal", "worksheet", "checklist", "bundle", "editable",
                 "instant", "digital", "kit", "pack", "workbook", "form", "invoice",
                 "contract", "sheet", "sheets", "cards", "labels", "stickers", "svg",
                 "price", "cheap", "shop", "sale", "etsy"}
COMMERCIAL = {"best", "top", "review", "reviews", "vs", "versus", "comparison", "ideas",
              "examples", "alternatives", "cute", "aesthetic", "minimalist"}
INFORMATIONAL = {"how", "what", "why", "when", "where", "guide", "tutorial", "meaning",
                 "definition", "tips", "diy", "learn", "explained"}
BRANDS = {"canva", "pinterest", "amazon", "google", "youtube", "notion", "goodnotes",
          "walmart", "ebay", "gumroad", "shopify"}
FREEBIE = {"free"}


def classify(keyword: str) -> dict:
    """Returns {intent, buyer_intent (0-1), cues}."""
    tokens = tokenize(keyword)
    token_set = set(tokens)
    cues = {
        "transactional": sorted(token_set & TRANSACTIONAL),
        "commercial": sorted(token_set & COMMERCIAL),
        "informational": sorted(token_set & INFORMATIONAL),
    }
    score = 0.30
    score += 0.14 * len(cues["transactional"])
    score += 0.05 * len(cues["commercial"])
    if tokens and tokens[0] in INFORMATIONAL:
        score -= 0.12
    if token_set & FREEBIE:
        score -= 0.15  # freebie seekers convert poorly, though they fit lead magnets
    if token_set & BRANDS and len(token_set - BRANDS) >= 1:
        score += 0.04  # brand qualifier like "canva budget planner" implies product hunting
    buyer = round(max(0.05, min(0.98, score)), 2)

    if len(token_set) <= 2 and token_set <= BRANDS:
        intent = "navigational"
    elif cues["transactional"]:
        intent = "transactional"
    elif cues["commercial"]:
        intent = "commercial"
    elif cues["informational"]:
        intent = "informational"
    else:
        intent = "commercial" if buyer >= 0.45 else "informational"
    return {"intent": intent, "buyer_intent": buyer, "cues": cues}
