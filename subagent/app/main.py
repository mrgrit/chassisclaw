from fastapi import FastAPI
from app.api.run_script import router as run_script_router
from app.api.capabilities import router as capabilities_router
from app.services.runner import Runner

app = FastAPI(title="ChassisClaw SubAgent", version="m1")

runner = Runner()
run_script_router.runner = runner

app.include_router(run_script_router)
app.include_router(capabilities_router)

@app.get("/health")
def health():
    return {"ok": True, "agent_id": "local-agent-1", "service": "chassisclaw-subagent"}
