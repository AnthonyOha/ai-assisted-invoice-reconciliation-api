from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass(frozen=True)
class AIResult:
    explanation: str
    confidence: str


class AIClient:
    async def explain_match(self, *, prompt: str) -> AIResult:
        raise NotImplementedError


class DisabledAIClient(AIClient):
    async def explain_match(self, *, prompt: str) -> AIResult:
        raise RuntimeError("AI disabled")


class MockAIClient(AIClient):
    async def explain_match(self, *, prompt: str) -> AIResult:
        # deterministic 'AI-ish' response for local runs
        return AIResult(
            explanation="This match is likely because the amounts align and the transaction timing is close to the invoice. The memo text also overlaps with the invoice description, increasing confidence.",
            confidence="medium",
        )


class OpenAIAIClient(AIClient):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("Missing APP_OPENAI_API_KEY")
        self._key = settings.openai_api_key
        self._base_url = settings.openai_base_url.rstrip("/")
        self._model = settings.openai_model
        self._timeout = settings.ai_timeout_seconds

    async def explain_match(self, *, prompt: str) -> AIResult:
        # Chat Completions-style request (kept minimal).
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "You explain invoice-bank transaction matching decisions. Be concise: 2-6 sentences. Return a confidence label of low|medium|high.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        # naive confidence extraction
        lowered = text.lower()
        conf = "medium"
        if "confidence: high" in lowered or "high confidence" in lowered:
            conf = "high"
        elif "confidence: low" in lowered or "low confidence" in lowered:
            conf = "low"
        return AIResult(explanation=text.strip() or "No explanation returned.", confidence=conf)


def build_ai_client() -> AIClient:
    provider = (settings.ai_provider or "disabled").lower()
    if provider == "openai":
        return OpenAIAIClient()
    if provider == "mock":
        return MockAIClient()
    return DisabledAIClient()
