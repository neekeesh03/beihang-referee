from __future__ import annotations
from dataclasses import dataclass,asdict,field
from abc import ABC,abstractmethod
from typing import Any
@dataclass
class ScholarlyRecord:
    title:str; year:int|None=None; doi:str|None=None; url:str|None=None; authors:list[str]=field(default_factory=list); abstract:str|None=None; venue:str|None=None; provider:str=''; citation_count:int|None=None; identifiers:dict[str,str]=field(default_factory=dict); raw:dict[str,Any]=field(default_factory=dict)
    def to_dict(self):return asdict(self)
class ScholarlyProvider(ABC):
    name='base'
    @abstractmethod
    async def search(self,query:str,*,limit:int=10)->list[ScholarlyRecord]:...
    async def get(self,identifier:str)->ScholarlyRecord|None:return None
