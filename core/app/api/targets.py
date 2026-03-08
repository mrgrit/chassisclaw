from fastapi import APIRouter, HTTPException
from app.models.target import TargetUpsertReq

router = APIRouter()

@router.get("/targets")
def list_targets():
    return {"items": router.target_store.list()}

@router.get("/targets/{target_id}")
def get_target(target_id: str):
    t = router.target_store.get(target_id)
    if not t:
        raise HTTPException(status_code=404, detail="target not found")
    return t

@router.post("/targets")
def upsert_target(req: TargetUpsertReq):
    payload = req.model_dump()
    router.target_store.upsert(req.id, payload)
    return payload
