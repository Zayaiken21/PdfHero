"""Provider factory + robust JSON generation for the AI SEO layer."""
from __future__ import annotations

import json
import re

from core import config


class ProviderError(RuntimeError):
    pass


def get_provider():
    name = config.provider_name()
    if name == "openai":
        from ai.openai_client import OpenAIClient
        return OpenAIClient()
    if name == "anthropic":
        from ai.anthropic_client import AnthropicClient
        return AnthropicClient()
    if name == "gemini":
        from ai.gemini_client import GeminiClient
        return GeminiClient()
    from ai.ollama_client import OllamaClient
    return OllamaClient()


def status() -> dict:
    provider = get_provider()
    ok, detail = provider.available()
    return {"provider": provider.name, "ok": ok, "detail": detail}


def test_call() -> tuple[bool, str]:
    try:
        provider = get_provider()
        out = provider.generate("Reply with the single word: ready", temperature=0.0)
        return True, (out or "").strip()[:80] or "(empty reply)"
    except Exception as exc:
        return False, f"{exc.__class__.__name__}: {exc}"


def generate(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    try:
        return get_provider().generate(prompt, system=system, temperature=temperature)
    except Exception as exc:
        raise ProviderError(str(exc)) from exc


def extract_json(text: str):
    """Best-effort JSON extraction: strip fences, slice first {...} span,
    repair trailing commas."""
    if not text:
        raise ProviderError("Empty AI response")
    cleaned = re.sub(r"```(?:json)?", "", text).strip("` \n\r\t")
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ProviderError("No JSON object found in AI response")
    blob = cleaned[start:end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*([}\]])", r"\1", blob)
        return json.loads(repaired)


def generate_json(prompt: str, system: str = "", temperature: float = 0.7):
    """Generate + parse JSON; one automatic low-temperature retry on failure."""
    provider = get_provider()
    kwargs = {"system": system, "temperature": temperature}
    if provider.name == "openai":
        kwargs["json_mode"] = True
    try:
        return extract_json(provider.generate(prompt, **kwargs))
    except Exception:
        kwargs["temperature"] = 0.2
        retry_prompt = prompt + "\n\nIMPORTANT: Output ONLY the JSON object. No prose, no markdown."
        try:
            return extract_json(provider.generate(retry_prompt, **kwargs))
        except Exception as exc:
            raise ProviderError(f"AI did not return valid JSON: {exc}") from exc
