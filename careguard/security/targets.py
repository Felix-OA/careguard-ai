from urllib.parse import urlparse

AUTHORIZED_HOSTS = {"localhost", "127.0.0.1", "demo-agent", "careguard-api", "careguard-guard"}


def ensure_authorized_endpoint(endpoint: str, allowed_hosts: set[str] | None = None) -> None:
    parsed = urlparse(endpoint)
    host = parsed.hostname
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("CareGuard connectors require an HTTP(S) endpoint")
    if parsed.username or parsed.password:
        raise ValueError("Credentials must not be embedded in connector URLs")
    if host not in (allowed_hosts or AUTHORIZED_HOSTS):
        raise ValueError(f"CareGuard permits only explicitly authorized local targets; rejected host: {host}")
