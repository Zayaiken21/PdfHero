"""Prompt templates for the AI SEO generator. Original content only, JSON only."""

SYSTEM_SEO = (
    "You are an expert e-commerce SEO copywriter for digital PDF products "
    "(planners, trackers, worksheets, templates, journals). You write 100% "
    "original content — never copy competitor listings. You respond with ONE "
    "valid JSON object and nothing else: no markdown fences, no commentary."
)


def build_listing_prompt(keyword: str, context: dict | None = None) -> str:
    ctx = context or {}
    extra = ""
    if ctx.get("related"):
        extra += f"\nRelated search phrases (public suggestion data): {', '.join(ctx['related'][:25])}"
    if ctx.get("category"):
        extra += f"\nDetected product category: {ctx['category']}"
    if ctx.get("intent"):
        extra += f"\nDominant search intent: {ctx['intent']}"
    if ctx.get("volume_label"):
        extra += f"\nSearch demand: {ctx['volume_label']}"
    if ctx.get("audience"):
        extra += f"\nTarget audience: {ctx['audience']}"

    return f"""Create a complete, original marketplace listing for a digital PDF product built around the keyword: "{keyword}".{extra}

Return ONLY this JSON object (fill every field, arrays non-empty):
{{
  "seo_titles": ["5 distinct SEO titles, best first, each under 140 chars"],
  "short_description": "150-200 character hook",
  "long_description": "300-800 word original sales description with paragraphs",
  "features": ["8-12 concrete features"],
  "benefits": ["6-10 buyer benefits"],
  "tags": ["30-60 lowercase search tags"],
  "categories": ["2-4 marketplace categories"],
  "marketplace_tags": {{
    "etsy": ["exactly 13 tags, each 20 characters or fewer"],
    "gumroad": ["10-15 tags"],
    "shopify": ["10-20 tags"],
    "ebay": ["10-15 tags"],
    "payhip": ["10-15 tags"]
  }},
  "search_intent": "transactional | commercial | informational",
  "buyer_avatar": "2-3 sentence portrait of the ideal buyer",
  "product_angle": "one sentence unique positioning",
  "difficulty_score": 1,
  "opportunity_explanation": "2-3 sentences on why this can sell",
  "faq": [{{"q": "question", "a": "answer"}}],
  "bundle_ideas": ["3-5 bundle concepts"],
  "upsell_ideas": ["3-5 upsell concepts"],
  "listing_copy": "ready-to-paste listing body with sections",
  "platform_descriptions": {{
    "etsy": "Etsy-optimized description",
    "gumroad": "Gumroad-optimized description",
    "shopify": "Shopify-optimized description",
    "ebay": "eBay-optimized description",
    "payhip": "Payhip-optimized description"
  }},
  "social_caption": "scroll-stopping social media caption with light emoji",
  "pinterest_pin": {{"title": "Pinterest pin title under 100 chars",
                     "description": "Pinterest pin description 200-400 chars with keywords"}}
}}

Rules: difficulty_score is an integer 1-10. Every string is original. Etsy tags MUST be 13 items, each <=20 characters. JSON only."""



def build_product_line_prompt(keyword: str, context: dict | None = None) -> str:
    ctx = context or {}
    extra = f"\nAudience: {ctx['audience']}" if ctx.get("audience") else ""
    return f"""Design a complete digital product line built around the PDF product idea: "{keyword}".{extra}

Return ONLY this JSON object:
{{
  "line_name": "name for the whole product line",
  "starter": {{"title": "entry-level PDF title", "price": "$X", "whats_inside": ["4-6 items"], "pitch": "one sentence"}},
  "premium": {{"title": "premium PDF title", "price": "$X", "whats_inside": ["6-10 items"], "pitch": "one sentence"}},
  "bundle": {{"title": "bundle title", "price": "$X", "contains": ["what it combines"], "pitch": "one sentence"}},
  "upsell": {{"title": "natural upsell", "price": "$X", "why_it_works": "one sentence"}},
  "printable_pack": {{"title": "printable pack title", "price": "$X", "whats_inside": ["4-8 items"]}},
  "editable_template": {{"title": "editable version title", "price": "$X", "editable_in": "e.g. Canva / fillable PDF"}},
  "seasonal_variation": {{"title": "seasonal spin title", "season": "which season/event", "price": "$X"}},
  "launch_order": ["recommended release order of the 7 products"],
  "pricing_strategy": "2-3 sentences on ladder pricing",
  "cross_sell_map": "2-3 sentences on how the products feed each other"
}}

Rules: realistic digital-product prices ($3-$49). Original titles only. JSON only."""
