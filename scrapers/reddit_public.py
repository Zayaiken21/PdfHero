"""Reddit public data — post titles from the public search JSON API (no login).
Titles feed the NLP pattern miner; they are not autocomplete suggestions."""
from utils.http import get_json

SEARCH = "https://www.reddit.com/search.json"
SUBS = "https://www.reddit.com/api/subreddit_autocomplete_v2.json"
_HEADERS = {"User-Agent": "PDFSEOIntelBot/1.0 (public keyword research)"}


def fetch(query: str, lang: str = "en", country: str = "us", limit: int = 25):
    """Returns public post titles matching the query (past year, by relevance)."""
    obj = get_json(SEARCH, params={"q": query, "limit": limit, "sort": "relevance",
                                   "t": "year", "raw_json": 1}, headers=_HEADERS)
    titles = []
    try:
        for child in obj["data"]["children"]:
            title = child.get("data", {}).get("title")
            if title:
                titles.append(title)
    except Exception:
        pass
    return titles


def subreddits(query: str, limit: int = 8):
    obj = get_json(SUBS, params={"query": query, "limit": limit, "raw_json": 1},
                   headers=_HEADERS)
    names = []
    try:
        for child in obj["data"]["children"]:
            d = child.get("data", {})
            if d.get("display_name_prefixed"):
                names.append({"name": d["display_name_prefixed"],
                              "subscribers": d.get("subscribers", 0),
                              "about": (d.get("public_description") or "")[:140]})
    except Exception:
        pass
    return names
