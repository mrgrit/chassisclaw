from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class RunScriptReq(BaseModel):
    run_id: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)
    script: str = Field(..., min_length=1)
    timeout_s: int = 60
    approval_required: bool = False
    evidence_requests: List[Dict[str, Any]] = []