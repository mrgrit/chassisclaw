from fastapi import FastAPI, HTTPException

from storage.audit_store import append_audit
from schemas.projects import CreateProjectReq
from storage.projects_store import create_project, get_project

from schemas.targets import TargetUpsertReq
from storage.targets_store import list_targets, get_target, upsert_target, delete_target

from schemas.a2a import RunScriptReq
from engine.a2a_client import run_script as a2a_run_script
from storage.targets_store import get_target
import os

from schemas.probe import ProbeReq
from probes.sys_probe import collect_sys_probe
from probes.svc_probe import collect_svc_probe
from probes.fs_probe import collect_fs_probe
from probes.net_probe import collect_net_probe

app = FastAPI(title="OpsClaw Core (Rebuild)")

@app.get("/health")
def health():
    return {"ok": True, "service": "opsclaw-core", "version": "core-rebuild-v0"}

@app.post("/audit/test")
def audit_test():
    append_audit({"type": "AUDIT_TEST", "msg": "hello from core"})
    return {"ok": True}

@app.post("/projects")
def create_project_api(req: CreateProjectReq):
    st = create_project(name=req.name, request_text=req.request_text)
    append_audit({"type": "PROJECT_CREATED", "project_id": st["project_id"], "name": st["name"]})
    return {"project_id": st["project_id"], "state": st}

@app.get("/projects/{project_id}")
def get_project_api(project_id: str):
    st = get_project(project_id)
    if not st:
        raise HTTPException(status_code=404, detail="project not found")
    return st

@app.get("/targets")
def list_targets_api():
    return {"items": list_targets()}

@app.get("/targets/{target_id}")
def get_target_api(target_id: str):
    t = get_target(target_id)
    if not t:
        raise HTTPException(status_code=404, detail="target not found")
    return t

@app.post("/targets")
def upsert_target_api(req: TargetUpsertReq):
    t = req.model_dump()
    upsert_target(t)
    append_audit({"type": "TARGET_UPSERT", "target_id": t["id"], "base_url": t["base_url"]})
    return t

@app.delete("/targets/{target_id}")
def delete_target_api(target_id: str):
    ok = delete_target(target_id)
    append_audit({"type": "TARGET_DELETE", "target_id": target_id, "ok": ok})
    return {"ok": ok}

SUBAGENT_URL = os.getenv("SUBAGENT_URL", "http://subagent:55123")

def resolve_subagent_url(target_id: str) -> str:
    if not target_id or target_id in ("local-agent-1", "local", "localhost"):
        return SUBAGENT_URL
    t = get_target(target_id)
    if not t:
        raise HTTPException(status_code=404, detail=f"target not found: {target_id}")
    return (t.get("base_url") or "").rstrip("/")


@app.post("/a2a/run_script")
def run_script_api(req: RunScriptReq):
    subagent_url = resolve_subagent_url(req.target_id)

    payload = req.model_dump()
    res = a2a_run_script(subagent_url, payload, timeout_s=req.timeout_s + 30)

    append_audit({
        "type": "A2A_RUN_SCRIPT",
        "run_id": req.run_id,
        "target_id": req.target_id,
        "subagent_url": subagent_url,
        "exit_code": res.get("exit_code"),
    })

    # evidence_refs는 subagent가 /data/evidence 경로를 주니까 그대로 리턴
    return res

@app.post("/probe/sys")
def probe_sys(req: ProbeReq):
    subagent_url = resolve_subagent_url(req.target_id)
    res = collect_sys_probe(subagent_url=subagent_url, target_id=req.target_id, timeout_s=req.timeout_s)
    append_audit({"type": "PROBE_SYS", "target_id": req.target_id, "status": res.get("status")})
    return res

@app.post("/probe/svc")
def probe_svc(req: ProbeReq):
    subagent_url = resolve_subagent_url(req.target_id)
    service_name = (req.params or {}).get("service_name")
    health_url = (req.params or {}).get("health_url")
    res = collect_svc_probe(subagent_url=subagent_url, target_id=req.target_id, timeout_s=req.timeout_s, service_name=service_name, health_url=health_url)
    append_audit({"type": "PROBE_SVC", "target_id": req.target_id, "status": res.get("status")})
    return res

@app.post("/probe/fs")
def probe_fs(req: ProbeReq):
    subagent_url = resolve_subagent_url(req.target_id)
    path = (req.params or {}).get("path") or "/"
    top_n = int((req.params or {}).get("top_n") or 10)
    res = collect_fs_probe(subagent_url=subagent_url, target_id=req.target_id, timeout_s=req.timeout_s, path=path, top_n=top_n)
    append_audit({"type": "PROBE_FS", "target_id": req.target_id, "status": res.get("status"), "path": path})
    return res

@app.post("/probe/net")
def probe_net(req: ProbeReq):
    subagent_url = resolve_subagent_url(req.target_id)
    res = collect_net_probe(subagent_url=subagent_url, target_id=req.target_id, timeout_s=req.timeout_s)
    append_audit({"type": "PROBE_NET", "target_id": req.target_id, "status": res.get("status")})
    return res