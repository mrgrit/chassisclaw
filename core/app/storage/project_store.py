from pathlib import Path
from .paths import PROJECTS_DIR
from .json_store import read_json, write_json

class ProjectStore:
    def __init__(self, base_dir: Path = PROJECTS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        return self.base_dir / f"{project_id}.json"

    def create(self, project_id: str, payload: dict) -> dict:
        return write_json(self._path(project_id), payload)

    def get(self, project_id: str):
        path = self._path(project_id)
        if not path.exists():
            return None
        return read_json(path, {})

    def save(self, project_id: str, payload: dict) -> dict:
        return write_json(self._path(project_id), payload)

    def list(self):
        return [read_json(p, {}) for p in sorted(self.base_dir.glob("*.json"))]
