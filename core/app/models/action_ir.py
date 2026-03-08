from typing import Optional, Literal, Any
from pydantic import BaseModel, Field

ActionType = Literal["shell", "http", "file_op", "oss_install", "wrapper_gen"]


class ActionItem(BaseModel):
    id: str
    type: ActionType
    target_id: str
    timeout_s: int = 30
    script: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)
    expected_artifacts: list[str] = Field(default_factory=list)


class QuestionChoice(BaseModel):
    value: str
    label: str


class HumanQuestion(BaseModel):
    type: Literal["fact", "policy", "approval", "preference"] = "fact"
    field: str
    text: str
    choices: list[QuestionChoice] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    field: str
    text: str
    risk: str = "high"


class ActionIR(BaseModel):
    actions: list[ActionItem] = Field(default_factory=list)
    resolved_inputs: dict[str, Any] = Field(default_factory=dict)

    # resolved_inputs가 왜 나왔는지, 어떤 evidence를 근거로 했는지
    input_rationales: dict[str, str] = Field(default_factory=dict)
    evidence_map: dict[str, list[str]] = Field(default_factory=dict)

    question: Optional[HumanQuestion] = None
    approval_request: Optional[ApprovalRequest] = None