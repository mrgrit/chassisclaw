from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class ProbeReq(BaseModel):
    target_id: str = Field(..., min_length=1)
    timeout_s: int = 30
    params: Dict[str, Any] = {}

class ProbeRes(BaseModel):
    status: str
    domain: str
    facts: Dict[str, Any] = {}
    rationale: List[str] = []
    evidence_refs: List[str] = []
    unknowns: List[str] = []