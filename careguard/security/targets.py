from urllib.parse import urlsplit


# Stage 3 deliberately allows only the two local synthetic service ports. This
# is an application allow-list, not a substitute for production egress policy.
AUTHORIZED_ORIGINS = {
    ("http", "localhost", 8001),
    ("http", "127.0.0.1", 8001),
    ("http", "localhost", 8002),
    ("http", "127.0.0.1", 8002),
    ("http", "demo-agent", 8001),
    ("http", "careguard-guard", 8002),
}


def ensure_authorized_endpoint(
    endpoint: str,
    allowed_origins: set[tuple[str, str, int]] | None = None,
) -> None:
    if endpoint != endpoint.strip() or any(ord(character) < 32 for character in endpoint):
        raise ValueError("Connector URLs must not contain whitespace or control characters")
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("CareGuard connectors require an HTTP(S) endpoint")
    if parsed.username or parsed.password:
        raise ValueError("Credentials must not be embedded in connector URLs")
    if parsed.query or parsed.fragment:
        raise ValueError("Connector URLs must not contain query strings or fragments")
    if not parsed.hostname:
        raise ValueError("Connector URL hostname is required")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise ValueError("Connector URL port is invalid") from exc
    origin = (parsed.scheme, parsed.hostname, port)
    if origin not in (allowed_origins or AUTHORIZED_ORIGINS):
        raise ValueError("CareGuard permits only explicitly authorized local synthetic service origins")
