"""OpenAI client via plain REST."""
import json
import requests
from core import config


class OpenAIClient:
    name = "openai"

    def __init__(self):
        self.key = config.get("OPENAI_API_KEY", "")
        self.model = config.get("OPENAI_MODEL")

    def available(self) -> tuple[bool, str]:
        if not self.key:
            return False, "OPENAI_API_KEY not set"
        return True, f"key set · model {self.model}"

    def generate(self, prompt: str, system: str = "", temperature: float = 0.7,
                 json_mode: bool = False) -> str:
        body = {
            "model": self.model, "temperature": temperature,
            "messages": ([{"role": "system", "content": system}] if system else [])
                        + [{"role": "user", "content": prompt}],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.key}",
                     "Content-Type": "application/json"},
            data=json.dumps(body), timeout=120)
        if resp.status_code == 400 and json_mode:
            body.pop("response_format", None)
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.key}",
                         "Content-Type": "application/json"},
                data=json.dumps(body), timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
