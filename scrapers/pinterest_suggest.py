"""Pinterest search suggestions — public typeahead; endpoint shape varies, parsed defensively."""
from utils.http import get_json, collect_strings

ENDPOINT = "https://www.pinterest.com/search/suggestions/"


def fetch(query: str, lang: str = "en", country: str = "us"):
    headers = {"Referer": "https://www.pinterest.com/", "Accept": "application/json"}
    obj = get_json(ENDPOINT, params={"q": query, "limit": 10}, headers=headers, retries=0)
    return collect_strings(obj) if obj is not None else []
