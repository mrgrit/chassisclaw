from pathlib import Path
from .paths import TARGETS_DIR
from .json_store import read_json, write_json

class TargetStore:
    def __init__(self, base_dir: Path = TARGETS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, target_id: str) -> Path:
        return self.base_dir / f"{target_id}.json"

    def upsert(self, target_id: str, payload: dict) -> dict:
        return write_json(self._path(target_id), payload)

    def get(self, target_id: str):
        path = self._path(target_id)
        if not path.exists():
            return None
        return read_json(path, {})

    def delete(self, target_id: str) -> bool:
        path = self._path(target_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list(self):
        return [read_json(p, {}) for p in sorted(self.base_dir.glob("*.json"))]
