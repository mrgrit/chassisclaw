from fastapi import APIRouter, HTTPException
router = APIRouter()

@router.post("/projects/{project_id}/approve")
def approve_project(project_id: str, body: dict):
    project = router.project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    approvals = project.get("approvals", {})
    approvals.update(body.get("approvals", {}))
    project["approvals"] = approvals
    router.project_store.save(project_id, project)
    router.audit_service.append(project_id, "APPROVAL_SET", {"approvals": body.get("approvals", {})})
    return {"ok": True, "approvals": approvals}
