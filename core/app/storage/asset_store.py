from pathlib import Path
from .paths import ASSETS_DIR
from .json_store import read_json, write_json


class AssetStore:
    def __init__(self, base_dir: Path = ASSETS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, asset_id: str) -> Path:
        return self.base_dir / f"{asset_id}.json"

    def upsert(self, asset_id: str, payload: dict) -> dict:
        return write_json(self._path(asset_id), payload)

    def get(self, asset_id: str):
        path = self._path(asset_id)
        if not path.exists():
            return None
        return read_json(path, {})

    def delete(self, asset_id: str) -> bool:
        path = self._path(asset_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list(self):
        return [read_json(p, {}) for p in sorted(self.base_dir.glob('*.json'))]
