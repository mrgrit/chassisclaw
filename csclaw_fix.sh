#!/usr/bin/env bash
set -uo pipefail

ROOT="${1:-$PWD}"
cd "$ROOT" || exit 1

echo "[1/8] backup"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="archive/fix_backup_${TS}"
mkdir -p "$BACKUP_DIR"

backup_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  mkdir -p "$BACKUP_DIR/$(dirname "$f")"
  cp -a "$f" "$BACKUP_DIR/$f"
}

for f in \
  docker-compose.yml \
  core/app/main.py \
  core/app/api/*.py \
  core/app/models/*.py \
  core/app/services/*.py \
  core/app/storage/*.py \
  subagent/app/main.py \
  subagent/app/api/*.py \
  subagent/app/models/*.py \
  subagent/app/services/*.py
do
  for x in $f; do
    backup_file "$x"
  done
done

echo "[2/8] ensure dirs/init"
mkdir -p core/app/{api,models,services,storage}
mkdir -p subagent/app/{api,models,services,storage}
mkdir -p engine/app
touch core/__init__.py core/app/__init__.py
touch core/app/api/__init__.py core/app/models/__init__.py core/app/services/__init__.py core/app/storage/__init__.py
touch subagent/__init__.py subagent/app/__init__.py
touch subagent/app/api/__init__.py subagent/app/models/__init__.py subagent/app/services/__init__.py subagent/app/storage/__init__.py
touch engine/__init__.py engine/app/__init__.py

echo "[3/8] fix imports safely"
fix_imports() {
  local dir="$1"
  local bad="$2"
  local good="$3"
  while IFS= read -r -d '' f; do
    sed -i \
      -e "s/from ${bad}\./from ${good}./g" \
      -e "s/import ${bad}\./import ${good}./g" \
      -e "s/from ${bad}/from ${good}/g" \
      -e "s/import ${bad}/import ${good}/g" \
      "$f"
  done < <(find "$dir" -type f \( -name "*.py" -o -name "*.txt" \) -print0 2>/dev/null)
}

fix_imports core/app "core.app" "app"
fix_imports subagent/app "subagent.app" "app"

echo "[4/8] write core files"
cat > core/app/storage/paths.py <<'PYEOF'
from pathlib import Path
import os

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data"))
STATE_DIR = DATA_ROOT / "state"
PROJECTS_DIR = STATE_DIR / "projects"
TARGETS_DIR = STATE_DIR / "targets"
AUDIT_DIR = DATA_ROOT / "audit"
EVIDENCE_DIR = DATA_ROOT / "evidence"
ARTIFACTS_DIR = DATA_ROOT / "artifacts"

for p in [STATE_DIR, PROJECTS_DIR, TARGETS_DIR, AUDIT_DIR, EVIDENCE_DIR, ARTIFACTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
PYEOF

cat > core/app/storage/json_store.py <<'PYEOF'
import json
from pathlib import Path
from typing import Any

def read_json(path: Path, default: Any):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
PYEOF

cat > core/app/storage/project_store.py <<'PYEOF'
from pathlib import Path
from .paths import PROJECTS_DIR
from .json_store import read_json, write_json

class ProjectStore:
    def __init__(self, base_dir: Path = PROJECTS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        return self.base_dir / f"{project_id}.json"

    def create(self, project_id: str, payload: dict) -> dict:
        return write_json(self._path(project_id), payload)

    def get(self, project_id: str):
        path = self._path(project_id)
        if not path.exists():
            return None
        return read_json(path, {})

    def save(self, project_id: str, payload: dict) -> dict:
        return write_json(self._path(project_id), payload)

    def list(self):
        return [read_json(p, {}) for p in sorted(self.base_dir.glob("*.json"))]
PYEOF

cat > core/app/storage/target_store.py <<'PYEOF'
from pathlib import Path
from .paths import TARGETS_DIR
from .json_store import read_json, write_json

class TargetStore:
    def __init__(self, base_dir: Path = TARGETS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, target_id: str) -> Path:
        return self.base_dir / f"{target_id}.json"

    def upsert(self, target_id: str, payload: dict) -> dict:
        return write_json(self._path(target_id), payload)

    def get(self, target_id: str):
        path = self._path(target_id)
        if not path.exists():
            return None
        return read_json(path, {})

    def delete(self, target_id: str) -> bool:
        path = self._path(target_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list(self):
        return [read_json(p, {}) for p in sorted(self.base_dir.glob("*.json"))]
PYEOF

cat > core/app/models/project.py <<'PYEOF'
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
PYEOF

cat > core/app/models/target.py <<'PYEOF'
from pydantic import BaseModel, Field

class TargetUpsertReq(BaseModel):
    id: str
    base_url: str
    mode: str = "subagent_http"
    tags: list[str] = Field(default_factory=list)
PYEOF

cat > core/app/models/tool_result.py <<'PYEOF'
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    ok: bool = True
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    resource_hints: dict = Field(default_factory=dict)
PYEOF

cat > core/app/models/action_ir.py <<'PYEOF'
from typing import Optional, Literal
from pydantic import BaseModel, Field

ActionType = Literal["shell", "http", "file_op", "oss_install", "wrapper_gen"]

class ActionItem(BaseModel):
    id: str
    type: ActionType
    target_id: str
    timeout_s: int = 30
    script: Optional[str] = None
    params: dict = Field(default_factory=dict)
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
    resolved_inputs: dict = Field(default_factory=dict)
    question: Optional[HumanQuestion] = None
    approval_request: Optional[ApprovalRequest] = None
PYEOF

cat > core/app/models/resolution.py <<'PYEOF'
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
    evidence_map: dict = Field(default_factory=dict)
PYEOF

cat > core/app/models/playbook_ir.py <<'PYEOF'
from typing import Any
from pydantic import BaseModel, Field

class PlaybookIR(BaseModel):
    goal: str
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    unknowns: list[str] = Field(default_factory=list)
    probes: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    plan: dict[str, Any] = Field(default_factory=lambda: {"jobs": [], "steps": []})
    validate: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    fixes: list[dict[str, Any]] = Field(default_factory=list)
    replans: list[dict[str, Any]] = Field(default_factory=list)
    iterations: int = 0
PYEOF

cat > core/app/services/llm_registry.py <<'PYEOF'
class LLMRegistry:
    def __init__(self):
        self.connections = {}
        self.role_bindings = {}

    def register_connection(self, conn_id: str, payload: dict) -> dict:
        self.connections[conn_id] = payload
        return payload

    def bind_role(self, role: str, conn_id: str) -> None:
        if conn_id not in self.connections:
            raise ValueError(f"unknown conn_id: {conn_id}")
        self.role_bindings[role] = conn_id

    def resolve_llm_conn_for_role(self, role: str, target_id: str | None = None) -> dict:
        conn_id = self.role_bindings.get(role)
        if not conn_id:
            raise ValueError(f"no llm bound for role={role}")
        return self.connections[conn_id]
PYEOF

cat > core/app/services/audit_service.py <<'PYEOF'
import json
from datetime import datetime
from app.storage.paths import AUDIT_DIR

class AuditService:
    def append(self, project_id: str, event_type: str, payload: dict):
        path = AUDIT_DIR / f"{project_id}.jsonl"
        rec = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            "payload": payload,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
PYEOF

cat > core/app/services/evidence_service.py <<'PYEOF'
import json
from datetime import datetime
from app.storage.paths import EVIDENCE_DIR

class EvidenceService:
    def save_tool_result(self, project_id: str, result) -> str:
        ref = f"ev_{project_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        path = EVIDENCE_DIR / f"{ref}.json"
        payload = result.model_dump() if hasattr(result, "model_dump") else result
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return ref
PYEOF

cat > core/app/services/subagent_client.py <<'PYEOF'
import requests
from app.models.tool_result import ToolResult

class SubAgentClient:
    def health(self, base_url: str) -> dict:
        r = requests.get(f"{base_url.rstrip('/')}/health", timeout=5)
        r.raise_for_status()
        return r.json()

    def capabilities(self, base_url: str) -> dict:
        r = requests.get(f"{base_url.rstrip('/')}/capabilities", timeout=10)
        r.raise_for_status()
        return r.json()

    def run_script(self, base_url: str, run_id: str, target_id: str, script: str, timeout_s: int = 30) -> ToolResult:
        r = requests.post(
            f"{base_url.rstrip('/')}/a2a/run_script",
            json={"run_id": run_id, "target_id": target_id, "script": script, "timeout_s": timeout_s},
            timeout=timeout_s + 10,
        )
        r.raise_for_status()
        return ToolResult(**r.json())
PYEOF

cat > core/app/services/probe_loop_service.py <<'PYEOF'
import uuid
from app.models.action_ir import ActionIR
from app.models.playbook_ir import PlaybookIR
from app.models.resolution import Resolution
from app.services.subagent_client import SubAgentClient

class ProbeLoopService:
    def __init__(self, llm_registry, subagent_client: SubAgentClient, audit_service, evidence_service):
        self.llm_registry = llm_registry
        self.subagent_client = subagent_client
        self.audit_service = audit_service
        self.evidence_service = evidence_service

    def run(self, project: dict, target: dict, max_iterations: int = 3) -> dict:
        plan_ir = PlaybookIR(**project["plan_ir"])

        for i in range(max_iterations):
            plan_ir.iterations += 1
            self.audit_service.append(project["id"], "PROBE_START", {"iteration": i + 1})

            llm_conn = self.llm_registry.resolve_llm_conn_for_role("master", target_id=target["id"])
            action_ir = self._ask_master_for_probe_or_question(llm_conn, plan_ir, project)

            if action_ir.question:
                resolution = Resolution(mode="ASK", question=action_ir.question, rationale="Need user clarification")
                project["plan_ir"] = plan_ir.model_dump()
                project["resolution"] = resolution.model_dump()
                project["status"] = "needs_clarification"
                project["stage"] = "resolve"
                return {"status": "needs_clarification", "resolution": resolution.model_dump()}

            if action_ir.approval_request:
                resolution = Resolution(mode="APPROVAL", approval_request=action_ir.approval_request, rationale="Approval required")
                project["plan_ir"] = plan_ir.model_dump()
                project["resolution"] = resolution.model_dump()
                project["status"] = "needs_approval"
                project["stage"] = "resolve"
                return {"status": "needs_approval", "resolution": resolution.model_dump()}

            if action_ir.resolved_inputs:
                resolution = Resolution(mode="AUTO", resolved_inputs=action_ir.resolved_inputs, rationale="Resolved automatically")
                project["plan_ir"] = plan_ir.model_dump()
                project["resolution"] = resolution.model_dump()
                project["status"] = "resolved"
                project["stage"] = "resolve"
                return {"status": "resolved", "resolution": resolution.model_dump()}

            for action in action_ir.actions:
                if action.type != "shell":
                    raise ValueError(f"unsupported action type in M1: {action.type}")

                result = self.subagent_client.run_script(
                    base_url=target["base_url"],
                    run_id=f"run_{uuid.uuid4().hex[:8]}",
                    target_id=target["id"],
                    script=action.script or "",
                    timeout_s=action.timeout_s,
                )
                ev_ref = self.evidence_service.save_tool_result(project["id"], result)
                plan_ir.evidence.append({"action_id": action.id, "evidence_ref": ev_ref})

                followup = self._ask_master_after_probe(llm_conn, plan_ir, result.model_dump(), project)

                if followup.question:
                    resolution = Resolution(mode="ASK", question=followup.question, rationale="Need user input after probe")
                    project["plan_ir"] = plan_ir.model_dump()
                    project["resolution"] = resolution.model_dump()
                    project["status"] = "needs_clarification"
                    project["stage"] = "resolve"
                    return {"status": "needs_clarification", "resolution": resolution.model_dump()}

                if followup.resolved_inputs:
                    resolution = Resolution(mode="AUTO", resolved_inputs=followup.resolved_inputs, rationale="Resolved from probe")
                    project["plan_ir"] = plan_ir.model_dump()
                    project["resolution"] = resolution.model_dump()
                    project["status"] = "resolved"
                    project["stage"] = "resolve"
                    return {"status": "resolved", "resolution": resolution.model_dump()}

        project["status"] = "failed"
        project["stage"] = "replan"
        return {"status": "failed", "reason": "max_iterations_exceeded"}

    def _ask_master_for_probe_or_question(self, llm_conn: dict, plan_ir: PlaybookIR, project: dict) -> ActionIR:
        unknowns = set(plan_ir.unknowns)
        if "iface_in" in unknowns or "iface_out" in unknowns:
            return ActionIR(actions=[{
                "id": "probe_iface",
                "type": "shell",
                "target_id": project["target_ids"][0],
                "timeout_s": 20,
                "script": "ip -o link show\nip route\n",
            }])
        return ActionIR(question={
            "type": "policy",
            "field": "internal_cidr",
            "text": "내부망 CIDR 알려줘",
            "choices": [],
        })

    def _ask_master_after_probe(self, llm_conn: dict, plan_ir: PlaybookIR, result: dict, project: dict) -> ActionIR:
        stdout = result.get("stdout", "") or ""
        if "ens33" in stdout:
            return ActionIR(resolved_inputs={"iface_in": "ens33"})
        if "eth0" in stdout:
            return ActionIR(resolved_inputs={"iface_in": "eth0"})
        return ActionIR(question={
            "type": "fact",
            "field": "iface_in",
            "text": "내부망 인터페이스 선택해줘",
            "choices": [],
        })
PYEOF

cat > core/app/api/health.py <<'PYEOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True, "service": "chassisclaw-core", "version": "m1"}
PYEOF

cat > core/app/api/projects.py <<'PYEOF'
import uuid
from fastapi import APIRouter, HTTPException
from app.models.project import CreateProjectReq

router = APIRouter()

@router.post("/projects")
def create_project(req: CreateProjectReq):
    project_id = f"prj_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": project_id,
        "name": req.name,
        "request_text": req.request_text,
        "status": "created",
        "stage": "plan",
        "target_ids": req.target_ids,
        "answers": {},
        "approvals": {},
        "plan_ir": {"goal": req.request_text, "unknowns": ["iface_in", "iface_out"]},
        "resolution": {},
        "artifacts": [],
    }
    router.project_store.create(project_id, payload)
    router.audit_service.append(project_id, "PROJECT_CREATED", {"name": req.name})
    return {"project_id": project_id, "state": payload}

@router.get("/projects")
def list_projects():
    return {"items": router.project_store.list()}

@router.get("/projects/{project_id}")
def get_project(project_id: str):
    st = router.project_store.get(project_id)
    if not st:
        raise HTTPException(status_code=404, detail="project not found")
    return st
PYEOF

cat > core/app/api/targets.py <<'PYEOF'
from fastapi import APIRouter, HTTPException
from app.models.target import TargetUpsertReq

router = APIRouter()

@router.get("/targets")
def list_targets():
    return {"items": router.target_store.list()}

@router.get("/targets/{target_id}")
def get_target(target_id: str):
    t = router.target_store.get(target_id)
    if not t:
        raise HTTPException(status_code=404, detail="target not found")
    return t

@router.post("/targets")
def upsert_target(req: TargetUpsertReq):
    payload = req.model_dump()
    router.target_store.upsert(req.id, payload)
    return payload
PYEOF

cat > core/app/api/answers.py <<'PYEOF'
from fastapi import APIRouter, HTTPException
router = APIRouter()

@router.post("/projects/{project_id}/answer")
def answer_project(project_id: str, body: dict):
    project = router.project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    answers = project.get("answers", {})
    answers.update(body.get("answers", {}))
    project["answers"] = answers
    router.project_store.save(project_id, project)
    router.audit_service.append(project_id, "ANSWER_SET", {"answers": body.get("answers", {})})
    return {"ok": True, "answers": answers}
PYEOF

cat > core/app/api/approvals.py <<'PYEOF'
from fastapi import APIRouter, HTTPException
router = APIRouter()

@router.post("/projects/{project_id}/approve")
def approve_project(project_id: str, body: dict):
    project = router.project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    approvals = project.get("approvals", {})
    approvals.update(body.get("approvals", {}))
    project["approvals"] = approvals
    router.project_store.save(project_id, project)
    router.audit_service.append(project_id, "APPROVAL_SET", {"approvals": body.get("approvals", {})})
    return {"ok": True, "approvals": approvals}
PYEOF

cat > core/app/api/llm.py <<'PYEOF'
from fastapi import APIRouter
router = APIRouter()

@router.post("/llm/connections")
def register_connection(body: dict):
    conn_id = body["id"]
    return router.llm_registry.register_connection(conn_id, body)

@router.post("/llm/roles")
def bind_role(body: dict):
    router.llm_registry.bind_role(body["role"], body["conn_id"])
    return {"ok": True, "role": body["role"], "conn_id": body["conn_id"]}
PYEOF

cat > core/app/api/run_auto.py <<'PYEOF'
from fastapi import APIRouter, HTTPException
router = APIRouter()

@router.post("/projects/{project_id}/run_auto")
def run_auto(project_id: str, body: dict):
    project = router.project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not project.get("target_ids"):
        raise HTTPException(status_code=400, detail="project has no target_ids")
    target_id = project["target_ids"][0]
    target = router.target_store.get(target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"target not found: {target_id}")

    project["status"] = "running"
    project["stage"] = "probe"
    router.project_store.save(project_id, project)

    result = router.probe_loop_service.run(project=project, target=target, max_iterations=body.get("max_iterations", 3))
    router.project_store.save(project_id, project)
    return result
PYEOF

cat > core/app/main.py <<'PYEOF'
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.targets import router as targets_router
from app.api.answers import router as answers_router
from app.api.approvals import router as approvals_router
from app.api.llm import router as llm_router
from app.api.run_auto import router as run_auto_router

from app.services.audit_service import AuditService
from app.services.evidence_service import EvidenceService
from app.services.llm_registry import LLMRegistry
from app.services.probe_loop_service import ProbeLoopService
from app.services.subagent_client import SubAgentClient

from app.storage.project_store import ProjectStore
from app.storage.target_store import TargetStore

app = FastAPI(title="ChassisClaw Core")

project_store = ProjectStore()
target_store = TargetStore()
audit_service = AuditService()
evidence_service = EvidenceService()
llm_registry = LLMRegistry()
subagent_client = SubAgentClient()
probe_loop_service = ProbeLoopService(llm_registry, subagent_client, audit_service, evidence_service)

llm_registry.register_connection("master-default", {"id": "master-default", "provider": "stub", "model": "stub-master"})
llm_registry.bind_role("master", "master-default")

for r in [projects_router, targets_router, answers_router, approvals_router, run_auto_router]:
    r.project_store = project_store
    r.target_store = target_store
    r.audit_service = audit_service
    r.probe_loop_service = probe_loop_service

llm_router.llm_registry = llm_registry

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(targets_router)
app.include_router(answers_router)
app.include_router(approvals_router)
app.include_router(llm_router)
app.include_router(run_auto_router)
PYEOF

echo "[5/8] write subagent files"
cat > subagent/app/models/tool_result.py <<'PYEOF'
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    ok: bool = True
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    resource_hints: dict = Field(default_factory=dict)
PYEOF

cat > subagent/app/services/guardrails.py <<'PYEOF'
def check_command(script: str):
    deny_patterns = [
        "rm -rf /",
        "mkfs",
        ":(){ :|:& };:",
    ]
    low = (script or "").lower()
    for p in deny_patterns:
        if p in low:
            return False, f"blocked by guardrails: {p}"
    return True, ""
PYEOF

cat > subagent/app/services/runner.py <<'PYEOF'
import os
import subprocess
from datetime import datetime
from pathlib import Path
from app.models.tool_result import ToolResult
from app.services.guardrails import check_command

MAX_OUTPUT_BYTES = int(os.getenv("MAX_OUTPUT_BYTES", "200000"))
EVIDENCE_DIR = Path(os.getenv("EVIDENCE_DIR", "/data/evidence"))
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

def _cap(s: str | None) -> str:
    if s is None:
        return ""
    b = s.encode("utf-8", errors="ignore")[:MAX_OUTPUT_BYTES]
    return b.decode("utf-8", errors="ignore")

class Runner:
    def _save_evidence(self, run_id: str, name: str, content: str) -> str:
        path = EVIDENCE_DIR / f"{run_id}_{name}.log"
        path.write_text(content, encoding="utf-8")
        return str(path)

    def run_script(self, run_id: str, script: str, timeout_s: int = 30) -> ToolResult:
        ok, reason = check_command(script)
        started_at = datetime.utcnow()
        if not ok:
            ended_at = datetime.utcnow()
            stderr = reason
            refs = [self._save_evidence(run_id, "blocked_stderr", stderr)]
            return ToolResult(ok=False, exit_code=126, stdout="", stderr=stderr, evidence_refs=refs, started_at=started_at, ended_at=ended_at)

        try:
            proc = subprocess.run(["bash", "-lc", script], capture_output=True, text=True, timeout=timeout_s)
            stdout = _cap(proc.stdout)
            stderr = _cap(proc.stderr)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired as e:
            stdout = _cap(e.stdout if isinstance(e.stdout, str) else "")
            stderr = _cap((e.stderr if isinstance(e.stderr, str) else "") + "\nTIMEOUT")
            exit_code = 124

        ended_at = datetime.utcnow()
        refs = [
            self._save_evidence(run_id, "run_stdout", stdout),
            self._save_evidence(run_id, "run_stderr", stderr),
        ]
        return ToolResult(
            ok=(exit_code == 0),
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            evidence_refs=refs,
            changed_files=[],
            started_at=started_at,
            ended_at=ended_at,
        )
PYEOF

cat > subagent/app/api/run_script.py <<'PYEOF'
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class RunScriptReq(BaseModel):
    run_id: str
    target_id: str
    script: str
    timeout_s: int = 60

@router.post("/a2a/run_script")
def run_script(req: RunScriptReq):
    result = router.runner.run_script(run_id=req.run_id, script=req.script, timeout_s=req.timeout_s)
    return result.model_dump()
PYEOF

cat > subagent/app/api/capabilities.py <<'PYEOF'
import shutil
import subprocess
from fastapi import APIRouter

router = APIRouter()

def _has_cmd(name: str) -> bool:
    return shutil.which(name) is not None

@router.get("/capabilities")
def capabilities():
    return {
        "ok": True,
        "sudo": _has_cmd("sudo"),
        "systemctl": _has_cmd("systemctl"),
        "docker": _has_cmd("docker"),
        "package_manager": "apt" if _has_cmd("apt") else ("dnf" if _has_cmd("dnf") else ("yum" if _has_cmd("yum") else None)),
        "python": subprocess.getoutput("python3 --version"),
        "node": subprocess.getoutput("node --version") if _has_cmd("node") else None,
    }
PYEOF

cat > subagent/app/main.py <<'PYEOF'
from fastapi import FastAPI
from app.api.run_script import router as run_script_router
from app.api.capabilities import router as capabilities_router
from app.services.runner import Runner

app = FastAPI(title="ChassisClaw SubAgent", version="m1")

runner = Runner()
run_script_router.runner = runner

app.include_router(run_script_router)
app.include_router(capabilities_router)

@app.get("/health")
def health():
    return {"ok": True, "agent_id": "local-agent-1", "service": "chassisclaw-subagent"}
PYEOF

echo "[6/8] write dockerfiles"
cat > core/Dockerfile <<'EOF2'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF2

cat > subagent/Dockerfile <<'EOF2'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
ENV PYTHONPATH=/app
EXPOSE 55123
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "55123"]
EOF2

cat > engine/app/main.py <<'PYEOF'
from fastapi import FastAPI
app = FastAPI(title="ChassisClaw Engine")

@app.get("/health")
def health():
    return {"ok": True, "service": "chassisclaw-engine", "status": "placeholder"}
PYEOF

echo "[7/8] check leftovers"
echo "---- leftover bad imports ----"
grep -RIn 'from core\.app\|import core\.app\|from subagent\.app\|import subagent\.app' core/app subagent/app 2>/dev/null || true

echo "[8/8] rebuild"
docker compose down
docker compose up -d --build

echo
echo "done"
echo "backup: $BACKUP_DIR"
echo "check:"
echo "  docker compose ps"
echo "  docker compose logs -n 80 core"
echo "  docker compose logs -n 80 subagent"
echo "  curl http://127.0.0.1:8000/health"
echo "  curl http://127.0.0.1:55123/health"
echo "  curl http://127.0.0.1:55123/capabilities"
