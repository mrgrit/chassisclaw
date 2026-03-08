import json
import os
from datetime import datetime
from typing import Any, Dict

from .paths import AUDIT_DIR

def append_audit(event: Dict[str, Any]) -> None:
    os.makedirs(AUDIT_DIR, exist_ok=True)
    event = dict(event)
    event.setdefault("ts", datetime.utcnow().isoformat() + "Z")
    p = os.path.join(AUDIT_DIR, "audit.jsonl")
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")