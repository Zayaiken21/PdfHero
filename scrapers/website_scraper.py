"""Public web page extractor. Respects robots.txt, rate limits, and never touches
login-only content, CAPTCHAs, or paywalls (it simply fails politely on those)."""
import json
import re
from urllib.parse import urljoin, urlparse

from utils.http import get_text
from utils.robots import can_fetch
from utils.text_cleaner import clean_text

MAX_PARAGRAPHS = 120
MAX_LIST_ITEMS = 120


def scrape(url: str, respect_robots: bool = None) -> dict:
    """Extract SEO-relevant content from a single public page.

    Returns a dict with: ok, error, and the fields listed in the product spec
    (title, meta, headings, paragraphs, lists, tables, alt text, captions,
    schema.org / JSON-LD, Open Graph, FAQ, internal links).
    """
    result = {"ok": False, "url": url, "error": ""}
    if not re.match(r"^https?://", url or ""):
        result["error"] = "URL must start with http:// or https://"
        return result
    if not can_fetch(url, respect_robots):
        result["error"] = "Blocked by robots.txt — this page asked bots not to crawl it."
        return result

    html_text = get_text(url, ttl=3600)
    if html_text is None:
        result["error"] = "Page could not be fetched (blocked, offline, or requires login)."
        return result

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "lxml")
    except Exception:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        if tag.name == "script" and tag.get("type") == "application/ld+json":
            continue
        if tag.name == "script":
            tag_type = tag.get("type", "")
            if tag_type != "application/ld+json":
                tag.decompose()
        else:
            tag.decompose()

    def texts(selector, limit=60):
        return [clean_text(el.get_text(" ")) for el in soup.select(selector)[:limit]
                if clean_text(el.get_text(" "))]

    meta = {}
    for m in soup.find_all("meta"):
        key = m.get("name") or m.get("property") or ""
        content = m.get("content") or ""
        if key and content:
            meta[key.lower()] = clean_text(content)

    og = {k.replace("og:", ""): v for k, v in meta.items() if k.startswith("og:")}

    json_ld, faq = [], []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        json_ld.append(data)
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict) and node.get("@type") in ("FAQPage",):
                for q in node.get("mainEntity", []) or []:
                    question = clean_text(q.get("name", ""))
                    answer = ""
                    acc = q.get("acceptedAnswer") or {}
                    if isinstance(acc, dict):
                        answer = clean_text(acc.get("text", ""))
                    if question:
                        faq.append({"q": question, "a": answer})

    # Heuristic FAQ: question-style headings followed by a paragraph
    if not faq:
        for h in soup.select("h2, h3, h4"):
            heading = clean_text(h.get_text(" "))
            if heading.endswith("?") and 10 < len(heading) < 160:
                sibling = h.find_next(["p", "div"])
                answer = clean_text(sibling.get_text(" "))[:400] if sibling else ""
                faq.append({"q": heading, "a": answer})
        faq = faq[:15]

    tables = []
    for table in soup.find_all("table")[:6]:
        rows = []
        for tr in table.find_all("tr")[:25]:
            cells = [clean_text(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)

    domain = urlparse(url).netloc
    internal_links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        if urlparse(href).netloc == domain and href not in seen and "#" not in href:
            seen.add(href)
            internal_links.append({"url": href, "text": clean_text(a.get_text(" "))[:80]})
        if len(internal_links) >= 40:
            break

    result.update({
        "ok": True,
        "title": clean_text(soup.title.get_text()) if soup.title else "",
        "meta_description": meta.get("description", ""),
        "meta_keywords": meta.get("keywords", ""),
        "canonical": (soup.find("link", rel="canonical") or {}).get("href", ""),
        "h1": texts("h1", 10),
        "h2": texts("h2", 40),
        "h3": texts("h3", 60),
        "h4": texts("h4", 60),
        "paragraphs": texts("p", MAX_PARAGRAPHS),
        "list_items": texts("li", MAX_LIST_ITEMS),
        "tables": tables,
        "image_alt": [clean_text(img.get("alt", "")) for img in soup.find_all("img")
                      if clean_text(img.get("alt", ""))][:60],
        "captions": texts("figcaption", 30),
        "open_graph": og,
        "json_ld": json_ld[:5],
        "faq": faq,
        "internal_links": internal_links,
    })
    return result


def combined_text(page: dict) -> str:
    """Flatten a scraped page into one analysis-ready text blob."""
    parts = [page.get("title", ""), page.get("meta_description", ""), page.get("meta_keywords", "")]
    for key in ("h1", "h2", "h3", "h4", "paragraphs", "list_items", "image_alt", "captions"):
        parts.extend(page.get(key, []) or [])
    for item in page.get("faq", []) or []:
        parts.extend([item.get("q", ""), item.get("a", "")])
    return "\n".join(p for p in parts if p)
