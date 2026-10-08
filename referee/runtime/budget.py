from __future__ import annotations
from dataclasses import dataclass

class BudgetExceeded(RuntimeError):
    pass

@dataclass
class Budget:
    llm_calls_max: int = 200
    search_calls_max: int = 100
    llm_calls: int = 0
    search_calls: int = 0

    def consume_llm(self, n: int = 1) -> None:
        self.llm_calls += n
        if self.llm_calls > self.llm_calls_max:
            raise BudgetExceeded("LLM call budget exceeded")

    def consume_search(self, n: int = 1) -> None:
        self.search_calls += n
        if self.search_calls > self.search_calls_max:
            raise BudgetExceeded("Search call budget exceeded")
