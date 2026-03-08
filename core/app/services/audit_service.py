import json
from datetime import datetime
from app.storage.paths import AUDIT_DIR

class AuditService:
    def append(self, project_id: str, event_type: str, payload: dict):
        path = AUDIT_DIR / f"{project_id}.jsonl"
        rec = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            "payload": payload,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
