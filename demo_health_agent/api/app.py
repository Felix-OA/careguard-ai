from fastapi import FastAPI, Query

from careguard.models.schemas import NormalizedRequest, NormalizedResponse
from demo_health_agent.engine import respond
from demo_health_agent.retrieval import retrieve

app = FastAPI(title="CareGuard Synthetic Demo Health Agent", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "synthetic_data_only": True}


@app.post("/chat", response_model=NormalizedResponse)
def chat(request: NormalizedRequest) -> NormalizedResponse:
    return respond(request)


@app.get("/debug/retrieval")
def debug_retrieval(q: str = Query("")) -> dict:
    return {"query": q, "sources": retrieve(q), "warning": "synthetic local debug endpoint"}

