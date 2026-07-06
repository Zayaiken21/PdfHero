"""Etsy search suggestions — public autocomplete used by the site search box.
Etsy rotates bot protections; failures degrade gracefully to []."""
from utils.http import get_json, collect_strings

ENDPOINT = "https://www.etsy.com/suggestions_ajax.php"


def fetch(query: str, lang: str = "en", country: str = "us"):
    headers = {
        "Referer": "https://www.etsy.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
    }
    obj = get_json(ENDPOINT, params={"search_type": "all", "search_query": query},
                   headers=headers, retries=0)
    return collect_strings(obj) if obj is not None else []
