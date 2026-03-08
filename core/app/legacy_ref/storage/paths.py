import os

STATE_DIR = os.getenv("STATE_DIR", "/data/state")
AUDIT_DIR = os.getenv("AUDIT_DIR", "/data/audit")
EVIDENCE_DIR = os.getenv("EVIDENCE_DIR", "/data/evidence")

os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(AUDIT_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)