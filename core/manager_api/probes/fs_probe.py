from typing import Any, Dict, List, Optional
from engine.a2a_client import run_script

def collect_fs_probe(
    *,
    subagent_url: str,
    target_id: str,
    timeout_s: int,
    path: str = "/",
    top_n: int = 10,
) -> Dict[str, Any]:
    rationale: List[str] = []
    evidence_refs: List[str] = []
    facts: Dict[str, Any] = {
        "df": None,
        "path": path,
        "path_exists": None,
        "file_count": None,
        "top_large_files": [],
    }
    unknowns: List[str] = []

    # df
    r = run_script(subagent_url, {
        "run_id": f"fsprobe-df-{target_id}",
        "target_id": target_id,
        "script": "df -h || true",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs += (r.get("evidence_refs") or [])
    facts["df"] = r.get("stdout") or ""
    rationale.append("collected df -h")

    # path exists?
    r = run_script(subagent_url, {
        "run_id": f"fsprobe-exists-{target_id}",
        "target_id": target_id,
        "script": f"test -e '{path}' && echo yes || echo no",
        "timeout_s": timeout_s,
        "approval_required": False,
        "evidence_requests": [],
    }, timeout_s=timeout_s + 30)
    evidence_refs += (r.get("evidence_refs") or [])
    facts["path_exists"] = ((r.get("stdout") or "").strip() == "yes")
    rationale.append(f"checked path exists: {path}")

    # file count (only if exists)
    if facts["path_exists"]:
        r = run_script(subagent_url, {
            "run_id": f"fsprobe-count-{target_id}",
            "target_id": target_id,
            "script": f"find '{path}' -xdev -type f 2>/dev/null | wc -l || true",
            "timeout_s": timeout_s,
            "approval_required": False,
            "evidence_requests": [],
        }, timeout_s=timeout_s + 30)
        evidence_refs += (r.get("evidence_refs") or [])
        out = (r.get("stdout") or "").strip()
        try:
            facts["file_count"] = int(out)
        except Exception:
            facts["file_count"] = None
            unknowns.append("file_count")
        rationale.append(f"counted files under {path} (xdev)")
    else:
        unknowns.append("file_count")
        unknowns.append("top_large_files")

    # top large files (only if exists)
    if facts["path_exists"]:
        # note: limit depth a bit to avoid huge cost; adjust later
        cmd = (
            f"find '{path}' -xdev -type f -printf '%s\\t%p\\n' 2>/dev/null | "
            f"sort -nr | head -n {int(top_n)} || true"
        )
        r = run_script(subagent_url, {
            "run_id": f"fsprobe-top-{target_id}",
            "target_id": target_id,
            "script": cmd,
            "timeout_s": timeout_s,
            "approval_required": False,
            "evidence_requests": [],
        }, timeout_s=timeout_s + 30)
        evidence_refs += (r.get("evidence_refs") or [])
        lines = [x.strip() for x in (r.get("stdout") or "").splitlines() if x.strip()]
        facts["top_large_files"] = lines
        rationale.append(f"collected top {top_n} largest files under {path}")

    status = "ok" if len(unknowns) == 0 else "partial"
    return {
        "status": status,
        "domain": "fs.probe",
        "facts": facts,
        "rationale": rationale,
        "evidence_refs": evidence_refs,
        "unknowns": unknowns,
    }