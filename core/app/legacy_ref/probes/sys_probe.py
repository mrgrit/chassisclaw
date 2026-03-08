from typing import Any, Dict, List
from engine.a2a_client import run_script

def collect_sys_probe(*, subagent_url: str, target_id: str, timeout_s: int) -> Dict[str, Any]:
    rationale: List[str] = []
    evidence_refs: List[str] = []
    facts: Dict[str, Any] = {}

    # 1) os-release
    r = run_script(subagent_url, {
        "run_id": f"sysprobe-os-{target_id}",
        "target_id": target_id,
        "script": "cat /etc/os-release || true",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs.extend(r.get("evidence_refs") or [])
    facts["os_release"] = r.get("stdout") or ""
    rationale.append("collected /etc/os-release")

    # 2) uname/uptime
    r = run_script(subagent_url, {
        "run_id": f"sysprobe-uname-{target_id}",
        "target_id": target_id,
        "script": "uname -a; uptime || true",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs.extend(r.get("evidence_refs") or [])
    facts["uname_uptime"] = r.get("stdout") or ""
    rationale.append("collected uname/uptime")

    # 3) pkg manager detect
    r = run_script(subagent_url, {
        "run_id": f"sysprobe-pkg-{target_id}",
        "target_id": target_id,
        "script": "command -v apt-get >/dev/null 2>&1 && echo apt || command -v dnf >/dev/null 2>&1 && echo dnf || command -v yum >/dev/null 2>&1 && echo yum || echo unknown",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs.extend(r.get("evidence_refs") or [])
    pm = (r.get("stdout") or "").strip()
    facts["pkg_manager"] = pm
    rationale.append(f"detected pkg_manager={pm}")

    return {
        "status": "ok",
        "domain": "sys.probe",
        "facts": facts,
        "rationale": rationale,
        "evidence_refs": evidence_refs,
        "unknowns": [],
    }