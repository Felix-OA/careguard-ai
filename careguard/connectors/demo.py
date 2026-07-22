from __future__ import annotations

import os

from careguard.connectors.base import TargetConnector
from careguard.connectors.http_safety import bounded_json_post
from careguard.models.schemas import NormalizedRequest, NormalizedResponse
from careguard.security import ensure_authorized_endpoint


class DemoConnector(TargetConnector):
    def __init__(self, endpoint: str | None = None, timeout_seconds: int = 10) -> None:
        self.endpoint = endpoint or os.getenv("CAREGUARD_DEMO_URL")
        if self.endpoint:
            ensure_authorized_endpoint(self.endpoint)
        self._timeout_seconds = timeout_seconds

    async def send(self, request: NormalizedRequest) -> NormalizedResponse:
        if not self.endpoint:
            from demo_health_agent.engine import respond

            return respond(request)
        try:
            payload = await bounded_json_post(
                f"{self.endpoint.rstrip('/')}/chat",
                payload=request.model_dump(mode="json"),
                timeout_seconds=self._timeout_seconds,
            )
            return NormalizedResponse.model_validate(payload)
        except Exception as exc:  # normalized error, never headers or credentials
            return NormalizedResponse(
                target_id=request.target_id,
                conversation_id=request.conversation_id,
                error=f"demo connector error: {type(exc).__name__}",
            )
