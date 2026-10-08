from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class ReviewModeSpec:
    name:str
    description:str
    required_roles:tuple[str,...]
    outputs:tuple[str,...]
    compare_revisions:bool=False
    assess_rebuttal:bool=False
