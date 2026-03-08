from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class RunScriptReq(BaseModel):
    run_id: str
    target_id: str
    script: str
    timeout_s: int = 60

@router.post("/a2a/run_script")
def run_script(req: RunScriptReq):
    result = router.runner.run_script(run_id=req.run_id, script=req.script, timeout_s=req.timeout_s)
    return result.model_dump()
