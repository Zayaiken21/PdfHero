"""Walmart typeahead — public endpoint; frequently bot-guarded, so failures degrade to []."""
from utils.http import get_json, collect_strings

ENDPOINT = "https://www.walmart.com/typeahead/v3/complete"


def fetch(query: str, lang: str = "en", country: str = "us"):
    headers = {"Referer": "https://www.walmart.com/", "Accept": "application/json"}
    obj = get_json(ENDPOINT, params={"term": query}, headers=headers, retries=0)
    return collect_strings(obj) if obj is not None else []
