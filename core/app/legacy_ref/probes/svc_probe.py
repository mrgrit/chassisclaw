from typing import Any, Dict, List, Optional
from engine.a2a_client import run_script

def collect_svc_probe(*, subagent_url: str, target_id: str, timeout_s: int, service_name: Optional[str]=None, health_url: Optional[str]=None) -> Dict[str, Any]:
    rationale: List[str] = []
    evidence_refs: List[str] = []
    facts: Dict[str, Any] = {"service_manager": None, "service_active": None, "process_found": None, "listening_ports": [], "health_ok": None}
    unknowns: List[str] = []

    # service manager (systemctl vs service)
    r = run_script(subagent_url, {
        "run_id": f"svcprobe-mgr-{target_id}",
        "target_id": target_id,
        "script": "command -v systemctl >/dev/null 2>&1 && echo systemctl || (command -v service >/dev/null 2>&1 && echo service || echo unknown)",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs += (r.get("evidence_refs") or [])
    sm = (r.get("stdout") or "").strip()
    facts["service_manager"] = sm
    rationale.append(f"detected service manager '{sm}'")

    # listening ports snapshot (always)
    r = run_script(subagent_url, {
        "run_id": f"svcprobe-ports-{target_id}",
        "target_id": target_id,
        "script": "ss -lntp 2>/dev/null | awk 'NR>1{print $4}' | sort -u || true",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs += (r.get("evidence_refs") or [])
    ports = [x.strip() for x in (r.get("stdout") or "").splitlines() if x.strip()]
    facts["listening_ports"] = ports
    rationale.append(f"collected {len(ports)} listening socket entries")

    # service_active (optional)
    if service_name:
        if sm == "systemctl":
            cmd = f"systemctl is-active {service_name} 2>/dev/null || true"
        elif sm == "service":
            cmd = f"service {service_name} status 2>/dev/null | grep -qi running && echo active || echo stopped"
        else:
            cmd = "echo unknown"
        r = run_script(subagent_url, {
            "run_id": f"svcprobe-active-{target_id}",
            "target_id": target_id,
            "script": cmd,
            "timeout_s": timeout_s,
            "approval_required": False,
            "evidence_requests": [],
        }, timeout_s=timeout_s + 30)
        evidence_refs += (r.get("evidence_refs") or [])
        out = (r.get("stdout") or "").strip().lower()
        facts["service_active"] = (out == "active")
        rationale.append(f"checked service active state for '{service_name}'")
    else:
        unknowns.append("service_active")

    # process_found (optional: service_name used as grep key)
    if service_name:
        r = run_script(subagent_url, {
            "run_id": f"svcprobe-proc-{target_id}",
            "target_id": target_id,
            "script": f"ps aux | grep -v grep | grep -q '{service_name}' && echo found || echo notfound",
            "timeout_s": timeout_s,
            "approval_required": False,
            "evidence_requests": [],
        }, timeout_s=timeout_s + 30)
        evidence_refs += (r.get("evidence_refs") or [])
        facts["process_found"] = ((r.get("stdout") or "").strip() == "found")
        rationale.append(f"checked process existence for '{service_name}'")
    else:
        unknowns.append("process_found")

    # health check (optional)
    if health_url:
        r = run_script(subagent_url, {
            "run_id": f"svcprobe-health-{target_id}",
            "target_id": target_id,
            "script": f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 3 '{health_url}' || echo 000",
            "timeout_s": timeout_s,
            "approval_required": False,
            "evidence_requests": [],
        }, timeout_s=timeout_s + 30)
        evidence_refs += (r.get("evidence_refs") or [])
        code = (r.get("stdout") or "").strip()
        facts["health_ok"] = (code == "200")
        rationale.append(f"checked health url '{health_url}'")
    else:
        unknowns.append("health_ok")

    status = "ok" if len(unknowns) == 0 else "partial"
    return {"status": status, "domain": "svc.probe", "facts": facts, "rationale": rationale, "evidence_refs": evidence_refs, "unknowns": unknowns}