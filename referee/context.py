from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .config import ReviewConfig
from .providers.base import LLMProvider, SearchProvider
from .runtime.events import EventBus
from .runtime.checkpoint import CheckpointStore
from .runtime.budget import Budget
from .prompting import PromptLibrary

@dataclass(slots=True)
class RunContext:
    config: ReviewConfig
    package_root: Path
    run_dir: Path
    llm: LLMProvider
    search: SearchProvider | None
    events: EventBus
    checkpoints: CheckpointStore
    budget: Budget
    prompts: PromptLibrary
