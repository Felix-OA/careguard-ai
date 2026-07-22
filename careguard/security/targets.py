from urllib.parse import urlparse

AUTHORIZED_HOSTS = {"localhost", "127.0.0.1", "demo-agent", "careguard-api", "careguard-guard"}


def ensure_authorized_endpoint(endpoint: str, allowed_hosts: set[str] | None = None) -> None:
    host = urlparse(endpoint).hostname
    if host not in (allowed_hosts or AUTHORIZED_HOSTS):
        raise ValueError(f"Stage 1 only permits explicitly authorized local targets; rejected host: {host}")
