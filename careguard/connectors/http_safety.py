from __future__ import annotations

import json
from typing import Any

import httpx


MAX_CONNECTOR_RESPONSE_BYTES = 1_000_000


async def bounded_json_post(
    endpoint: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 15,
) -> Any:
    """POST without redirects and parse at most one megabyte of JSON."""
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
        async with client.stream("POST", endpoint, json=payload, headers=headers or {}) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > MAX_CONNECTOR_RESPONSE_BYTES:
                        raise ValueError("connector response exceeds the local safety limit")
                except ValueError as exc:
                    raise ValueError("connector response size is invalid or exceeds the local safety limit") from exc
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > MAX_CONNECTOR_RESPONSE_BYTES:
                    raise ValueError("connector response exceeds the local safety limit")
    return json.loads(body)
