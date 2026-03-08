from fastapi import APIRouter, HTTPException
router = APIRouter()

@router.post("/projects/{project_id}/answer")
def answer_project(project_id: str, body: dict):
    project = router.project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    answers = project.get("answers", {})
    answers.update(body.get("answers", {}))
    project["answers"] = answers
    router.project_store.save(project_id, project)
    router.audit_service.append(project_id, "ANSWER_SET", {"answers": body.get("answers", {})})
    return {"ok": True, "answers": answers}
