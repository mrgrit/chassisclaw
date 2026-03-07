import requests
from typing import Any, Dict

def run_script(subagent_base_url: str, payload: Dict[str, Any], timeout_s: int = 120) -> Dict[str, Any]:
    base = (subagent_base_url or "").rstrip("/")
    url = f"{base}/a2a/run_script"
    r = requests.post(url, json=payload, timeout=timeout_s)
    r.raise_for_status()
    return r.json()