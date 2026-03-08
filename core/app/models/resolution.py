from typing import Optional, Literal
from pydantic import BaseModel, Field
from app.models.action_ir import ApprovalRequest, HumanQuestion

ResolutionMode = Literal["AUTO", "CONFIRM", "ASK", "APPROVAL"]


class Resolution(BaseModel):
    mode: ResolutionMode
    resolved_inputs: dict = Field(default_factory=dict)
    question: Optional[HumanQuestion] = None
    approval_request: Optional[ApprovalRequest] = None
    rationale: str = ""
    evidence_map: dict[str, list[str]] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)