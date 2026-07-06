"""PDF Hero — Bundle & Product-Line Forge.

Turns ranked real-search ideas into a complete bundle business opportunity:
bundle name options, grouped contents, a pricing ladder, a platform plan,
a launch checklist, and a ready-to-paste listing. Works fully offline via the
template engine; when an AI provider is connected the result gets an extra
polish pass. Every title runs through the same de-dup logic as the rest of
the app, so nothing repeats.
"""
from __future__ import annotations

import time

from core.duplicate_checker import dedupe_rows
from core.title_forge import forge, _smart_case  # reuse casing rules


# ── pricing ──────────────────────────────────────────────────────────
def item_price(score: int) -> float:
    if score >= 85:
        return 9.0
    if score >= 70:
        return 7.0
    if score >= 55:
        return 5.0
    return 4.0


def bundle_price(items: list[dict]) -> tuple[float, float]:
    """(bundle_price, anchor_value). Bundle ≈ 55% of the stack, ends in .99."""
    anchor = sum(item_price(int(r.get("opportunity", 0))) for r in items)
    price = max(9.99, round(anchor * 0.55) - 0.01)
    return price, round(anchor, 2)


# ── bundle builder ───────────────────────────────────────────────────
def build_bundle(selected_rows: list[dict], source_projects: list[str],
                 max_items: int = 8, workspace: str = "") -> dict:
    """Pick the strongest non-duplicate ideas and assemble the bundle."""
    rows = dedupe_rows(list(selected_rows or []))
    rows.sort(key=lambda r: -int(r.get("opportunity", 0)))
    items = rows[:max_items]

    # dominant niche names the bundle
    niches: dict[str, int] = {}
    for r in items:
        n = r.get("niche") or r.get("category") or "PDF"
        niches[n] = niches.get(n, 0) + 1
    dominant = max(niches, key=niches.get) if niches else "PDF"
    theme = _smart_case(dominant)

    names = [
        f"The Complete {theme} Toolkit — {len(items)}-PDF Mega Bundle",
        f"{theme} Power Pack · {len(items)} Printables in One Download",
        f"Everything {theme}: The All-in-One PDF Bundle",
    ]
    # de-dup name words that echo ("PDF PDF")
    seen_names, uniq_names = set(), []
    for n in names:
        key = n.lower()
        if key not in seen_names:
            seen_names.add(key)
            uniq_names.append(n)

    contents = []
    for r in items:
        forged_title = (r.get("pdf_titles") or [None])[0]
        if not forged_title:
            forged_title = forge(r.get("keyword", ""), r.get("category", "General"),
                                 r.get("intent", ""))["pdf_titles"][0]
        contents.append({
            "keyword": r.get("keyword", ""),
            "title": forged_title,
            "category": r.get("category", "General"),
            "niche": r.get("niche", dominant),
            "score": int(r.get("opportunity", 0)),
            "volume_label": r.get("volume_label", ""),
            "solo_price": item_price(int(r.get("opportunity", 0))),
        })

    price, anchor = bundle_price(items)

    # platform plan = most common platforms across items
    plat_counts: dict[str, int] = {}
    for r in items:
        for p in r.get("platforms", []) or []:
            plat_counts[p] = plat_counts.get(p, 0) + 1
    platforms = [p for p, _ in sorted(plat_counts.items(), key=lambda kv: -kv[1])[:4]] \
        or ["Etsy", "Gumroad"]

    # grouped contents by category for a structured "what's inside"
    by_cat: dict[str, list[str]] = {}
    for c in contents:
        by_cat.setdefault(c["category"], []).append(c["title"])

    tags = sorted({w for c in contents for w in c["keyword"].split() if len(w) > 3})[:30]
    tags += [theme.lower(), "bundle", "printable", "instant download", "pdf"]
    tags = list(dict.fromkeys(t.lower() for t in tags))[:40]

    desc = (f"A {theme.lower()} bundle built from {len(items)} of the strongest "
            f"real-search ideas in your research — every file answers a phrase people "
            f"are typing into search right now. Bought separately these would run "
            f"${anchor:.2f}; the bundle delivers the full set in one instant download "
            f"for ${price:.2f}. Print-ready layouts, consistent design, no filler.")

    checklist = [
        f"Design the {len(items)} PDFs with one shared style so the bundle feels like a set",
        "Export print-ready PDFs (US Letter + A4) and one combined bundle file",
        f"List on {platforms[0]} first with the top title, then mirror to "
        + ", ".join(platforms[1:] or ["a second marketplace"]),
        f"Price at ${price:.2f} and show the ${anchor:.2f} separate-value anchor in the description",
        "Use the strongest single PDF as a low-price tripwire that upsells the bundle",
        "Pin 3 mockup images per marketplace listing (cover, inside pages, device mockup)",
        "Revisit Analytics in 2 weeks and refresh titles on anything below the pack average",
    ]

    return {
        "type": "bundle",
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "workspace": workspace,
        "theme": theme,
        "name_options": uniq_names,
        "name": uniq_names[0],
        "items": contents,
        "grouped_contents": by_cat,
        "item_count": len(contents),
        "price": price,
        "anchor_value": anchor,
        "platforms": platforms,
        "tags": tags,
        "description": desc,
        "launch_checklist": checklist,
        "source_projects": source_projects or [],
        "engine": "template",
    }


# ── product line builder ─────────────────────────────────────────────
def build_product_line(theme: str, rows: list[dict]) -> dict:
    """A structured ladder for one niche: free lead magnet -> core products ->
    flagship bundle. Deterministic; AI can polish afterwards."""
    rows = sorted(dedupe_rows(list(rows or [])), key=lambda r: -int(r.get("opportunity", 0)))
    top = rows[:6]
    theme_t = _smart_case(theme)

    def _title(r):
        t = (r.get("pdf_titles") or [None])[0]
        return t or forge(r.get("keyword", ""), r.get("category", "General"))["pdf_titles"][0]

    lead = None
    for r in top:
        if r.get("category") in ("Checklist", "Tracker", "Form / Sheet"):
            lead = r
            break
    lead = lead or (top[0] if top else None)

    core = [r for r in top if r is not lead][:3]
    flagship_price, anchor = bundle_price(top or [])

    line = {
        "type": "product-line",
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "theme": theme_t,
        "line_name": f"The {theme_t} System",
        "lead_magnet": ({"title": _title(lead), "keyword": lead.get("keyword", ""),
                         "price": "Free (email opt-in)",
                         "pitch": "Give away the quick win; it advertises the paid set."}
                        if lead else None),
        "core_products": [{"title": _title(r), "keyword": r.get("keyword", ""),
                           "category": r.get("category", "General"),
                           "price": f"${item_price(int(r.get('opportunity', 0))):.2f}",
                           "score": int(r.get("opportunity", 0))} for r in core],
        "flagship_bundle": {"title": f"The Complete {theme_t} Bundle",
                            "price": f"${flagship_price:.2f}",
                            "anchor": f"${anchor:.2f} value",
                            "contains": [_title(r) for r in top]},
        "pricing_ladder": ["Free lead magnet → builds the list",
                           "Core PDFs $4–$9 → volume sellers",
                           f"Flagship bundle ${flagship_price:.2f} → the real profit line"],
        "launch_order": ["Lead magnet", "Best-scoring core PDF",
                         "Remaining core PDFs (1/week)", "Flagship bundle"],
        "engine": "template",
    }
    return line


# ── optional AI polish ───────────────────────────────────────────────
def ai_polish_bundle(bundle: dict, related: list[str] | None = None) -> tuple[dict, str]:
    """Ask the connected AI provider to sharpen names/description. Safe no-op
    with a message when no provider is available."""
    try:
        from ai import provider as ai_provider
        stat = ai_provider.status()
        if not stat["ok"]:
            return bundle, f"AI provider '{stat['provider']}' unavailable — template engine kept."
        prompt = (
            "Improve this digital PDF bundle listing. Keep it truthful to the given "
            "contents; do not invent files. Return ONLY JSON: "
            '{"name_options": ["3 distinct bundle names, best first"], '
            '"description": "180-320 word original sales description", '
            '"tags": ["25-40 lowercase tags"]}\n\n'
            f"Theme: {bundle.get('theme')}\n"
            f"Contents: {[c['title'] for c in bundle.get('items', [])]}\n"
            f"Bundle price: ${bundle.get('price')} (value ${bundle.get('anchor_value')})\n"
            f"Related search phrases: {', '.join((related or [])[:20])}"
        )
        data = ai_provider.generate_json(prompt, system=(
            "You are an expert e-commerce copywriter for digital PDF bundles. "
            "Original content only. JSON only."))
        if isinstance(data, dict):
            if data.get("name_options"):
                bundle["name_options"] = [str(n) for n in data["name_options"]][:3]
                bundle["name"] = bundle["name_options"][0]
            if data.get("description"):
                bundle["description"] = str(data["description"])
            if data.get("tags"):
                bundle["tags"] = [str(t).lower() for t in data["tags"]][:40]
            bundle["engine"] = f"template + {stat['provider']} polish"
        return bundle, "AI polish applied."
    except Exception as exc:
        return bundle, f"AI polish skipped ({exc.__class__.__name__}) — template engine kept."


def bundle_to_rows(bundle: dict) -> list[dict]:
    """Represent a bundle as rows so it saves/exports like any project."""
    rows = []
    for i, c in enumerate(bundle.get("items", []), 1):
        rows.append({"rank": i, "keyword": c["keyword"],
                     "pdf_titles": [c["title"]],
                     "pdf_description": bundle.get("description", ""),
                     "product_type": "Bundle item",
                     "opportunity": c.get("score", 0),
                     "volume_label": c.get("volume_label", ""),
                     "niche": c.get("niche", bundle.get("theme", "")),
                     "category": c.get("category", "General"),
                     "platforms": bundle.get("platforms", []),
                     "intent": "transactional",
                     "trend_label": "—", "source_count": 0, "sources": []})
    return rows
