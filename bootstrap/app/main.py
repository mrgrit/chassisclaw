from fastapi import FastAPI
app = FastAPI(title="ChassisClaw Bootstrap")

@app.get("/health")
def health():
    return {"ok": True, "service": "chassisclaw-bootstrap", "status": "placeholder"}
