"""DuckDuckGo autocomplete — public JSON endpoint."""
from utils.http import get_json, collect_strings, opensearch_list

ENDPOINT = "https://duckduckgo.com/ac/"


def fetch(query: str, lang: str = "en", country: str = "us"):
    obj = get_json(ENDPOINT, params={"q": query, "kl": f"{country}-{lang}"})
    if obj is None:
        return []
    return opensearch_list(obj) or collect_strings(obj)
