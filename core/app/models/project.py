from typing import Any
from pydantic import BaseModel, Field

class CreateProjectReq(BaseModel):
    name: str
    request_text: str
    target_ids: list[str] = Field(default_factory=list)

class ProjectState(BaseModel):
    id: str
    name: str
    request_text: str
    status: str = "created"
    stage: str = "plan"
    target_ids: list[str] = Field(default_factory=list)
    answers: dict[str, Any] = Field(default_factory=dict)
    approvals: dict[str, Any] = Field(default_factory=dict)
    plan_ir: dict[str, Any] = Field(default_factory=dict)
    resolution: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
