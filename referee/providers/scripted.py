from __future__ import annotations
import copy
from typing import Any
from .base import LLMProvider, LLMRequest, SearchProvider

class ScriptedLLMProvider(LLMProvider):
    """Deterministic provider for tests, demos and regression fixtures.

    `responses` maps operation name -> response or list of responses.
    """
    def __init__(self, responses: dict[str, Any] | None = None):
        self.responses = responses or {}
        self.calls: list[LLMRequest] = []
        self._indices: dict[str, int] = {}

    async def complete(self, request: LLMRequest) -> Any:
        self.calls.append(request)
        value = self.responses.get(request.operation)
        if isinstance(value, list):
            idx = self._indices.get(request.operation, 0)
            self._indices[request.operation] = idx + 1
            if not value:
                return {}
            value = value[min(idx, len(value) - 1)]
        if callable(value):
            value = value(request)
        return copy.deepcopy(value if value is not None else {})

class ScriptedSearchProvider(SearchProvider):
    def __init__(self, results: dict[str, list[dict[str, Any]]] | None = None):
        self.results = results or {}
        self.calls: list[str] = []

    async def search(self, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
        self.calls.append(query)
        if query in self.results:
            return copy.deepcopy(self.results[query][:limit])
        return []
