"""Central configuration: .env locally, st.secrets on Streamlit Cloud, sane defaults."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROJECTS_DIR = DATA_DIR / "projects"
CACHE_DIR = DATA_DIR / "cache"
for _d in (PROJECTS_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

_DEFAULTS = {
    "AI_PROVIDER": "ollama",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "OLLAMA_MODEL": "llama3.1",
    "OPENAI_MODEL": "gpt-4o-mini",
    "ANTHROPIC_MODEL": "claude-sonnet-4-6",
    "GEMINI_MODEL": "gemini-2.0-flash",
    "RESPECT_ROBOTS": "true",
    "REQUEST_TIMEOUT": "10",
    "CACHE_TTL_HOURS": "6",
    "RATE_LIMIT_SECONDS": "0.35",
    "MAX_WORKERS": "12",
}


def get(key: str, default: str = None) -> str:
    """Env var -> Streamlit secrets -> built-in default."""
    value = os.getenv(key)
    if value not in (None, ""):
        return value
    try:
        import streamlit as st
        if key in st.secrets:  # type: ignore[operator]
            return str(st.secrets[key])
    except Exception:
        pass
    if default is not None:
        return default
    return _DEFAULTS.get(key, "")


def provider_name() -> str:
    return get("AI_PROVIDER").strip().lower() or "ollama"


def masked(value: str) -> str:
    if not value:
        return "— not set —"
    return value[:4] + "…" + value[-4:] if len(value) > 10 else "•••"


def snapshot() -> dict:
    return {
        "AI_PROVIDER": provider_name(),
        "OLLAMA_BASE_URL": get("OLLAMA_BASE_URL"),
        "OLLAMA_MODEL": get("OLLAMA_MODEL"),
        "OPENAI_MODEL": get("OPENAI_MODEL"),
        "OPENAI_API_KEY": masked(get("OPENAI_API_KEY", "")),
        "ANTHROPIC_MODEL": get("ANTHROPIC_MODEL"),
        "ANTHROPIC_API_KEY": masked(get("ANTHROPIC_API_KEY", "")),
        "GEMINI_MODEL": get("GEMINI_MODEL"),
        "GEMINI_API_KEY": masked(get("GEMINI_API_KEY", "")),
        "RESPECT_ROBOTS": get("RESPECT_ROBOTS"),
    }
