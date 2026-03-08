from fastapi import APIRouter, HTTPException
from app.models.playbook_ir import PlaybookIR

router = APIRouter()


def _merge_project_state_into_plan(project: dict) -> PlaybookIR:
    raw_plan = project.get("plan_ir") or {}
    if not raw_plan:
        raw_plan = {
            "goal": project.get("request_text", ""),
            "unknowns": ["iface_in", "iface_out"],
        }

    plan_ir = PlaybookIR(**raw_plan)

    answers = project.get("answers", {}) or {}
    approvals = project.get("approvals", {}) or {}
    resolution = project.get("resolution", {}) or {}
    resolved_inputs = resolution.get("resolved_inputs", {}) or {}
    resolution_evidence_map = resolution.get("evidence_map", {}) or {}

    plan_ir.answers.update(answers)
    plan_ir.approvals.update(approvals)

    # 사용자가 직접 답한 값
    for key, value in answers.items():
        if value is None:
            continue
        plan_ir.inputs[key] = value
        plan_ir.input_rationales.setdefault(key, "Provided by user answer")
        plan_ir.evidence_map.setdefault(key, [])

    # 이전 probe에서 자동 해결된 값
    for key, value in resolved_inputs.items():
        if value is None:
            continue
        plan_ir.inputs[key] = value
        plan_ir.input_rationales.setdefault(key, "Resolved automatically from prior probe")
        plan_ir.evidence_map[key] = resolution_evidence_map.get(key, plan_ir.evidence_map.get(key, []))

    # 이미 아는 값은 unknowns에서 제거
    plan_ir.unknowns = [u for u in plan_ir.unknowns if u not in plan_ir.inputs]
    return plan_ir


@router.post("/projects/{project_id}/run_auto")
def run_auto(project_id: str, body: dict):
    project = router.project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    if not project.get("target_ids"):
        raise HTTPException(status_code=400, detail="project has no target_ids")

    target_id = project["target_ids"][0]
    target = router.target_store.get(target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"target not found: {target_id}")

    plan_ir = _merge_project_state_into_plan(project)
    project["plan_ir"] = plan_ir.model_dump()

    project["status"] = "running"
    project["stage"] = "probe"
    router.project_store.save(project_id, project)

    result = router.probe_loop_service.run(
        project=project,
        target=target,
        max_iterations=body.get("max_iterations", 3),
    )

    router.project_store.save(project_id, project)
    return result