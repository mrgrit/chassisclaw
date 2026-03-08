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
