"""eBay search suggestions — public autosuggest endpoint (JSON/JSONP handled upstream)."""
from utils.http import get_json, collect_strings

ENDPOINT = "https://autosug.ebay.com/autosug"


def fetch(query: str, lang: str = "en", country: str = "us"):
    obj = get_json(ENDPOINT, params={"kwd": query, "sId": 0, "fmt": "json"})
    if obj is None:
        obj = get_json(ENDPOINT, params={"kwd": query, "sId": 0, "fmt": "osr"})
    return collect_strings(obj) if obj is not None else []
