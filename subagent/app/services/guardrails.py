def check_command(script: str):
    deny_patterns = [
        "rm -rf /",
        "mkfs",
        ":(){ :|:& };:",
    ]
    low = (script or "").lower()
    for p in deny_patterns:
        if p in low:
            return False, f"blocked by guardrails: {p}"
    return True, ""
