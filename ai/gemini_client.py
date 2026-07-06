"""Google Gemini client via plain REST."""
import json
import requests
from core import config


class GeminiClient:
    name = "gemini"

    def __init__(self):
        self.key = config.get("GEMINI_API_KEY", "")
        self.model = config.get("GEMINI_MODEL")

    def available(self) -> tuple[bool, str]:
        if not self.key:
            return False, "GEMINI_API_KEY not set"
        return True, f"key set · model {self.model}"

    def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={self.key}")
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        resp = requests.post(url, data=json.dumps(body),
                             headers={"Content-Type": "application/json"}, timeout=120)
        resp.raise_for_status()
        cands = resp.json().get("candidates", [])
        if not cands:
            return ""
        return "".join(p.get("text", "") for p in
                       cands[0].get("content", {}).get("parts", []))
