from __future__ import annotations
from typing import Any
from .base import SearchProvider
from ..scholarly import ScholarlyRegistry
from ..scholarly.federated import FederatedScholarSearch
from ..scholarly.http import get_text


class FederatedScholarlySearchProvider(SearchProvider):
    """SearchProvider bridge over Referee's scholarly adapters.

    The normal CLI uses this when literature search is enabled. Search results
    with abstracts expose that abstract as opened retriever content; otherwise
    Referee may fetch the landing page and records whether opening succeeded.
    """
    def __init__(self, provider_names: list[str] | None = None, *, max_concurrency: int = 4):
        registry = ScholarlyRegistry()
        names = provider_names or registry.names()
        self.provider_names = [n for n in names if n in registry.names()]
        self.federated = FederatedScholarSearch([registry.create(n) for n in self.provider_names], max_concurrency=max_concurrency)

    async def search(self, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
        if not self.provider_names:
            return []
        per = max(2, min(limit, 8))
        result = await self.federated.search(query, limit_per_provider=per)
        rows = []
        for r in result.get("records", [])[:limit]:
            row = dict(r)
            abstract = row.get("abstract")
            if abstract:
                row["raw_content"] = abstract
                row["content_status"] = "provided_by_retriever"
            row["federated_provider_status"] = result.get("providers", [])
            rows.append(row)
        return rows

    async def fetch(self, url: str) -> dict[str, Any]:
        text = await get_text(url, timeout=20.0)
        return {"url": url, "raw_content": text[:200000]}
