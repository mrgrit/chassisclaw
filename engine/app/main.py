from fastapi import FastAPI
app = FastAPI(title="ChassisClaw Engine")

@app.get("/health")
def health():
    return {"ok": True, "service": "chassisclaw-engine", "status": "placeholder"}
