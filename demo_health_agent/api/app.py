from ipaddress import ip_address, ip_network

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from careguard.models.schemas import NormalizedRequest, NormalizedResponse
from demo_health_agent.engine import generate, respond
from demo_health_agent.retrieval import retrieve

app = FastAPI(title="CareGuard Synthetic Demo Health Agent", version="0.1.0")


class InternalGenerateRequest(BaseModel):
    request: NormalizedRequest
    context: list[dict]
    execute_tools: bool = False


def _require_local(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host == "testclient":
        return
    try:
        address = ip_address(host)
        docker_network = address.version == 4 and address in ip_network("172.16.0.0/12")
        if address.is_loopback or docker_network:
            return
    except ValueError:
        if host in {"demo-agent", "careguard-guard"}:
            return
    raise HTTPException(403, "internal demo integration is restricted to the local network")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "synthetic_data_only": True}


@app.post("/chat", response_model=NormalizedResponse)
def chat(request: NormalizedRequest) -> NormalizedResponse:
    return respond(request)


@app.get("/debug/retrieval")
def debug_retrieval(q: str = Query("")) -> dict:
    return {"query": q, "sources": retrieve(q), "warning": "synthetic local debug endpoint"}


@app.post("/internal/retrieve")
def internal_retrieve(payload: NormalizedRequest, request: Request) -> dict:
    _require_local(request)
    return {"sources": retrieve(payload.user_message), "integration": "synthetic-local-only"}


@app.post("/internal/generate", response_model=NormalizedResponse)
def internal_generate(payload: InternalGenerateRequest, request: Request) -> NormalizedResponse:
    _require_local(request)
    return generate(payload.request, payload.context, execute_tools=payload.execute_tools)
