"""robots.txt compliance for full-page scraping. Suggestion APIs are rate-limited separately."""
import os
import urllib.robotparser
from urllib.parse import urlparse

from utils.cache import cache

USER_AGENT = "PDFSEOIntelBot/1.0 (+keyword research; respects robots.txt)"


def respect_enabled() -> bool:
    return os.getenv("RESPECT_ROBOTS", "true").strip().lower() not in ("false", "0", "no")


def can_fetch(url: str, respect: bool = None) -> bool:
    """True if our bot may fetch this URL. Fails open when robots.txt is unreachable."""
    if respect is None:
        respect = respect_enabled()
    if not respect:
        return True
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = base + "/robots.txt"
        body = cache.get("robots", base)
        if body is None:
            import requests
            try:
                resp = requests.get(robots_url, timeout=6,
                                    headers={"User-Agent": USER_AGENT})
                body = resp.text if resp.status_code == 200 else ""
            except Exception:
                body = ""
            cache.set("robots", base, body, ttl=86400)
        if not body.strip():
            return True
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(body.splitlines())
        return rp.can_fetch(USER_AGENT, url) and rp.can_fetch("*", url) is not False
    except Exception:
        return True
