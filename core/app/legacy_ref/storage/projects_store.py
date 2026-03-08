import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .paths import STATE_DIR
from .json_store import load_json, save_json

def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"

def project_path(project_id: str) -> str:
    return os.path.join(STATE_DIR, "projects", f"{project_id}.json")

def create_project(name: str, request_text: str = "") -> Dict[str, Any]:
    pid = str(uuid.uuid4())
    st = {
        "project_id": pid,
        "name": name,
        "request_text": request_text or "",
        "plan": {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    save_json(project_path(pid), st)
    return st

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    return load_json(project_path(project_id), None)

def update_project(project_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    st = get_project(project_id) or {}
    st.update(patch or {})
    st["project_id"] = project_id
    st["updated_at"] = _now()
    save_json(project_path(project_id), st)
    return st