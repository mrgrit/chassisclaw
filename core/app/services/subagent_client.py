import requests
from app.models.tool_result import ToolResult

class SubAgentClient:
    def health(self, base_url: str) -> dict:
        r = requests.get(f"{base_url.rstrip('/')}/health", timeout=5)
        r.raise_for_status()
        return r.json()

    def capabilities(self, base_url: str) -> dict:
        r = requests.get(f"{base_url.rstrip('/')}/capabilities", timeout=10)
        r.raise_for_status()
        return r.json()

    def run_script(self, base_url: str, run_id: str, target_id: str, script: str, timeout_s: int = 30) -> ToolResult:
        r = requests.post(
            f"{base_url.rstrip('/')}/a2a/run_script",
            json={"run_id": run_id, "target_id": target_id, "script": script, "timeout_s": timeout_s},
            timeout=timeout_s + 10,
        )
        r.raise_for_status()
        return ToolResult(**r.json())
