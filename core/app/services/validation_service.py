from app.models.playbook_ir import PlaybookIR


class ValidationService:
    def validate(self, project: dict, plan_ir: PlaybookIR, last_result: dict | None = None) -> dict:
        # 아직 모르는 입력이 남아 있으면 완료 아님
        if plan_ir.unknowns:
            return {
                "ok": False,
                "reason": "unknowns_remaining",
                "retryable": True,
                "unknowns": list(plan_ir.unknowns),
            }

        # 마지막 실행이 실패면 replan 진입 가능
        if last_result and int(last_result.get("exit_code", 0)) != 0:
            return {
                "ok": False,
                "reason": "last_action_failed",
                "retryable": True,
                "exit_code": int(last_result.get("exit_code", 0)),
            }

        return {
            "ok": True,
            "reason": "minimal_validation_passed",
            "retryable": False,
        }