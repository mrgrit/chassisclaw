import json
import uuid
import requests
from pathlib import Path


class SkillRunner:
    def __init__(self, skill_registry, project_store, target_store, subagent_client):
        self.skill_registry = skill_registry
        self.project_store = project_store
        self.target_store = target_store
        self.subagent_client = subagent_client

    def _load_inputs_schema(self, skill_id: str) -> dict | None:
        skill_dir = Path("skills") / skill_id
        schema_file = skill_dir / "inputs.schema.json"
        if not schema_file.exists():
            return None
        return json.loads(schema_file.read_text(encoding="utf-8"))

    def _validate_required_inputs(self, skill_id: str, inputs: dict) -> list[str]:
        schema = self._load_inputs_schema(skill_id)
        if not schema:
            return []
        required = schema.get("required", []) or []
        return [k for k in required if k not in inputs or inputs.get(k) in (None, "")]

    def _check_target_existence(self, inputs: dict) -> dict:
        result = {"ok": True, "missing_targets": [], "found_targets": []}
        for key in ("node_a_target_id", "node_b_target_id"):
            target_id = inputs.get(key)
            if not target_id:
                continue
            target = self.target_store.get(target_id)
            if target:
                result["found_targets"].append(target_id)
            else:
                result["missing_targets"].append(target_id)
        if result["missing_targets"]:
            result["ok"] = False
        return result

    def _get_target(self, target_id: str) -> dict | None:
        return self.target_store.get(target_id)

    def _probe_target(self, target: dict) -> dict:
        base_url = target["base_url"].rstrip("/")
        out = {
            "target_id": target["id"],
            "base_url": base_url,
            "health": None,
            "capabilities": None,
            "ok": False,
            "errors": [],
        }

        try:
            r = requests.get(f"{base_url}/health", timeout=5)
            out["health"] = {"status_code": r.status_code, "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text}
        except Exception as e:
            out["errors"].append(f"health_error: {e}")

        try:
            r = requests.get(f"{base_url}/capabilities", timeout=5)
            out["capabilities"] = {"status_code": r.status_code, "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text}
        except Exception as e:
            out["errors"].append(f"capabilities_error: {e}")

        out["ok"] = bool(
            out["health"] and out["health"]["status_code"] < 500
        ) or bool(
            out["capabilities"] and out["capabilities"]["status_code"] < 500
        )
        identity = self._check_target_identity(target["id"], out)
        out["identity"] = identity

        return out

    def run_stub(self, project_id: str, skill_id: str, inputs: dict) -> dict:
        project = self.project_store.get(project_id)
        if not project:
            return {"ok": False, "error": "project_not_found"}

        skill = self.skill_registry.get_skill(skill_id)
        if not skill:
            return {"ok": False, "error": "skill_not_found"}

        plan_template = self.skill_registry.get_plan_template(skill_id)
        if not plan_template:
            return {"ok": False, "error": "plan_template_not_found"}

        missing = self._validate_required_inputs(skill_id, inputs)
        if missing:
            return {"ok": False, "error": "missing_required_inputs", "missing": missing}

        target_check = self._check_target_existence(inputs)

        plan_ir = project.get("plan_ir", {}) or {}
        plan_ir["goal"] = project.get("request_text", "")
        plan_ir["selected_skill"] = skill_id
        plan_ir["unknowns"] = []
        plan_ir["input_rationales"] = plan_ir.get("input_rationales", {}) or {}
        plan_ir["evidence_map"] = plan_ir.get("evidence_map", {}) or {}
        plan_ir["skill_inputs"] = inputs
        plan_ir["candidate_playbooks"] = [skill_id]
        plan_ir["plan"] = {
            "skill_id": skill_id,
            "jobs": plan_template.get("jobs", []),
            "expected_artifacts": plan_template.get("expected_artifacts", []),
            "precheck": target_check,
            "job_results": [],
        }

        current_inputs = plan_ir.get("inputs", {}) or {}
        current_inputs.update(inputs)
        plan_ir["inputs"] = current_inputs

        plan_ir["unknowns"] = []

        project["plan_ir"] = plan_ir
        project["selected_skill"] = skill_id

        if target_check["ok"]:
            project["status"] = "planned"
            project["stage"] = "plan"
            project["resolution"] = {}
            project["answers"] = project.get("answers", {}) or {}
            project["approvals"] = project.get("approvals", {}) or {}
        else:
            project["status"] = "needs_clarification"
            project["stage"] = "plan"
            project["resolution"] = {
                "mode": "ASK",
                "resolved_inputs": {},
                "question": {
                    "type": "fact",
                    "field": "missing_target_ids",
                    "text": f"등록되지 않은 타겟이 있음: {', '.join(target_check['missing_targets'])}",
                    "choices": [],
                },
                "approval_request": None,
                "rationale": "Target existence precheck failed",
                "evidence_map": {},
                "evidence_refs": [],
            }

        self.project_store.save(project_id, project)
        return {
            "ok": True,
            "project_id": project_id,
            "selected_skill": skill_id,
            "plan": plan_ir["plan"],
            "remaining_unknowns": plan_ir.get("unknowns", []),
            "status": project["status"],
            "stage": project["stage"],
        }

    def execute_stub(self, project_id: str, skill_id: str) -> dict:
        project = self.project_store.get(project_id)
        if not project:
            return {"ok": False, "error": "project_not_found"}

        if project.get("selected_skill") != skill_id:
            return {"ok": False, "error": "selected_skill_mismatch"}

        plan_ir = project.get("plan_ir", {}) or {}
        plan = plan_ir.get("plan", {}) or {}
        jobs = plan.get("jobs", []) or []
        skill_inputs = plan_ir.get("skill_inputs", {}) or {}

        job_results = []
        for job in jobs:
            job_type = job.get("type")
            job_id = job.get("id")

            if job_type == "precheck":
                job_results.append({
                    "job_id": job_id,
                    "type": job_type,
                    "ok": bool(plan.get("precheck", {}).get("ok")),
                    "result": plan.get("precheck", {}),
                })
                continue

            if job_type == "probe":
                target_input = job.get("target_input")
                target_id = skill_inputs.get(target_input)
                target = self._get_target(target_id) if target_id else None

                if not target:
                    job_results.append({
                        "job_id": job_id,
                        "type": job_type,
                        "ok": False,
                        "error": "target_not_found",
                        "target_id": target_id,
                    })
                    continue

                probe_result = self._probe_target(target)
                job_results.append({
                    "job_id": job_id,
                    "type": job_type,
                    "ok": probe_result["ok"],
                    "target_id": target_id,
                    "result": probe_result,
                })
                continue

            if job_type == "decision":
                decision_summary = self._build_decision_summary(job_results)
                job_results.append({
                    "job_id": job_id,
                    "type": job_type,
                    "ok": True,
                    "result": decision_summary,
                })
                continue

            if job_type == "install":
                decision_job = next((j for j in job_results if j.get("type") == "decision"), None)
                decision_result = decision_job.get("result", {}) if decision_job else {}
                approved = bool((project.get("approvals", {}) or {}).get("install_subagent", False))

                install_result = self._build_install_stub_result(decision_result, approved)

                if install_result.get("mode") == "approved_install_plan":
                    self._store_install_artifact(project, install_result)

                    execution_result = self._execute_install_actions(install_result.get("plans", []))
                    self._store_install_execution_artifact(project, execution_result)

                    merged_result = {
                        **install_result,
                        "execution": execution_result,
                    }

                    job_results.append({
                        "job_id": job_id,
                        "type": job_type,
                        "ok": execution_result.get("ok", False),
                        "result": merged_result,
                    })
                else:
                    job_results.append({
                        "job_id": job_id,
                        "type": job_type,
                        "ok": install_result.get("ok", False),
                        "result": install_result,
                    })
                continue

            if job_type == "report":
                job_results.append({
                    "job_id": job_id,
                    "type": job_type,
                    "ok": True,
                    "result": "summary_will_be_generated_after_jobs",
                })
                continue

            job_results.append({
                "job_id": job_id,
                "type": job_type,
                "ok": False,
                "error": "unsupported_job_type",
            })

        plan["job_results"] = job_results
        plan_ir["plan"] = plan
        project["plan_ir"] = plan_ir
        project["artifacts"] = project.get("artifacts", []) or []

        all_prechecks_ok = all(j.get("ok", False) for j in job_results if j.get("type") == "precheck")
        probe_results = [j for j in job_results if j.get("type") == "probe"]
        probes_ok = all(j.get("ok", False) for j in probe_results) if probe_results else False

        summary = self._build_onboarding_summary(project, job_results)
        self._store_summary_artifact(project, summary)

        failure_summary = summary.get("failure_summary") or {}
        if failure_summary.get("has_failures"):
            transition = self._decide_failure_transition(failure_summary)
            project["status"] = transition["status"]
            project["stage"] = transition["stage"]
            project["resolution"] = transition.get("resolution", {})
            self.project_store.save(project_id, project)
            return {
                "ok": True,
                "project_id": project_id,
                "status": project["status"],
                "stage": project["stage"],
                "job_results": job_results,
                "summary": summary,
                "failure_transition": transition,
            }

        decision_job = next((j for j in job_results if j.get("type") == "decision"), None)
        decision_result = decision_job.get("result", {}) if decision_job else {}
        overall_decision = decision_result.get("overall_decision")

        identity_mismatch = any(
            isinstance(t.get("identity"), dict) and t["identity"].get("matched") is False
            for t in (summary.get("targets", []) or [])
        )

        if identity_mismatch:
            project["status"] = "needs_clarification"
            project["stage"] = "resolve"
            project["resolution"] = {
                "mode": "ASK",
                "resolved_inputs": {},
                "question": {
                    "type": "fact",
                    "field": "target_identity_mapping",
                    "text": "요청한 target_id와 실제 응답한 agent_id가 일치하지 않음. 타겟 매핑을 확인해야 함.",
                    "choices": [],
                },
                "approval_request": None,
                "rationale": "Target identity mismatch detected during probe.",
                "evidence_map": {},
                "evidence_refs": [],
            }
            self.project_store.save(project_id, project)
            return {
                "ok": True,
                "project_id": project_id,
                "status": project["status"],
                "stage": project["stage"],
                "job_results": job_results,
                "summary": summary,
            }

        if all_prechecks_ok and probes_ok:
            project["resolution"] = {}

            if overall_decision == "approval_needed":
                approved = bool((project.get("approvals", {}) or {}).get("install_subagent", False))
                if approved:
                    project["status"] = "planned"
                    project["stage"] = "report"
                else:
                    project["status"] = "needs_approval"
                    project["stage"] = "resolve"
                    project["resolution"] = {
                        "mode": "APPROVAL",
                        "resolved_inputs": {},
                        "question": None,
                        "approval_request": {
                            "field": "install_subagent",
                            "text": f"다음 타겟에 subagent/bootstrap 설치 승인이 필요함: {', '.join(decision_result.get('needs_approval_targets', []))}",
                            "risk": "high",
                        },
                        "rationale": "Decision stub determined that installation approval is required.",
                        "evidence_map": {},
                        "evidence_refs": [],
                    }
            else:
                project["status"] = "planned"
                project["stage"] = "report"

        elif not all_prechecks_ok:
            project["status"] = "needs_clarification"
            project["stage"] = "plan"
        else:
            project["status"] = "needs_clarification"
            project["stage"] = "resolve"

        self.project_store.save(project_id, project)
        return {
            "ok": True,
            "project_id": project_id,
            "status": project["status"],
            "stage": project["stage"],
            "job_results": job_results,
            "summary": summary,
        }

    def _build_onboarding_summary(self, project: dict, job_results: list[dict]) -> dict:
        precheck = next((j for j in job_results if j.get("type") == "precheck"), None)
        probe_jobs = [j for j in job_results if j.get("type") == "probe"]
        decision_job = next((j for j in job_results if j.get("type") == "decision"), None)
        install_job = next((j for j in job_results if j.get("type") == "install"), None)

        summary = {
            "project_id": project["id"],
            "selected_skill": project.get("selected_skill"),
            "precheck_ok": bool(precheck and precheck.get("ok")),
            "targets": [],
            "decision": decision_job.get("result") if decision_job else None,
            "install": install_job.get("result") if install_job else None,
            "artifacts": [],
            "overall_status": "unknown",
            "blockers": [],
            "next_actions": [],
            "action_plan_ready": False,
            "execution_ready": False,
            "execution_ok": None,
            "failure_summary": None,
            "remediation_suggestions": [],
            "bootstrap_targets": [],
            "post_install_health": [],
        }

        for job in probe_jobs:
            result = job.get("result", {}) or {}
            summary["targets"].append({
                "target_id": job.get("target_id"),
                "ok": job.get("ok", False),
                "health": result.get("health"),
                "capabilities": result.get("capabilities"),
                "identity": result.get("identity"),
                "errors": result.get("errors", []),
            })

        if not summary["precheck_ok"]:
            summary["overall_status"] = "blocked"
            summary["blockers"].append("target_precheck_failed")
            summary["next_actions"].append("Register missing targets and rerun the skill.")
            return summary

        failed_targets = [t["target_id"] for t in summary["targets"] if not t.get("ok")]
        if failed_targets:
            summary["overall_status"] = "partial"
            summary["blockers"].append(f"probe_failed:{', '.join(failed_targets)}")
            summary["next_actions"].append("Check target health/capabilities connectivity and rerun.")
            return summary

        identity_mismatch_targets = [
            t["target_id"]
            for t in summary["targets"]
            if isinstance(t.get("identity"), dict) and t["identity"].get("matched") is False
        ]

        if identity_mismatch_targets:
            summary["blockers"].append(f"identity_mismatch:{', '.join(identity_mismatch_targets)}")
            summary["next_actions"].append("Review target mapping because reported agent identity does not match requested target id.")

        decision = summary.get("decision") or {}
        overall_decision = decision.get("overall_decision")

        install_result = summary.get("install") or {}
        install_mode = install_result.get("mode")

        if overall_decision == "manual_action_needed":
            summary["overall_status"] = "manual_action_needed"
            summary["next_actions"].append("Prepare manual bootstrap path for targets lacking installation prerequisites.")
        elif overall_decision == "approval_needed":
            if install_mode == "approved_install_plan":
                summary["overall_status"] = "install_planned"
                summary["next_actions"].append("Installation stub plan created after approval.")
            else:
                summary["overall_status"] = "approval_needed"
                summary["next_actions"].append("Request approval for subagent/bootstrap installation on required targets.")
        else:
            summary["overall_status"] = "ready"
            summary["next_actions"].append("No installation blocker detected for currently reachable targets.")

        summary["next_actions"].append("Proceed to detailed onboarding execution in later milestones.")

        if summary.get("install") and summary["install"].get("mode") == "approved_install_plan":
            summary["artifacts"].append("install_subagent_plan.json")

        install_info = summary.get("install") or {}
        plans = install_info.get("plans", []) or []
        execution = install_info.get("execution", {}) or {}

        if any(p.get("actions") for p in plans):
            summary["action_plan_ready"] = True

        if execution:
            summary["execution_ready"] = True
            summary["execution_ok"] = execution.get("ok")
            summary["failure_summary"] = execution.get("failure_summary")

            if execution.get("ok"):
                summary["next_actions"].append("Install action plan executed successfully in stub flow.")
            else:
                summary["blockers"].append("install_execution_failed")

                failure_summary = execution.get("failure_summary", {}) or {}
                for item in failure_summary.get("items", []) or []:
                    suggestion = item.get("suggested_next_action")
                    if suggestion and suggestion not in summary["remediation_suggestions"]:
                        summary["remediation_suggestions"].append(suggestion)

                summary["next_actions"].append("Review install_subagent_execution artifact and fix failing steps.")

            executed_targets = execution.get("executed_targets", []) or []
        failed_health_rechecks = [
            x.get("target_id")
            for x in executed_targets
            if not (x.get("health_recheck", {}) or {}).get("ok", False)
        ]
        if failed_health_rechecks:
            summary["blockers"].append(
                f"post_install_health_check_failed:{', '.join(failed_health_rechecks)}"
            )
            summary["remediation_suggestions"].append(
                "Review install logs and verify the subagent process/service is running before retrying."
            )

        for x in executed_targets:
            if x.get("health_recheck") is not None:
                summary["post_install_health"].append(x["health_recheck"])

        install_info = summary.get("install") or {}
        for plan in install_info.get("plans", []) or []:
            summary["bootstrap_targets"].append({
                "target_id": plan.get("target_id"),
                "package_manager": plan.get("package_manager"),
                "health_check_url": plan.get("health_check_url"),
                "bootstrap_mode": plan.get("bootstrap_mode"),
            })

        return summary


    def _store_summary_artifact(self, project: dict, summary: dict) -> None:
        artifacts = project.get("artifacts", []) or []
        artifacts = [a for a in artifacts if a.get("type") != "onboarding_summary"]
        artifacts.append({
            "type": "onboarding_summary",
            "name": "onboarding_summary.json",
            "data": summary,
        })
        project["artifacts"] = artifacts

    def _decide_subagent_install_for_target(self, probe_job_result: dict) -> dict:
        target_id = probe_job_result.get("target_id")
        result = probe_job_result.get("result", {}) or {}

        health = result.get("health", {}) or {}
        capabilities = result.get("capabilities", {}) or {}

        health_body = health.get("body", {}) if isinstance(health.get("body"), dict) else {}
        capabilities_body = capabilities.get("body", {}) if isinstance(capabilities.get("body"), dict) else {}

        health_ok = bool(health and int(health.get("status_code", 0) or 0) < 400 and health_body.get("ok") is True)
        package_manager = capabilities_body.get("package_manager")
        python_value = capabilities_body.get("python")
        sudo_value = capabilities_body.get("sudo")

        '''        
        if health_ok:
            return {
                "target_id": target_id,
                "decision": "already_present",
                "needs_approval": False,
                "reason": "Subagent health endpoint already responds successfully.",
                "recommended_next_action": "Skip installation and continue onboarding.",
            }
        '''
        if health_ok:
            return {
                "target_id": target_id,
                "decision": "installable_with_approval",
                "needs_approval": True,
                "reason": "TEST MODE: force approval flow even though subagent health responds successfully.",
                "recommended_next_action": "Request approval and prepare bootstrap/subagent installation.",
                "capability_hints": {
                    "package_manager": package_manager,
                    "python": python_value,
                    "sudo": sudo_value,
                },
            }

        if package_manager and python_value:
            return {
                "target_id": target_id,
                "decision": "installable_with_approval",
                "needs_approval": True,
                "reason": f"Subagent health is unavailable, but package manager={package_manager} and python={python_value} are present.",
                "recommended_next_action": "Request approval and prepare bootstrap/subagent installation.",
                "capability_hints": {
                    "package_manager": package_manager,
                    "python": python_value,
                    "sudo": sudo_value,
                },
            }

        return {
            "target_id": target_id,
            "decision": "manual_bootstrap_needed",
            "needs_approval": True,
            "reason": "Subagent is not reachable and installation prerequisites are incomplete or unknown.",
            "recommended_next_action": "Collect more environment facts or perform manual bootstrap preparation.",
            "capability_hints": {
                "package_manager": package_manager,
                "python": python_value,
                "sudo": sudo_value,
            },
        }


    def _build_decision_summary(self, job_results: list[dict]) -> dict:
        probe_jobs = [j for j in job_results if j.get("type") == "probe"]
        per_target = [self._decide_subagent_install_for_target(j) for j in probe_jobs]

        needs_approval_targets = [x["target_id"] for x in per_target if x.get("needs_approval")]
        already_present_targets = [x["target_id"] for x in per_target if x.get("decision") == "already_present"]
        manual_targets = [x["target_id"] for x in per_target if x.get("decision") == "manual_bootstrap_needed"]

        overall = "ready"
        if manual_targets:
            overall = "manual_action_needed"
        elif needs_approval_targets:
            overall = "approval_needed"

        return {
            "overall_decision": overall,
            "already_present_targets": already_present_targets,
            "needs_approval_targets": needs_approval_targets,
            "manual_bootstrap_targets": manual_targets,
            "per_target": per_target,
        }

    def _build_install_stub_result(self, decision_result: dict, approved: bool) -> dict:
        needs_targets = decision_result.get("needs_approval_targets", []) or []
        manual_targets = decision_result.get("manual_bootstrap_targets", []) or []
        per_target = decision_result.get("per_target", []) or []

        if not needs_targets and not manual_targets:
            return {
                "ok": True,
                "mode": "skip",
                "reason": "No installation-required targets detected.",
                "targets": [],
                "plans": [],
            }

        if not approved:
            return {
                "ok": False,
                "mode": "blocked",
                "reason": "Approval not granted for install_subagent.",
                "targets": needs_targets + manual_targets,
                "plans": [],
            }

        plans = []

        for item in per_target:
            target_id = item.get("target_id")
            decision = item.get("decision")
            hints = item.get("capability_hints", {}) or {}

            package_manager = hints.get("package_manager") or "unknown"
            python_value = hints.get("python")
            sudo_value = hints.get("sudo")

            if decision == "installable_with_approval":
                install_script = self._render_install_stub_script(
                    package_manager=package_manager,
                    python_value=python_value,
                    needs_sudo=bool(sudo_value),
                )
                plans.append({
                    "target_id": target_id,
                    "action": "prepare_install_stub",
                    "status": "planned",
                    "reason": "Approval granted; installation stub can proceed in later milestones.",
                    "package_manager": package_manager,
                    "python": python_value,
                    "needs_sudo": bool(sudo_value),
                    "install_script": install_script,
                    "actions": self._build_install_actions(target_id, install_script),
                    "bootstrap_mode": "systemd_or_background",
                    "health_check_url": "http://127.0.0.1:55123/health",
                    "notes": [
                        "This is a generated install stub, not a live execution result.",
                        "Later milestones should convert this plan into an executable tool action.",
                    ],
                })

            elif decision == "manual_bootstrap_needed":
                plans.append({
                    "target_id": target_id,
                    "action": "prepare_install_stub",
                    "status": "planned",
                    "reason": "Approval granted; installation stub can proceed in later milestones.",
                    "package_manager": package_manager,
                    "python": python_value,
                    "needs_sudo": bool(sudo_value),
                    "install_script": install_script,
                    "actions": self._build_install_actions(target_id, install_script),
                    "notes": [
                        "This is a generated install stub, not a live execution result.",
                        "The actions array is the next-step execution plan for later milestones.",
                    ],
                })

        return {
            "ok": True,
            "mode": "approved_install_plan",
            "targets": needs_targets + manual_targets,
            "plans": plans,
        }

    def approve_stub(self, project_id: str, skill_id: str, approved: bool) -> dict:
        project = self.project_store.get(project_id)
        if not project:
            return {"ok": False, "error": "project_not_found"}

        if project.get("selected_skill") != skill_id:
            return {"ok": False, "error": "selected_skill_mismatch"}

        approvals = project.get("approvals", {}) or {}
        approvals["install_subagent"] = approved
        project["approvals"] = approvals

        if approved:
            project["status"] = "planned"
            project["stage"] = "execute"
            project["resolution"] = {}
        else:
            project["status"] = "needs_clarification"
            project["stage"] = "resolve"

        self.project_store.save(project_id, project)
        return {
            "ok": True,
            "project_id": project_id,
            "approved": approved,
            "status": project["status"],
            "stage": project["stage"],
        }
    def _render_install_stub_script(self, package_manager: str, python_value: str | None, needs_sudo: bool) -> str:
        sudo_prefix = "sudo " if needs_sudo else ""

        if package_manager == "apt":
            install_pkg = f"{sudo_prefix}apt-get update && {sudo_prefix}apt-get install -y python3 curl ca-certificates"
        elif package_manager == "dnf":
            install_pkg = f"{sudo_prefix}dnf install -y python3 curl ca-certificates"
        elif package_manager == "yum":
            install_pkg = f"{sudo_prefix}yum install -y python3 curl ca-certificates"
        elif package_manager == "apk":
            install_pkg = f"{sudo_prefix}apk add --no-cache python3 curl ca-certificates"
        else:
            install_pkg = "# TODO: detect/install prerequisites manually"

        service_block = f"""{sudo_prefix}mkdir -p /opt/chassisclaw/subagent
    cat > /tmp/chassisclaw-subagent-placeholder.py <<'PYEOF'
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import json
    import os

    AGENT_ID = os.environ.get("CHASSISCLAW_AGENT_ID", "bootstrap-agent")

    class H(BaseHTTPRequestHandler):
        def _send(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self._send({{"ok": True, "agent_id": AGENT_ID, "service": "chassisclaw-subagent-bootstrap"}})
                return
            self._send({{"ok": False, "error": "not_found"}}, 404)

    HTTPServer(("0.0.0.0", 55123), H).serve_forever()
    PYEOF

    {sudo_prefix}cp /tmp/chassisclaw-subagent-placeholder.py /opt/chassisclaw/subagent/subagent.py
    """

        systemd_block = f"""if command -v systemctl >/dev/null 2>&1; then
    cat > /tmp/chassisclaw-subagent.service <<'EOF'
    [Unit]
    Description=ChassisClaw SubAgent Placeholder
    After=network.target

    [Service]
    Environment=CHASSISCLAW_AGENT_ID=$(hostname)
    ExecStart=/usr/bin/python3 /opt/chassisclaw/subagent/subagent.py
    Restart=always
    RestartSec=3

    [Install]
    WantedBy=multi-user.target
    EOF

    {sudo_prefix}cp /tmp/chassisclaw-subagent.service /etc/systemd/system/chassisclaw-subagent.service
    {sudo_prefix}systemctl daemon-reload
    {sudo_prefix}systemctl enable --now chassisclaw-subagent.service
    else
    nohup python3 /opt/chassisclaw/subagent/subagent.py >/tmp/chassisclaw-subagent.out 2>/tmp/chassisclaw-subagent.err &
    fi
    """

        verify_block = """sleep 2
    curl -fsS http://127.0.0.1:55123/health || true
    """

        script = f"""#!/usr/bin/env bash
    set -euo pipefail

    echo "[1/5] install prerequisites"
    {install_pkg}

    echo "[2/5] verify python"
    python3 --version || true

    echo "[3/5] place placeholder subagent"
    {service_block}

    echo "[4/5] start service or background process"
    {systemd_block}

    echo "[5/5] verify local health"
    {verify_block}
    """
        return script

    def _store_install_artifact(self, project: dict, install_result: dict) -> None:
        artifacts = project.get("artifacts", []) or []
        artifacts = [a for a in artifacts if a.get("type") != "install_subagent_plan"]
        artifacts.append({
            "type": "install_subagent_plan",
            "name": "install_subagent_plan.json",
            "data": install_result,
        })
        project["artifacts"] = artifacts

    def _build_install_actions(self, target_id: str, install_script: str) -> list[dict]:
        return [
            {
                "id": f"install_subagent_{target_id}",
                "type": "shell",
                "target_id": target_id,
                "timeout_s": 300,
                "script": install_script,
                "expected_artifacts": [
                    "install_stdout.log",
                    "install_stderr.log"
                ],
            }
        ]
    
    def _execute_install_actions(self, plans: list[dict]) -> dict:
        executed = []

        for plan in plans:
            target_id = plan.get("target_id")
            actions = plan.get("actions", []) or []
            target = self.target_store.get(target_id)

            if not target:
                executed.append({
                    "target_id": target_id,
                    "ok": False,
                    "error": "target_not_found",
                    "results": [],
                })
                continue

            action_results = []
            all_ok = True

            for action in actions:
                result = self.subagent_client.run_script(
                    base_url=target["base_url"],
                    run_id=f"run_{uuid.uuid4().hex[:8]}",
                    target_id=target_id,
                    script=action.get("script", ""),
                    timeout_s=int(action.get("timeout_s", 300)),
                )

                item = result.model_dump() if hasattr(result, "model_dump") else result
                classification = self._classify_execution_failure(item)

                action_results.append({
                    "action_id": action.get("id"),
                    "result": item,
                    "classification": classification,
                })

                exit_code = item.get("exit_code", 1)
                if exit_code != 0:
                    all_ok = False

            health_recheck = self._recheck_subagent_health(target_id)

            executed.append({
                "target_id": target_id,
                "ok": all_ok and health_recheck.get("ok", False),
                "results": action_results,
                "health_recheck": health_recheck,
            })

        overall_ok = all(x.get("ok", False) for x in executed) if executed else False
        failure_summary = self._summarize_execution_failures(executed)

        return {
            "ok": overall_ok,
            "mode": "executed",
            "executed_targets": executed,
            "failure_summary": failure_summary,
        }

    def _store_install_execution_artifact(self, project: dict, execution_result: dict) -> None:
        artifacts = project.get("artifacts", []) or []
        artifacts = [a for a in artifacts if a.get("type") != "install_subagent_execution"]
        artifacts.append({
            "type": "install_subagent_execution",
            "name": "install_subagent_execution.json",
            "data": execution_result,
        })
        project["artifacts"] = artifacts

    def _classify_execution_failure(self, result: dict) -> dict:
        exit_code = int(result.get("exit_code", 0) or 0)
        stdout = (result.get("stdout", "") or "").lower()
        stderr = (result.get("stderr", "") or "").lower()
        text = f"{stdout}\n{stderr}"

        if exit_code == 0:
            return {
                "failure_type": None,
                "reason": "success",
                "suggested_next_action": "No action needed.",
            }

        if "command not found" in text or exit_code == 127:
            return {
                "failure_type": "command_not_found",
                "reason": "Required command is not available in the target environment.",
                "suggested_next_action": "Decide whether to install the missing tool, use an alternative command, or ask for approval.",
            }

        if "permission denied" in text or "not permitted" in text:
            return {
                "failure_type": "permission_denied",
                "reason": "Command requires higher privileges or target permissions are insufficient.",
                "suggested_next_action": "Request approval for elevated execution or adjust privilege strategy.",
            }

        if "timeout" in text or "timed out" in text:
            return {
                "failure_type": "timeout",
                "reason": "Execution exceeded the expected time budget or remote command stalled.",
                "suggested_next_action": "Retry with adjusted timeout, simplify the action, or probe connectivity first.",
            }

        if "network is unreachable" in text or "name or service not known" in text or "connection reset" in text:
            return {
                "failure_type": "network_unreachable",
                "reason": "Target connectivity or name resolution failed during execution.",
                "suggested_next_action": "Check connectivity, DNS, routing, or proxy/network policy before retrying.",
            }

        if "apt-get: not found" in text or "dnf: not found" in text or "yum: not found" in text or "apk: not found" in text:
            return {
                "failure_type": "package_manager_missing",
                "reason": "Expected package manager is not available on the target.",
                "suggested_next_action": "Probe the environment again to detect the correct package manager or prepare manual bootstrap.",
            }

        if "python3: not found" in text or "python: not found" in text:
            return {
                "failure_type": "python_missing",
                "reason": "Python runtime required by the plan is not available.",
                "suggested_next_action": "Install Python if approved, or switch to a shell-only bootstrap path.",
            }

        return {
            "failure_type": "unknown_failure",
            "reason": "Execution failed but did not match a known failure pattern.",
            "suggested_next_action": "Inspect stderr/stdout and create a targeted remediation or fallback plan.",
        }


    def _summarize_execution_failures(self, executed_targets: list[dict]) -> dict:
        items = []
        seen_types = []

        for target in executed_targets:
            target_id = target.get("target_id")
            for action_item in target.get("results", []) or []:
                result = action_item.get("result", {}) or {}
                classified = self._classify_execution_failure(result)
                failure_type = classified.get("failure_type")
                if failure_type:
                    items.append({
                        "target_id": target_id,
                        "action_id": action_item.get("action_id"),
                        "failure_type": failure_type,
                        "reason": classified.get("reason"),
                        "suggested_next_action": classified.get("suggested_next_action"),
                    })
                    if failure_type not in seen_types:
                        seen_types.append(failure_type)

        return {
            "has_failures": bool(items),
            "failure_types": seen_types,
            "items": items,
        }

    def _decide_failure_transition(self, failure_summary: dict) -> dict:
        failure_types = failure_summary.get("failure_types", []) or []

        if not failure_types:
            return {
                "status": "planned",
                "stage": "report",
                "resolution": {},
            }

        if "permission_denied" in failure_types:
            return {
                "status": "needs_approval",
                "stage": "resolve",
                "resolution": {
                    "mode": "APPROVAL",
                    "resolved_inputs": {},
                    "question": None,
                    "approval_request": {
                        "field": "elevated_execution",
                        "text": "설치 실행에 더 높은 권한이 필요함. 권한 상승 또는 sudo 사용 승인이 필요함.",
                        "risk": "high",
                    },
                    "rationale": "Install execution failed with permission_denied.",
                    "evidence_map": {},
                    "evidence_refs": [],
                },
            }

        if "command_not_found" in failure_types or "package_manager_missing" in failure_types or "python_missing" in failure_types:
            return {
                "status": "needs_clarification",
                "stage": "resolve",
                "resolution": {
                    "mode": "ASK",
                    "resolved_inputs": {},
                    "question": {
                        "type": "fact",
                        "field": "bootstrap_strategy",
                        "text": "대상 환경에 필요한 명령/패키지가 없음. 도구 설치, 대체 도구 사용, 수동 부트스트랩 중 어떤 전략으로 진행할지 결정 필요.",
                        "choices": [
                            {"value": "install_missing_tools", "label": "누락 도구 설치"},
                            {"value": "use_alternative_tools", "label": "대체 도구 사용"},
                            {"value": "manual_bootstrap", "label": "수동 부트스트랩"},
                        ],
                    },
                    "approval_request": None,
                    "rationale": "Install execution failed due to missing environment prerequisites.",
                    "evidence_map": {},
                    "evidence_refs": [],
                },
            }

        if "timeout" in failure_types or "network_unreachable" in failure_types:
            return {
                "status": "replan",
                "stage": "replan",
                "resolution": {},
            }

        return {
            "status": "replan",
            "stage": "replan",
            "resolution": {},
        }

    def _check_target_identity(self, requested_target_id: str, probe_result: dict) -> dict:
        health = probe_result.get("health", {}) or {}
        body = health.get("body", {}) if isinstance(health.get("body"), dict) else {}

        reported_agent_id = body.get("agent_id")
        matched = (reported_agent_id == requested_target_id) if reported_agent_id else None

        return {
            "requested_target_id": requested_target_id,
            "reported_agent_id": reported_agent_id,
            "matched": matched,
        }


    def _recheck_subagent_health(self, target_id: str) -> dict:
        target = self.target_store.get(target_id)
        if not target:
            return {
                "target_id": target_id,
                "ok": False,
                "error": "target_not_found",
            }

        base_url = target["base_url"].rstrip("/")
        try:
            r = requests.get(f"{base_url}/health", timeout=5)
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
            return {
                "target_id": target_id,
                "ok": r.status_code < 400,
                "status_code": r.status_code,
                "body": body,
            }
        except Exception as e:
            return {
                "target_id": target_id,
                "ok": False,
                "error": str(e),
            }
    