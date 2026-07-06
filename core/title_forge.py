"""Title & description forge — turn a real search phrase into a concrete,
sellable PDF product: 3 unique titles + a structured, meaningful description
that tells you what the guide/journal/planner would actually contain.

Design goals:
  • Every title/description is built from LOGIC, not filler: the search phrase,
    its detected category, the audience, the buyer intent, and the format.
  • No duplicate titles across a result set (global de-dup pass).
  • No word bleeding / repetition inside a single title.
  • Reads like a product a person would pay for — not stale copy-cat text.
"""
from __future__ import annotations

import re

# ── casing helpers ───────────────────────────────────────────────────
_ACRONYMS = {"adhd": "ADHD", "pdf": "PDF", "seo": "SEO", "diy": "DIY",
             "cdl": "CDL", "hr": "HR", "sat": "SAT", "act": "ACT",
             "iep": "IEP", "llc": "LLC", "irs": "IRS", "faq": "FAQ",
             "adr": "ADR", "ai": "AI", "usa": "USA", "uk": "UK"}
_LOWER = {"for", "and", "the", "to", "of", "a", "in", "with", "your"}

_STRIP = re.compile(
    r"\b(best|top|free|good|great|how\s+to|how\s+do\s+i|what\s+is|what\s+are|"
    r"why\s+is|ways?\s+to|ideas?|tips?|advice|guide|pdf|printable|template|"
    r"download|online|near\s+me|step\s+by\s+step|\d{4})\b", re.I)


def _smart_case(text: str) -> str:
    words = (text or "").split()
    out = []
    for i, w in enumerate(words):
        low = w.lower()
        if low in _ACRONYMS:
            out.append(_ACRONYMS[low])
        elif i > 0 and low in _LOWER:
            out.append(low)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def _dedupe_words(text: str) -> str:
    """Remove immediate/again-repeated words so titles never bleed the same word."""
    seen_adjacent = None
    seen = set()
    out = []
    for w in text.split():
        key = re.sub(r"[^a-z]", "", w.lower())
        if key and key == seen_adjacent:
            continue
        if key and key in seen and key not in _LOWER and len(key) > 3:
            continue
        out.append(w)
        seen_adjacent = key
        if key:
            seen.add(key)
    return " ".join(out)


def _tidy(text: str) -> str:
    """Strip dangling separators/spaces left after word de-duplication."""
    import re as _re
    text = _re.sub(r"\s*[·,\-]\s*$", "", text).strip()
    text = _re.sub(r"\s{2,}", " ", text)
    text = _re.sub(r"\(\s+", "(", text)
    return text


def _split_audience(keyword: str) -> tuple[str, str]:
    kw = (keyword or "").lower()
    m = re.search(r"\bfor ([a-z][a-z ]{1,25})$", kw)
    if m:
        return kw[:m.start()].strip(), _smart_case(m.group(1).strip())
    return kw, ""


def _core_topic(keyword: str) -> str:
    cleaned = _STRIP.sub(" ", keyword or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return _smart_case(cleaned or keyword or "PDF Product")


# ── category → product framing ───────────────────────────────────────
# noun = product noun; inside = concrete sections the PDF would contain;
# verb = what the buyer does with it; qualities = format descriptors.
CATEGORY_SPEC = {
    "Planner": dict(noun="Planner",
                    inside=["daily & weekly layouts", "monthly overview spreads",
                            "goal-setting pages", "priority and to-do sections"],
                    verb="plan and organize", qualities=["Undated", "Print-at-Home", "A4 · A5 · Letter"]),
    "Tracker": dict(noun="Tracker",
                    inside=["at-a-glance tracking grids", "progress charts",
                            "streak logs", "monthly review pages"],
                    verb="track progress on", qualities=["Minimalist", "Printable", "Instant Download"]),
    "Journal": dict(noun="Journal",
                    inside=["guided daily prompts", "reflection pages",
                            "weekly check-ins", "milestone spreads"],
                    verb="reflect on", qualities=["Guided", "Printable", "Daily & Weekly Pages"]),
    "Worksheet": dict(noun="Worksheet Pack",
                      inside=["step-by-step exercises", "practice pages",
                              "answer keys", "quick-review sheets"],
                      verb="practice", qualities=["Printable", "with Answer Keys", "Classroom-Ready"]),
    "Template": dict(noun="Template",
                     inside=["fill-in-the-blank fields", "ready-to-edit sections",
                             "example entries", "a quick-start guide"],
                     verb="fill in and reuse", qualities=["Editable", "Fill & Print", "Professional Layout"]),
    "Checklist": dict(noun="Checklist",
                      inside=["step-by-step checkpoints", "do-not-forget lists",
                              "a one-page quick guide", "notes column"],
                      verb="work through", qualities=["Printable", "One-Page", "Step-by-Step"]),
    "Calendar": dict(noun="Calendar",
                     inside=["monthly calendar spreads", "weekly planning grids",
                             "important-dates pages", "notes sections"],
                     verb="schedule with", qualities=["Printable", "Monthly & Weekly", "Minimal Design"]),
    "Workbook": dict(noun="Workbook",
                     inside=["guided lessons", "hands-on exercises",
                             "progress checkpoints", "reflection prompts"],
                     verb="learn", qualities=["Guided", "Printable", "Self-Paced"]),
    "Study guide": dict(noun="Study Guide",
                        inside=["condensed exam notes", "practice questions",
                                "quick-review sheets", "memory aids"],
                        verb="study for", qualities=["Exam-Ready", "Printable", "Quick-Review"]),
    "Form": dict(noun="Form Pack",
                 inside=["client-ready fields", "intake sections",
                         "signature blocks", "a usage guide"],
                 verb="collect information for", qualities=["Editable", "Client-Ready", "Professional"]),
    "Game": dict(noun="Printable Game Pack",
                 inside=["print-and-play cards", "game boards",
                         "rules sheet", "score trackers"],
                 verb="play", qualities=["Print & Play", "Party-Ready", "Instant Download"]),
}
_GENERIC = dict(noun="Guide",
                inside=["a clear step-by-step framework", "checklists and worksheets",
                        "real examples", "quick-reference cheat sheets"],
                verb="master", qualities=["Printable", "Beginner-Friendly", "Instant Download"])

_HOOKS = ["Ultimate", "Complete", "Essential", "Simple", "Smart",
          "Everyday", "No-Stress", "Step-by-Step"]


def _pick(seq, seed_text):
    return seq[sum(map(ord, seed_text)) % len(seq)]


def forge(keyword: str, category: str = "General", intent: str = "informational",
          related: list[str] | None = None, audience_override: str = "") -> dict:
    """Return {product_type, pdf_titles:[3], pdf_description, whats_inside:[...]}."""
    core_kw, audience = _split_audience(keyword)
    audience = audience or _smart_case(audience_override)
    topic = _core_topic(core_kw)
    spec = CATEGORY_SPEC.get(category, _GENERIC)
    noun = spec["noun"]
    who = f" for {audience}" if audience else ""
    who_lead = f"{audience} " if audience else ""

    # product phrase without word bleed (e.g. avoid "Planner Planner")
    if noun.split()[0].lower() in topic.lower():
        product = topic
    else:
        product = f"{topic} {noun}"
    product = _dedupe_words(product)
    q = spec["qualities"]

    # product is already de-duplicated; keep quality descriptors intact so words
    # like "Daily"/"Weekly" survive even if they echo the topic.
    titles = [
        _tidy(f"{product}{who} — {q[0]} PDF, {q[1]}"),
        _tidy(f"The {_pick(_HOOKS, keyword)} {who_lead}{product} · {q[2]}"),
        _tidy(f"{product}{who} — Printable PDF Bundle (Instant Download)"),
    ]
    if intent == "transactional" and "editable" not in titles[0].lower() \
            and "fill" not in titles[0].lower():
        titles[0] += " · Editable"

    # ── structured description (real logic) ──────────────────────────
    inside = spec["inside"]
    # weave 1–2 distinct related sub-terms in, if they add signal
    extras = []
    for r in (related or []):
        rt = _core_topic(r)
        if rt and rt.lower() not in topic.lower() and rt.lower() not in " ".join(extras).lower():
            extras.append(rt.lower())
        if len(extras) >= 2:
            break

    aud_clause = f" made for {audience.lower()}" if audience else ""
    inside_clause = (", ".join(inside[:3]) + f", and {inside[3]}") if len(inside) > 3 else ", ".join(inside)
    extra_clause = (f" It naturally extends into {extras[0]}" +
                    (f" and {extras[1]}" if len(extras) > 1 else "") + ".") if extras else ""
    intent_clause = {
        "transactional": "Searchers here are ready to buy a done-for-you solution, so an "
                         "instant-download, print-ready file converts especially well.",
        "commercial": "Shoppers are comparing options and want a polished, ready-to-use file, so "
                     "positioning it as the complete no-setup option wins the sale.",
        "informational": "People want a clear answer they can act on, so packaging the know-how "
                        "as a printable they keep and reuse gives it lasting value.",
    }.get(intent, "It packages in-demand know-how into a printable people keep and reuse.")

    q0 = spec["qualities"][0].lower()
    article = "An" if q0[:1] in "aeiou" else "A"
    description = _dedupe_sentence_words(
        f"{article} {q0} {noun.lower()} built around the topic \u201c{topic}\u201d{aud_clause}, "
        f"designed to be genuinely usable from the first print. "
        f"Inside you get {inside_clause}.{extra_clause} {intent_clause}"
    )

    return {"product_type": noun,
            "pdf_titles": titles,
            "pdf_description": description,
            "whats_inside": inside}


def _dedupe_sentence_words(text: str) -> str:
    """Collapse accidental triple-repeats of a content word in a sentence."""
    counts: dict[str, int] = {}
    out = []
    for w in text.split():
        key = re.sub(r"[^a-z]", "", w.lower())
        if key and len(key) > 4:
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > 3:
                continue
        out.append(w)
    return " ".join(out)


def attach_titles(rows: list[dict]) -> list[dict]:
    """Attach titles + descriptions to every row, guaranteeing no duplicate
    primary title across the whole set (append a distinguishing tail if needed)."""
    used: set[str] = set()
    related_pool = [r.get("keyword", "") for r in (rows or [])[:20]]
    for row in rows or []:
        forged = forge(row.get("keyword", ""), row.get("category", "General"),
                       row.get("intent", ""), related=related_pool)
        primary = forged["pdf_titles"][0]
        if primary.lower() in used:
            # differentiate by category/audience so no two are identical
            tag = row.get("category", "PDF")
            forged["pdf_titles"][0] = _dedupe_words(f"{primary} · {tag} Edition")
        used.add(forged["pdf_titles"][0].lower())
        row.update(forged)
    return rows
