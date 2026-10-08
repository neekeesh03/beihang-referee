# Provider development

LLM, generic web-search, and scholarly-search providers are intentionally separate. A new LLM provider implements `LLMProvider.complete`. A generic search provider implements `SearchProvider.search` and optionally `fetch`. Scholarly providers return normalized `ScholarlyRecord` objects.

The plugin registry also exposes entry-point groups for LLMs, search backends, scholarly providers, and custom stages, allowing external packages to extend the platform without editing the scientific kernel.
