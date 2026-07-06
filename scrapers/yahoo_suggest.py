"""Yahoo search suggestions — public 'gossip' endpoint (shape varies; parsed defensively)."""
from utils.http import get_json, collect_strings

ENDPOINT = "https://search.yahoo.com/sugg/gossip/gossip-us-ura/"


def fetch(query: str, lang: str = "en", country: str = "us"):
    obj = get_json(ENDPOINT, params={"output": "sd1", "command": query, "nresults": 10})
    return collect_strings(obj) if obj is not None else []
