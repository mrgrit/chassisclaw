from app.models.playbook_ir import PlaybookIR


class ValidationService:
    def validate(self, project: dict, plan_ir: PlaybookIR, last_result: dict | None = None) -> dict:
        if last_result is None:
            if plan_ir.unknowns:
                return {
                    "ok": False,
                    "reason": "unknowns_remaining",
                    "retryable": False,
                    "next_stage": "resolve",
                    "unknowns": list(plan_ir.unknowns),
                }
            return {
                "ok": False,
                "reason": "no_action_taken",
                "retryable": False,
                "next_stage": "replan",
            }

        exit_code = int(last_result.get("exit_code", 0))
        stderr = (last_result.get("stderr", "") or "").lower()
        stdout = (last_result.get("stdout", "") or "").lower()
        text = f"{stdout}\n{stderr}"

        if exit_code != 0:
            retryable_keywords = [
                "temporary failure",
                "temporarily unavailable",
                "try again",
                "timed out",
                "timeout",
                "connection reset",
                "network is unreachable",
                "name or service not known",
            ]

            non_retryable_keywords = [
                "command not found",
                "permission denied",
                "not permitted",
                "invalid option",
                "unknown option",
                "no such file or directory",
                "syntax error",
            ]

            if any(k in text for k in non_retryable_keywords):
                return {
                    "ok": False,
                    "reason": "last_action_failed",
                    "retryable": False,
                    "next_stage": "replan",
                    "exit_code": exit_code,
                }

            if any(k in text for k in retryable_keywords):
                return {
                    "ok": False,
                    "reason": "last_action_failed",
                    "retryable": True,
                    "next_stage": "retry",
                    "exit_code": exit_code,
                }

            return {
                "ok": False,
                "reason": "last_action_failed",
                "retryable": False,
                "next_stage": "replan",
                "exit_code": exit_code,
            }

        if plan_ir.unknowns:
            return {
                "ok": False,
                "reason": "unknowns_remaining",
                "retryable": False,
                "next_stage": "resolve",
                "unknowns": list(plan_ir.unknowns),
            }

        return {
            "ok": True,
            "reason": "passed",
            "retryable": False,
            "next_stage": "resolve",
        }