import re

DENY_PATTERNS = [
    re.compile(r"rm\s+-rf\s+/", re.I),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*;\s*\}\s*;:", re.I),  # fork bomb
    re.compile(r"\bmkfs\.", re.I),
    re.compile(r"\bdd\s+if=.*\s+of=/dev/", re.I),
]

def check_command(cmd: str):
    for p in DENY_PATTERNS:
        if p.search(cmd):
            return False, f"Blocked by guardrails: pattern={p.pattern}"
    return True, ""