from typing import Any, Dict, List
from engine.a2a_client import run_script

def _lines(s: str) -> List[str]:
    return [x.strip() for x in (s or "").splitlines() if x.strip()]

def collect_net_probe(*, subagent_url: str, target_id: str, timeout_s: int) -> Dict[str, Any]:
    rationale: List[str] = []
    evidence_refs: List[str] = []
    facts: Dict[str, Any] = {
        "interfaces": [],
        "ipv4_addresses": {},
        "default_route": None,
        "routes": [],
        "dns_resolv_conf": None,
    }
    unknowns: List[str] = []

    # interfaces
    r = run_script(subagent_url, {
        "run_id": f"netprobe-if-{target_id}",
        "target_id": target_id,
        "script": "ip -o link show | awk -F': ' '{print $2}' || true",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs += (r.get("evidence_refs") or [])
    ifs = _lines(r.get("stdout") or "")
    facts["interfaces"] = ifs
    rationale.append(f"detected {len(ifs)} interfaces")

    # ipv4 addr summary
    r = run_script(subagent_url, {
        "run_id": f"netprobe-ipv4-{target_id}",
        "target_id": target_id,
        "script": "ip -o -4 addr show || true",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs += (r.get("evidence_refs") or [])
    raw = r.get("stdout") or ""
    # very simple parse
    # format: <idx>: <ifname> inet <ip>/<mask> ...
    ipv4: Dict[str, List[str]] = {}
    for line in _lines(raw):
        parts = line.split()
        if len(parts) >= 4 and parts[2] == "inet":
            ifname = parts[1]
            ipcidr = parts[3]
            # normalize eth0@if9 -> eth0
            if "@" in ifname:
                ifname = ifname.split("@", 1)[0]
            ipv4.setdefault(ifname, []).append(ipcidr)
    facts["ipv4_addresses"] = ipv4
    rationale.append("collected ipv4 addresses")

    # default route
    r = run_script(subagent_url, {
        "run_id": f"netprobe-route-default-{target_id}",
        "target_id": target_id,
        "script": "ip route show default || true",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs += (r.get("evidence_refs") or [])
    facts["default_route"] = (r.get("stdout") or "").strip()
    rationale.append("collected default route")

    # route table (short)
    r = run_script(subagent_url, {
        "run_id": f"netprobe-routes-{target_id}",
        "target_id": target_id,
        "script": "ip route | head -n 50 || true",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs += (r.get("evidence_refs") or [])
    facts["routes"] = _lines(r.get("stdout") or "")
    rationale.append("collected route table (head 50)")

    # resolv.conf
    r = run_script(subagent_url, {
        "run_id": f"netprobe-dns-{target_id}",
        "target_id": target_id,
        "script": "cat /etc/resolv.conf 2>/dev/null | head -n 50 || true",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs += (r.get("evidence_refs") or [])
    facts["dns_resolv_conf"] = r.get("stdout") or ""
    rationale.append("collected /etc/resolv.conf (head 50)")

    status = "ok" if len(unknowns) == 0 else "partial"
    return {"status": status, "domain": "net.probe", "facts": facts, "rationale": rationale, "evidence_refs": evidence_refs, "unknowns": unknowns}