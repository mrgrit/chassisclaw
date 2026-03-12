from pydantic import BaseModel, Field
from typing import Any


class Asset(BaseModel):
    id: str
    name: str
    type: str = "vm"
    mgmt_ip: str
    env: str | None = None
    roles: list[str] = Field(default_factory=list)
    expected_subagent_port: int = 55123
    agent_id: str | None = None
    auth_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssetUpsertReq(BaseModel):
    id: str
    name: str
    type: str = "vm"
    mgmt_ip: str
    env: str | None = None
    roles: list[str] = Field(default_factory=list)
    expected_subagent_port: int = 55123
    agent_id: str | None = None
    auth_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)