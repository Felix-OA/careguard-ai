from __future__ import annotations

from time import perf_counter

from careguard.connectors.base import TargetConnector
from careguard.connectors.http_safety import bounded_json_post
from careguard.models.schemas import NormalizedRequest, NormalizedResponse, SourceMetadata, ToolCall
from careguard.security import ensure_authorized_endpoint


class RestChatConnector(TargetConnector):
    def __init__(
        self, endpoint: str, headers: dict[str, str] | None = None, timeout_seconds: int = 15,
    ) -> None:
        ensure_authorized_endpoint(endpoint)
        self.endpoint = endpoint
        self._headers = headers or {}
        self._timeout_seconds = timeout_seconds

    async def send(self, request: NormalizedRequest) -> NormalizedResponse:
        started = perf_counter()
        try:
            data = await bounded_json_post(
                self.endpoint,
                payload=request.model_dump(mode="json"),
                headers=self._headers,
                timeout_seconds=self._timeout_seconds,
            )
            return NormalizedResponse(
                target_id=request.target_id,
                conversation_id=request.conversation_id,
                answer=data.get("answer", data.get("message", "")),
                retrieved_sources=[SourceMetadata.model_validate(item) for item in data.get("retrieved_sources", [])],
                proposed_tool_calls=[ToolCall.model_validate(item) for item in data.get("proposed_tool_calls", [])],
                executed_tool_calls=[ToolCall.model_validate(item) for item in data.get("executed_tool_calls", [])],
                latency_ms=(perf_counter() - started) * 1000,
                provider=data.get("provider", "generic-rest"),
                model=data.get("model", "unknown"),
            )
        except Exception as exc:
            return NormalizedResponse(
                target_id=request.target_id, conversation_id=request.conversation_id,
                latency_ms=(perf_counter() - started) * 1000,
                provider="generic-rest", model="unknown", error=f"REST connector error: {type(exc).__name__}",
            )


class OpenAICompatibleConnector(TargetConnector):
    """Optional local/authorized OpenAI-compatible adapter; API key stays in this object."""

    def __init__(
        self, endpoint: str, model: str, api_key: str | None = None, timeout_seconds: int = 20,
    ) -> None:
        ensure_authorized_endpoint(endpoint)
        self.endpoint, self.model, self._api_key = endpoint, model, api_key
        self._timeout_seconds = timeout_seconds

    async def send(self, request: NormalizedRequest) -> NormalizedResponse:
        started = perf_counter()
        messages = [turn.model_dump() for turn in request.conversation_history]
        messages.append({"role": "user", "content": request.user_message})
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            data = await bounded_json_post(
                self.endpoint,
                headers=headers,
                payload={"model": self.model, "messages": messages},
                timeout_seconds=self._timeout_seconds,
            )
            return NormalizedResponse(
                target_id=request.target_id, conversation_id=request.conversation_id,
                answer=data["choices"][0]["message"].get("content", ""),
                latency_ms=(perf_counter() - started) * 1000,
                provider="openai-compatible", model=data.get("model", self.model),
            )
        except Exception as exc:
            return NormalizedResponse(
                target_id=request.target_id, conversation_id=request.conversation_id,
                latency_ms=(perf_counter() - started) * 1000,
                provider="openai-compatible", model=self.model,
                error=f"OpenAI-compatible connector error: {type(exc).__name__}",
            )
