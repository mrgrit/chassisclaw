import uuid
from fastapi import APIRouter, HTTPException
from app.models.project import CreateProjectReq

router = APIRouter()

@router.post("/projects")
def create_project(req: CreateProjectReq):
    project_id = f"prj_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": project_id,
        "name": req.name,
        "request_text": req.request_text,
        "status": "created",
        "stage": "plan",
        "target_ids": req.target_ids,
        "answers": {},
        "approvals": {},
        "plan_ir": {
            "goal": req.request_text,
            "unknowns": [],
            "inputs": {},
            "input_rationales": {},
            "evidence_map": {},
            "answers": {},
            "approvals": {},
            "plan": {"jobs": [], "steps": []}
        },
        "resolution": {},
        "artifacts": [],
    }
    router.project_store.create(project_id, payload)
    router.audit_service.append(project_id, "PROJECT_CREATED", {"name": req.name})
    return {"project_id": project_id, "state": payload}

@router.get("/projects")
def list_projects():
    return {"items": router.project_store.list()}

@router.get("/projects/{project_id}")
def get_project(project_id: str):
    st = router.project_store.get(project_id)
    if not st:
        raise HTTPException(status_code=404, detail="project not found")
    return st
