from fastapi import APIRouter, HTTPException
from fastapi import Body

router = APIRouter()


@router.get("/skills")
def list_skills():
    return {"skills": router.skill_registry.list_skills()}


@router.get("/skills/{skill_id}")
def get_skill(skill_id: str):
    skill = router.skill_registry.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="skill not found")
    return skill


@router.get("/skills/{skill_id}/plan_template")
def get_skill_plan_template(skill_id: str):
    plan = router.skill_registry.get_plan_template(skill_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan template not found")
    return plan

@router.post("/skills/{skill_id}/run_stub")
def run_skill_stub(skill_id: str, body: dict = Body(...)):
    project_id = body.get("project_id")
    inputs = body.get("inputs", {}) or {}

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    result = router.skill_runner.run_stub(project_id=project_id, skill_id=skill_id, inputs=inputs)

    if not result.get("ok"):
        error = result.get("error")
        if error in ("project_not_found", "skill_not_found", "plan_template_not_found"):
            raise HTTPException(status_code=404, detail=result)
        raise HTTPException(status_code=400, detail=result)

    return result

@router.post("/skills/{skill_id}/execute_stub")
def execute_skill_stub(skill_id: str, body: dict = Body(...)):
    project_id = body.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    result = router.skill_runner.execute_stub(project_id=project_id, skill_id=skill_id)
    if not result.get("ok"):
        error = result.get("error")
        if error in ("project_not_found", "selected_skill_mismatch"):
            raise HTTPException(status_code=404, detail=result)
        raise HTTPException(status_code=400, detail=result)
    return result