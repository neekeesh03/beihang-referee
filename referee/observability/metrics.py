from dataclasses import dataclass,field,asdict
@dataclass
class RunMetrics:
    stage_durations_s:dict[str,float]=field(default_factory=dict)
    llm_calls:int=0
    search_calls:int=0
    admitted:int=0
    rejected:int=0
    warnings:int=0
    def to_dict(self):return asdict(self)
