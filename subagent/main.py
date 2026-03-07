import os, subprocess, uuid, time
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from guardrails import check_command

AGENT_ID = os.getenv("AGENT_ID", "local-agent-1")
EVIDENCE_DIR = os.getenv("EVIDENCE_DIR", "/data/evidence")
MAX_OUTPUT_BYTES = int(os.getenv("MAX_OUTPUT_BYTES", "200000"))
os.makedirs(EVIDENCE_DIR, exist_ok=True)

app = FastAPI(title="OpsClaw SubAgent", version="0.1.0")

class RunScriptReq(BaseModel):
    run_id: str
    target_id: str
    script: str
    timeout_s: int = 60
    approval_required: bool = False
    evidence_requests: List[str] = Field(default_factory=list)

def _cap(s: str) -> str:
    if s is None:
        return ""
    b = s.encode("utf-8", errors="ignore")[:MAX_OUTPUT_BYTES]
    return b.decode("utf-8", errors="ignore")

def _save_evidence(run_id: str, name: str, content: str) -> str:
    path = os.path.join(EVIDENCE_DIR, f"{run_id}_{name}.log")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

def _evidence_cmd(name: str) -> Optional[str]:
    mapping = {
        "uname": "uname -a",
        "uptime": "uptime",
        "df": "df -h",
        "ss_listen": "ss -lntp",
    }
    return mapping.get(name)

@app.get("/health")
def health():
    return {"ok": True, "agent_id": AGENT_ID}

@app.post("/a2a/run_script")
def a2a_run_script(req: RunScriptReq):
    ok, reason = check_command(req.script)
    if not ok:
        return {
            "run_id": req.run_id,
            "exit_code": 126,
            "stdout": "",
            "stderr": reason,
            "changed_files": [],
            "evidence_refs": [],
        }

    # (MVP) approval_required는 UI/RBAC 붙일 때 처리. 지금은 flag만 유지.
    try:
        proc = subprocess.run(
            req.script,
            shell=True,
            capture_output=True,
            text=True,
            timeout=req.timeout_s,
        )
        stdout = _cap(proc.stdout)
        stderr = _cap(proc.stderr)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        stdout, stderr, exit_code = "", f"Timeout after {req.timeout_s}s", 124

    evidence_refs: List[str] = []
    # evidence 요청 수행
    for ev in req.evidence_requests:
        cmd = _evidence_cmd(ev)
        if not cmd:
            continue
        try:
            p2 = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
            out = _cap(p2.stdout + ("\n" + p2.stderr if p2.stderr else ""))
        except Exception as e:
            out = f"evidence error: {e}"
        evidence_refs.append(_save_evidence(req.run_id, ev, out))

    # 기본 증빙: 실행 결과도 파일로 남김
    evidence_refs.append(_save_evidence(req.run_id, "run_stdout", stdout))
    evidence_refs.append(_save_evidence(req.run_id, "run_stderr", stderr))

    return {
        "run_id": req.run_id,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "changed_files": [],
        "evidence_refs": evidence_refs,
    }