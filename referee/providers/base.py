from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class LLMRequest:
    operation: str
    system: str
    user: str
    schema: dict[str, Any] | None = None
    model: str | None = None
    temperature: float = 0.0
    request_id: str | None = None
    context_id: str | None = None
    agent_id: str | None = None

class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, request: LLMRequest) -> Any:
        raise NotImplementedError

class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def fetch(self, url: str) -> dict[str, Any]:
        raise NotImplementedError("This search provider does not support fetch")
