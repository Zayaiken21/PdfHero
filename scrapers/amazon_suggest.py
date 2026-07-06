"""Amazon search suggestions — public completion endpoint used by the search box."""
from utils.http import get_json, collect_strings

ENDPOINT = "https://completion.amazon.com/api/2017/suggestions"


def fetch(query: str, lang: str = "en", country: str = "us"):
    params = {
        "limit": 11, "prefix": query, "suggestion-type": "KEYWORD",
        "alias": "aps", "site-variant": "desktop", "version": 3,
        "event": "onKeyPress", "wc": "", "lop": "en_US",
        "mid": "ATVPDKIKX0DER", "plain-mid": 1, "client-info": "search-ui",
    }
    obj = get_json(ENDPOINT, params=params)
    return collect_strings(obj) if obj is not None else []
