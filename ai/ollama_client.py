"""Ollama client — local or external VPS via OLLAMA_BASE_URL."""
import json
import requests
from core import config


class OllamaClient:
    name = "ollama"

    def __init__(self):
        self.base = config.get("OLLAMA_BASE_URL").rstrip("/")
        self.model = config.get("OLLAMA_MODEL")

    def available(self) -> tuple[bool, str]:
        try:
            resp = requests.get(f"{self.base}/api/tags", timeout=4)
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            return True, f"{len(models)} model(s): {', '.join(models[:4])}"
        except Exception as exc:
            return False, f"Ollama unreachable at {self.base} ({exc.__class__.__name__})"

    def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        resp = requests.post(
            f"{self.base}/api/chat",
            data=json.dumps({"model": self.model, "messages": messages,
                             "stream": False, "options": {"temperature": temperature}}),
            headers={"Content-Type": "application/json"}, timeout=180)
        resp.raise_for_status()
        return (resp.json().get("message") or {}).get("content", "")
