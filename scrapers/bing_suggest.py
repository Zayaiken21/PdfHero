"""Bing suggestions — public OpenSearch JSON endpoint."""
from utils.http import get_json, opensearch_list

ENDPOINT = "https://api.bing.com/osjson.aspx"


def fetch(query: str, lang: str = "en", country: str = "us"):
    obj = get_json(ENDPOINT, params={"query": query, "language": lang, "market": f"{lang}-{country.upper()}"})
    return opensearch_list(obj)
