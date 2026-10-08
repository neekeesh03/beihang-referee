from __future__ import annotations
from .scripted import ScriptedLLMProvider, ScriptedSearchProvider
from .openai_compatible import OpenAICompatibleProvider
from .scholarly_search import FederatedScholarlySearchProvider

class ProviderRegistry:
    def __init__(self):
        self.llm = {"scripted": ScriptedLLMProvider, "openai-compatible": OpenAICompatibleProvider}
        self.search = {"scripted": ScriptedSearchProvider, "federated": FederatedScholarlySearchProvider}
    def register_llm(self, name, factory): self.llm[name] = factory
    def register_search(self, name, factory): self.search[name] = factory
    def llm_names(self): return sorted(self.llm)
    def search_names(self): return sorted(self.search)
