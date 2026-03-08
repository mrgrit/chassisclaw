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
