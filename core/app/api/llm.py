from fastapi import APIRouter
router = APIRouter()

@router.post("/llm/connections")
def register_connection(body: dict):
    conn_id = body["id"]
    return router.llm_registry.register_connection(conn_id, body)

@router.post("/llm/roles")
def bind_role(body: dict):
    router.llm_registry.bind_role(body["role"], body["conn_id"])
    return {"ok": True, "role": body["role"], "conn_id": body["conn_id"]}
