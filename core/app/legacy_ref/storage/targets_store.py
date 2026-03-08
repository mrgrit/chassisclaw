import os
from typing import Any, Dict, List, Optional

from .paths import STATE_DIR
from .json_store import load_json, save_json

def _path() -> str:
    return os.path.join(STATE_DIR, "_targets.json")

def list_targets() -> List[Dict[str, Any]]:
    obj = load_json(_path(), {"items": []})
    items = obj.get("items") or []
    if not isinstance(items, list):
        return []
    return items

def get_target(target_id: str) -> Optional[Dict[str, Any]]:
    for t in list_targets():
        if (t.get("id") or "") == target_id:
            return t
    return None

def upsert_target(t: Dict[str, Any]) -> Dict[str, Any]:
    items = list_targets()
    out: List[Dict[str, Any]] = []
    found = False
    for x in items:
        if (x.get("id") or "") == t.get("id"):
            out.append(t)
            found = True
        else:
            out.append(x)
    if not found:
        out.append(t)
    save_json(_path(), {"items": out})
    return t

def delete_target(target_id: str) -> bool:
    items = list_targets()
    out = [x for x in items if (x.get("id") or "") != target_id]
    save_json(_path(), {"items": out})
    return len(out) != len(items)