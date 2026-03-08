import json
from pathlib import Path

class EvidenceService:
    def __init__(self, base_dir="data/evidence"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_tool_result(self, project_id: str, result):
        project_dir = self.base_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        ev_ref = f"evidence_{project_id}_{getattr(result, 'run_id', 'unknown')}.json"
        path = project_dir / ev_ref

        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)