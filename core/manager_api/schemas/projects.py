from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CreateProjectReq(BaseModel):
    name: str = Field(..., min_length=1)
    request_text: str = Field(default="", description="user goal in natural language")

class ProjectState(BaseModel):
    project_id: str
    name: str
    request_text: str = ""
    plan: Dict[str, Any] = {}
    created_at: str
    updated_at: str