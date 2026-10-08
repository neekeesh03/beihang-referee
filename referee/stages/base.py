from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..context import RunContext
    from ..models import ReviewState

class Stage(ABC):
    stage_id: str
    @abstractmethod
    async def run(self, ctx: "RunContext", state: "ReviewState") -> None:
        raise NotImplementedError
