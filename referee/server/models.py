from __future__ import annotations
try:
    from pydantic import BaseModel, Field
except ImportError:
    BaseModel = object
    def Field(default=None, **kwargs): return default

class PackageInspectRequest(BaseModel):
    paths: list[str]

class RevisionCompareRequest(BaseModel):
    old_path: str
    new_path: str

class RebuttalAuditRequest(BaseModel):
    response_path: str

class ConcernStatusRequest(BaseModel):
    status: str
    note: str = ""

class AddNoteRequest(BaseModel):
    text: str
    author: str = "reviewer"
