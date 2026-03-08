from typing import Any
from pydantic import BaseModel, Field


class PlaybookIR(BaseModel):
    goal: str
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)

    # 입력 상태
    inputs: dict[str, Any] = Field(default_factory=dict)
    unknowns: list[str] = Field(default_factory=list)

    # 입력 확정 근거
    input_rationales: dict[str, str] = Field(default_factory=dict)
    evidence_map: dict[str, list[str]] = Field(default_factory=dict)

    # 사람 응답/승인 상태
    answers: dict[str, Any] = Field(default_factory=dict)
    approvals: dict[str, Any] = Field(default_factory=dict)

    # 실행/판단 흔적
    probes: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)

    # 이후 확장 대비
    candidate_playbooks: list[str] = Field(default_factory=list)
    plan: dict[str, Any] = Field(default_factory=lambda: {"jobs": [], "steps": []})
    validation_rules: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    fixes: list[dict[str, Any]] = Field(default_factory=list)
    replans: list[dict[str, Any]] = Field(default_factory=list)

    iterations: int = 0