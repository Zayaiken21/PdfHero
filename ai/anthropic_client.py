"""Anthropic client via plain REST."""
import json
import requests
from core import config


class AnthropicClient:
    name = "anthropic"

    def __init__(self):
        self.key = config.get("ANTHROPIC_API_KEY", "")
        self.model = config.get("ANTHROPIC_MODEL")

    def available(self) -> tuple[bool, str]:
        if not self.key:
            return False, "ANTHROPIC_API_KEY not set"
        return True, f"key set · model {self.model}"

    def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        body = {"model": self.model, "max_tokens": 4000, "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.key,
                     "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            data=json.dumps(body), timeout=120)
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json().get("content", [])
                       if b.get("type") == "text")
