"""Google Autocomplete — public suggestion endpoint (OpenSearch JSON)."""
from utils.http import get_json, opensearch_list

ENDPOINT = "https://suggestqueries.google.com/complete/search"


def fetch(query: str, lang: str = "en", country: str = "us"):
    obj = get_json(ENDPOINT, params={"client": "firefox", "hl": lang, "gl": country, "q": query})
    return opensearch_list(obj)
