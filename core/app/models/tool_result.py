from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    ok: bool = True
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    resource_hints: dict = Field(default_factory=dict)
