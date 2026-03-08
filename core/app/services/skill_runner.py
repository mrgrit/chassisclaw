import json
import requests
from pathlib import Path


class SkillRunner:
    def __init__(self, skill_registry, project_store, target_store):
        self.skill_registry = skill_registry
        self.project_store = project_store
        self.target_store = target_store

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

        decision_job = next((j for j in job_results if j.get("type") == "decision"), None)
        decision_result = decision_job.get("result", {}) if decision_job else {}
        overall_decision = decision_result.get("overall_decision")

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
            "overall_status": "unknown",
            "blockers": [],
            "next_actions": [],
        }

        for job in probe_jobs:
            result = job.get("result", {}) or {}
            summary["targets"].append({
                "target_id": job.get("target_id"),
                "ok": job.get("ok", False),
                "health": result.get("health"),
                "capabilities": result.get("capabilities"),
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
                
        if health_ok:
            return {
                "target_id": target_id,
                "decision": "already_present",
                "needs_approval": False,
                "reason": "Subagent health endpoint already responds successfully.",
                "recommended_next_action": "Skip installation and continue onboarding.",
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

        if not needs_targets and not manual_targets:
            return {
                "ok": True,
                "mode": "skip",
                "reason": "No installation-required targets detected.",
                "targets": [],
            }

        if not approved:
            return {
                "ok": False,
                "mode": "blocked",
                "reason": "Approval not granted for install_subagent.",
                "targets": needs_targets + manual_targets,
            }

        plans = []
        for target_id in needs_targets:
            plans.append({
                "target_id": target_id,
                "action": "prepare_install_stub",
                "status": "planned",
                "reason": "Approval granted; installation stub can proceed in later milestones.",
            })

        for target_id in manual_targets:
            plans.append({
                "target_id": target_id,
                "action": "manual_bootstrap_required",
                "status": "blocked_manual",
                "reason": "Approval granted but prerequisites are insufficient for automatic install.",
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