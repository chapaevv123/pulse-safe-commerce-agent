from __future__ import annotations

import json
import re
from typing import Protocol

import httpx

from .models import CommerceIntent


class IntentInterpreter(Protocol):
    async def parse(self, text: str) -> CommerceIntent: ...


class AIProviderUnavailable(RuntimeError):
    pass


class FixtureInterpreter:
    """Explicit deterministic demo fixture; never represented as a live AI call."""
    async def parse(self, text: str) -> CommerceIntent:
        match = re.search(r"(?:\$|USD\s*)(\d+(?:\.\d{1,2})?)", text, re.I)
        if not match:
            raise ValueError("A USD amount is required")
        purpose = "research report" if "research report" in text.lower() else "sandbox service"
        return CommerceIntent("PAY", match.group(1), "USD", "Sandbox merchant", purpose, .99,
                              ["Recipient is the configured sandbox merchant"], True, "DEMO_FIXTURE")


class OpenAICompatibleInterpreter:
    def __init__(self, api_key: str, base_url: str, model: str, transport=None):
        if not api_key:
            raise AIProviderUnavailable("AI_PROVIDER_UNAVAILABLE")
        self.api_key, self.base_url, self.model, self.transport = api_key, base_url.rstrip("/"), model, transport

    async def parse(self, text: str) -> CommerceIntent:
        prompt = "Return JSON only with action, amount, currency, recipient_label, purpose, confidence, assumptions, requires_owner_approval. Never authorize payment. Request: " + text
        async with httpx.AsyncClient(timeout=15, transport=self.transport) as client:
            response = await client.post(self.base_url + "/chat/completions", headers={"Authorization": "Bearer " + self.api_key},
                                         json={"model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
                                               "messages": [{"role": "system", "content": "You structure commerce intent; you never execute or approve payments."}, {"role": "user", "content": prompt}]})
        if response.status_code != 200:
            raise AIProviderUnavailable("AI_PROVIDER_UNAVAILABLE")
        data = json.loads(response.json()["choices"][0]["message"]["content"])
        return CommerceIntent(**data, provider="OPENAI_COMPATIBLE")
