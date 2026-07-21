from __future__ import annotations

import os

import httpx

from careguard.connectors.base import TargetConnector
from careguard.models.schemas import NormalizedRequest, NormalizedResponse
from careguard.security import ensure_authorized_endpoint


class DemoConnector(TargetConnector):
    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = endpoint or os.getenv("CAREGUARD_DEMO_URL")
        if self.endpoint:
            ensure_authorized_endpoint(self.endpoint)

    async def send(self, request: NormalizedRequest) -> NormalizedResponse:
        if not self.endpoint:
            from demo_health_agent.engine import respond

            return respond(request)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{self.endpoint.rstrip('/')}/chat", json=request.model_dump(mode="json"))
                response.raise_for_status()
                return NormalizedResponse.model_validate(response.json())
        except Exception as exc:  # normalized error, never headers or credentials
            return NormalizedResponse(
                target_id=request.target_id,
                conversation_id=request.conversation_id,
                error=f"demo connector error: {type(exc).__name__}",
            )

