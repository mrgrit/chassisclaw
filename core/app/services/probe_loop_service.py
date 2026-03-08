import uuid
from app.models.action_ir import ActionIR
from app.models.playbook_ir import PlaybookIR
from app.models.resolution import Resolution
from app.services.subagent_client import SubAgentClient

class ProbeLoopService:
    def __init__(self, llm_registry, subagent_client, audit_service, evidence_service, validation_service=None):
        self.llm_registry = llm_registry
        self.subagent_client = subagent_client
        self.audit_service = audit_service
        self.evidence_service = evidence_service
        self.validation_service = validation_service

    def run(self, project: dict, target: dict, max_iterations: int = 3) -> dict:
        plan_ir = PlaybookIR(**project["plan_ir"])

        for i in range(max_iterations):
            plan_ir.iterations += 1
            self.audit_service.append(
                project["id"],
                "PROBE_START",
                {"iteration": i + 1, "unknowns": list(plan_ir.unknowns)},
            )

            llm_conn = self.llm_registry.resolve_llm_conn_for_role("master", target_id=target["id"])
            action_ir = self._ask_master_for_probe_or_question(llm_conn, plan_ir, project)

            if action_ir.question:
                resolution = Resolution(
                    mode="ASK",
                    question=action_ir.question,
                    rationale="Need user clarification",
                )
                project["plan_ir"] = plan_ir.model_dump()
                project["resolution"] = resolution.model_dump()
                project["status"] = "needs_clarification"
                project["stage"] = "resolve"
                return {"status": "needs_clarification", "stage": "resolve", "resolution": resolution.model_dump()}

            if action_ir.approval_request:
                resolution = Resolution(
                    mode="APPROVAL",
                    approval_request=action_ir.approval_request,
                    rationale="Approval required",
                )
                project["plan_ir"] = plan_ir.model_dump()
                project["resolution"] = resolution.model_dump()
                project["status"] = "needs_approval"
                project["stage"] = "resolve"
                return {"status": "needs_approval", "stage": "resolve", "resolution": resolution.model_dump()}

            if action_ir.resolved_inputs:
                if hasattr(self, "_apply_resolved_inputs"):
                    self._apply_resolved_inputs(
                        plan_ir,
                        action_ir.resolved_inputs,
                        rationale_map=getattr(action_ir, "input_rationales", {}) or {},
                        evidence_refs_by_input=getattr(action_ir, "evidence_map", {}) or {},
                    )
                else:
                    for key, value in action_ir.resolved_inputs.items():
                        plan_ir.inputs[key] = value
                        if key in plan_ir.unknowns:
                            plan_ir.unknowns.remove(key)

                resolution = Resolution(
                    mode="AUTO",
                    resolved_inputs=action_ir.resolved_inputs,
                    rationale="Resolved automatically",
                    evidence_map=getattr(action_ir, "evidence_map", {}) or {},
                    evidence_refs=sorted(
                        {
                            ref
                            for refs in (getattr(action_ir, "evidence_map", {}) or {}).values()
                            for ref in refs
                        }
                    ),
                )

                validation = (
                    self.validation_service.validate(project, plan_ir, None)
                    if getattr(self, "validation_service", None)
                    else {"ok": True, "reason": "validation_service_disabled", "retryable": False}
                )

                project["plan_ir"] = plan_ir.model_dump()
                project["resolution"] = resolution.model_dump()
                project["validation"] = validation

                if validation["ok"]:
                    project["status"] = "resolved"
                    project["stage"] = "resolve"
                    return {
                        "status": "resolved",
                        "stage": "resolve",
                        "resolution": resolution.model_dump(),
                        "validation": validation,
                    }

                project["status"] = "failed"
                project["stage"] = "replan"
                return {
                    "status": "failed",
                    "stage": "replan",
                    "resolution": resolution.model_dump(),
                    "validation": validation,
                }

            for action in action_ir.actions:
                if action.type != "shell":
                    raise ValueError(f"unsupported action type in M1: {action.type}")

                result = self.subagent_client.run_script(
                    base_url=target["base_url"],
                    run_id=f"run_{uuid.uuid4().hex[:8]}",
                    target_id=target["id"],
                    script=action.script or "",
                    timeout_s=action.timeout_s,
                )

                ev_ref = self.evidence_service.save_tool_result(project["id"], result)
                plan_ir.evidence.append(
                    {
                        "action_id": action.id,
                        "evidence_ref": ev_ref,
                        "exit_code": result.exit_code,
                    }
                )

                followup = self._ask_master_after_probe(
                    llm_conn,
                    plan_ir,
                    result.model_dump(),
                    project,
                    ev_ref=ev_ref,
                )

                if followup.question:
                    resolution = Resolution(
                        mode="ASK",
                        question=followup.question,
                        rationale="Need user input after probe",
                        evidence_refs=[ev_ref],
                    )
                    project["plan_ir"] = plan_ir.model_dump()
                    project["resolution"] = resolution.model_dump()
                    project["status"] = "needs_clarification"
                    project["stage"] = "resolve"
                    return {
                        "status": "needs_clarification",
                        "stage": "resolve",
                        "resolution": resolution.model_dump(),
                    }

                if followup.resolved_inputs:
                    if hasattr(self, "_apply_resolved_inputs"):
                        self._apply_resolved_inputs(
                            plan_ir,
                            followup.resolved_inputs,
                            rationale_map=getattr(followup, "input_rationales", {}) or {},
                            evidence_refs_by_input=getattr(followup, "evidence_map", {}) or {},
                        )
                    else:
                        for key, value in followup.resolved_inputs.items():
                            plan_ir.inputs[key] = value
                            if key in plan_ir.unknowns:
                                plan_ir.unknowns.remove(key)

                    resolution = Resolution(
                        mode="AUTO",
                        resolved_inputs=followup.resolved_inputs,
                        rationale="Resolved from probe",
                        evidence_map=getattr(followup, "evidence_map", {}) or {},
                        evidence_refs=[ev_ref],
                    )

                    validation = (
                        self.validation_service.validate(project, plan_ir, result.model_dump())
                        if getattr(self, "validation_service", None)
                        else {"ok": True, "reason": "validation_service_disabled", "retryable": False}
                    )

                    project["plan_ir"] = plan_ir.model_dump()
                    project["resolution"] = resolution.model_dump()
                    project["validation"] = validation

                    if validation["ok"]:
                        project["status"] = "resolved"
                        project["stage"] = "resolve"
                        return {
                            "status": "resolved",
                            "stage": "resolve",
                            "resolution": resolution.model_dump(),
                            "validation": validation,
                        }

                    project["status"] = "failed"
                    project["stage"] = "replan"
                    return {
                        "status": "failed",
                        "stage": "replan",
                        "resolution": resolution.model_dump(),
                        "validation": validation,
                    }

                validation = (
                    self.validation_service.validate(project, plan_ir, result.model_dump())
                    if getattr(self, "validation_service", None)
                    else {"ok": True, "reason": "validation_service_disabled", "retryable": False}
                )

                if not validation["ok"] and validation.get("retryable", False):
                    project["plan_ir"] = plan_ir.model_dump()
                    project["validation"] = validation
                    project["status"] = "failed"
                    project["stage"] = "replan"
                    return {
                        "status": "failed",
                        "stage": "replan",
                        "validation": validation,
                    }

        project["plan_ir"] = plan_ir.model_dump()
        project["status"] = "failed"
        project["stage"] = "replan"
        return {"status": "failed", "stage": "replan", "reason": "max_iterations_exceeded"}

    def _ask_master_for_probe_or_question(self, llm_conn: dict, plan_ir: PlaybookIR, project: dict) -> ActionIR:
        unknowns = set(plan_ir.unknowns)
        known_inputs = plan_ir.inputs or {}

        if not unknowns:
            return ActionIR(
                resolved_inputs=dict(known_inputs),
                input_rationales=dict(plan_ir.input_rationales or {}),
                evidence_map=dict(plan_ir.evidence_map or {}),
            )

        if "iface_in" in unknowns and "iface_in" not in known_inputs:
            return ActionIR(actions=[{
                "id": "probe_iface",
                "type": "shell",
                "target_id": project["target_ids"][0],
                "timeout_s": 20,
                "script": "ip -o link show\nip route\n",
            }])

        if "iface_out" in unknowns and "iface_out" not in known_inputs:
            iface_in = known_inputs.get("iface_in", "")
            return ActionIR(actions=[{
                "id": "probe_iface_out",
                "type": "shell",
                "target_id": project["target_ids"][0],
                "timeout_s": 20,
                "script": f"ip -o link show\nip route\nprintf '\\nKNOWN_IFACE_IN={iface_in}\\n'\n",
            }])

        return ActionIR()

    def _ask_master_after_probe(self, llm_conn: dict, plan_ir: PlaybookIR, result: dict, project: dict, ev_ref: str) -> ActionIR:
        stdout = result.get("stdout", "") or ""
        known_inputs = plan_ir.inputs or {}
        unknowns = set(plan_ir.unknowns)
    
        # 1) iface_in 미해결 상태면 iface_in부터 판단
        if "iface_in" in unknowns and "iface_in" not in known_inputs:
            if "ens33" in stdout:
                return ActionIR(
                    resolved_inputs={"iface_in": "ens33"},
                    input_rationales={"iface_in": "Probe output contains interface ens33"},
                    evidence_map={"iface_in": [ev_ref]},
                )

            if "eth0" in stdout:
                return ActionIR(
                    resolved_inputs={"iface_in": "eth0"},
                    input_rationales={"iface_in": "Probe output contains interface eth0"},
                    evidence_map={"iface_in": [ev_ref]},
                )

            return ActionIR(question={
                "type": "fact",
                "field": "iface_in",
                "text": "내부망 인터페이스 선택해줘",
                "choices": [],
            })

        # 2) iface_in 은 이미 있고 iface_out 미해결이면 iface_out 판단
        if "iface_out" in unknowns and "iface_out" not in known_inputs:
            iface_in = known_inputs.get("iface_in")

            candidates = []
            for line in stdout.splitlines():
                line = line.strip()
                if not line or ": lo:" in line:
                    continue
                if ": " in line:
                    name = line.split(": ", 1)[1].split("@", 1)[0].strip()
                    if name and name != iface_in and name != "lo":
                        candidates.append(name)

            candidates = list(dict.fromkeys(candidates))

            if len(candidates) == 1:
                return ActionIR(
                    resolved_inputs={"iface_out": candidates[0]},
                    input_rationales={"iface_out": f"Selected remaining interface except iface_in={iface_in}"},
                    evidence_map={"iface_out": [ev_ref]},
                )

            if len(candidates) >= 2:
                return ActionIR(question={
                    "type": "fact",
                    "field": "iface_out",
                    "text": f"외부망 인터페이스 선택해줘 (iface_in={iface_in} 제외)",
                    "choices": [{"value": c, "label": c} for c in candidates],
                })

            return ActionIR(question={
                "type": "fact",
                "field": "iface_out",
                "text": "외부망 인터페이스 선택해줘",
                "choices": [],
            })

        return ActionIR(
            resolved_inputs={},
            input_rationales={},
            evidence_map={},
        )
