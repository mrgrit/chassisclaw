from pydantic import BaseModel, Field

class TargetUpsertReq(BaseModel):
    id: str
    base_url: str
    mode: str = "subagent_http"
    tags: list[str] = Field(default_factory=list)
