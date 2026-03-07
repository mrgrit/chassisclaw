from pydantic import BaseModel, Field
from typing import List

class TargetUpsertReq(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(default="")
    base_url: str = Field(..., min_length=1, description="ex) http://192.168.0.10:55123")
    tags: List[str] = []
    notes: str = ""