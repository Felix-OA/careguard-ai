from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from careguard_guard import __version__
from careguard_guard.config import load_guard_config
from careguard_guard.integration import DemoDeepIntegration
from careguard_guard.models import GuardChatRequest, GuardChatResponse, SecurityEvent
from careguard_guard.pipeline import GuardPipeline

app = FastAPI(title="CareGuard Guard Gateway", version=__version__)


def data_root() -> Path:
    return Path(os.getenv("CAREGUARD_DATA_DIR", Path(__file__).resolve().parents[2] / ".careguard-data"))


@lru_cache
def service() -> GuardPipeline:
    return GuardPipeline(
        load_guard_config(),
        data_root() / "guard",
        DemoDeepIntegration(os.getenv("CAREGUARD_DEMO_URL")),
    )


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "guard_mode": service().config.guard_mode.value,
        "synthetic_data_only": True,
    }


@app.post("/v1/chat", response_model=GuardChatResponse)
async def chat(request: GuardChatRequest) -> GuardChatResponse:
    return await service().process(request)


@app.get("/v1/policies")
def policies() -> dict:
    return service().config.model_dump(mode="json")


@app.get("/v1/events", response_model=list[SecurityEvent])
def events(limit: int = Query(100, ge=1, le=1000)) -> list[SecurityEvent]:
    return service().events.list(limit)


@app.get("/v1/events/{event_id}", response_model=SecurityEvent)
def event(event_id: str) -> SecurityEvent:
    item = service().events.get(event_id)
    if not item:
        raise HTTPException(404, "event not found")
    return item


@app.get("/v1/metrics")
def metrics() -> dict:
    return service().events.metrics()


@app.post("/v1/config/reload")
def reload_config() -> dict:
    config = load_guard_config()
    service().reload(config)
    return {"status": "reloaded", "version": config.version, "guard_mode": config.guard_mode.value}

