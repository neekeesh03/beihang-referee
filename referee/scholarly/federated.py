from __future__ import annotations
import asyncio
from .dedupe import deduplicate_records
from .ranking import rank_records

class FederatedScholarSearch:
    def __init__(self, providers, *, max_concurrency: int = 4):
        self.providers = list(providers)
        self.max_concurrency = max_concurrency

    async def search(self, query: str, *, limit_per_provider: int = 10, current_year: int | None = None):
        sem = asyncio.Semaphore(self.max_concurrency)
        async def one(provider):
            async with sem:
                try:
                    records = await provider.search(query, limit=limit_per_provider)
                    return {"provider": provider.name, "records": records, "error": None}
                except Exception as exc:
                    return {"provider": getattr(provider, "name", type(provider).__name__), "records": [], "error": f"{type(exc).__name__}: {exc}"}
        batches = await asyncio.gather(*(one(p) for p in self.providers))
        merged = deduplicate_records([r for b in batches for r in b["records"]])
        ranked = rank_records(merged, query, current_year=current_year)
        return {"query": query, "providers": [{"provider": b["provider"], "count": len(b["records"]), "error": b["error"]} for b in batches], "records": [r.to_dict() for r in ranked]}
