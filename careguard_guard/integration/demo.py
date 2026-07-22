from __future__ import annotations

import os

import httpx

from careguard.models.schemas import NormalizedRequest, NormalizedResponse
from careguard.security import ensure_authorized_endpoint


class DemoDeepIntegration:
    """Deep synthetic integration exposing retrieval before deterministic generation."""

    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = endpoint or os.getenv("CAREGUARD_DEMO_URL")
        if self.endpoint:
            ensure_authorized_endpoint(self.endpoint)

    async def retrieve(self, request: NormalizedRequest) -> list[dict]:
        if not self.endpoint:
            from demo_health_agent.retrieval import retrieve

            return retrieve(request.user_message)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.endpoint.rstrip('/')}/internal/retrieve", json=request.model_dump(mode="json")
            )
            response.raise_for_status()
            return response.json()["sources"]

    async def refill(self, request: NormalizedRequest) -> list[dict]:
        refill_request = request.model_copy(
            update={"user_message": "approved clinic policy hours and approved hydration health information"}
        )
        return await self.retrieve(refill_request)

    async def generate(
        self, request: NormalizedRequest, context: list[dict], execute_tools: bool = False
    ) -> NormalizedResponse:
        if not self.endpoint:
            from demo_health_agent.engine import generate

            return generate(request, context, execute_tools=execute_tools)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.endpoint.rstrip('/')}/internal/generate",
                json={
                    "request": request.model_dump(mode="json"),
                    "context": context,
                    "execute_tools": execute_tools,
                },
            )
            response.raise_for_status()
            return NormalizedResponse.model_validate(response.json())

