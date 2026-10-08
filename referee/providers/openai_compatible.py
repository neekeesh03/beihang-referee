from __future__ import annotations
import json
import os
import urllib.request
import re
from typing import Any
from .base import LLMProvider, LLMRequest

class OpenAICompatibleProvider(LLMProvider):
    """Small dependency-free adapter for OpenAI-compatible chat APIs.

    It intentionally implements only the transport boundary. Scientific policy,
    schemas and retry behavior stay in Referee.
    """
    def __init__(self, *, base_url: str | None = None, api_key: str | None = None, default_model: str | None = None):
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.default_model = default_model or os.getenv("REFEREE_MODEL")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAICompatibleProvider")

    async def complete(self, request: LLMRequest) -> Any:
        model = request.model if request.model not in (None, "", "host-default") else self.default_model
        if not model:
            raise ValueError("A model identifier is required; pass --model or set REFEREE_MODEL")
        payload: dict[str, Any] = {
            "model": model,
            "temperature": request.temperature,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
        }
        if request.schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": re.sub(r"[^A-Za-z0-9_-]+", "_", request.operation)[:64] or "referee_output", "schema": request.schema, "strict": True},
            }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        # Network I/O is kept synchronous inside this minimal adapter to avoid a
        # mandatory HTTP dependency. Production hosts may replace this provider.
        import asyncio
        raw = await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=120).read())
        data = json.loads(raw)
        text = data["choices"][0]["message"]["content"]
        try:
            return json.loads(text)
        except Exception:
            return text
