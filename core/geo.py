"""Country / geo support — one place that maps friendly names to the codes each
data source expects (autocomplete gl, Google Trends geo, language)."""
from __future__ import annotations

# name -> (trends_geo, suggest_country(gl), language(hl))
COUNTRIES = {
    "Worldwide":       ("",   "us", "en"),
    "United States":   ("US", "us", "en"),
    "United Kingdom":  ("GB", "gb", "en"),
    "Canada":          ("CA", "ca", "en"),
    "Australia":       ("AU", "au", "en"),
    "Ireland":         ("IE", "ie", "en"),
    "New Zealand":     ("NZ", "nz", "en"),
    "India":           ("IN", "in", "en"),
    "South Africa":    ("ZA", "za", "en"),
    "Germany":         ("DE", "de", "de"),
    "France":          ("FR", "fr", "fr"),
    "Spain":           ("ES", "es", "es"),
    "Italy":           ("IT", "it", "it"),
    "Netherlands":     ("NL", "nl", "nl"),
    "Mexico":          ("MX", "mx", "es"),
    "Brazil":          ("BR", "br", "pt"),
    "Philippines":     ("PH", "ph", "en"),
}

DEFAULT = "United States"


def resolve(name: str) -> dict:
    geo, gl, hl = COUNTRIES.get(name, COUNTRIES[DEFAULT])
    return {"name": name if name in COUNTRIES else DEFAULT,
            "trends_geo": geo, "gl": gl, "hl": hl}


def names() -> list[str]:
    return list(COUNTRIES.keys())
