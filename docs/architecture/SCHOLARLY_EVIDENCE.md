# Scholarly evidence subsystem

Built-in adapters cover Crossref, OpenAlex, Semantic Scholar, PubMed, arXiv, and Europe PMC. They normalize records into a common schema and can be used through a federated search layer. Deduplication prioritizes DOI identity and falls back to normalized title/year matching. Ranking uses query overlap plus limited citation/recency signals; it does not treat citation count as scientific quality.

Search hits are not automatically evidence. Review stages should distinguish metadata/snippets from opened or fetched source content and retain provider provenance. Network adapters are optional so offline regression tests remain deterministic.
