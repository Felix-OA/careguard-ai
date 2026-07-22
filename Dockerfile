FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
COPY careguard ./careguard
COPY careguard_guard ./careguard_guard
COPY demo_health_agent ./demo_health_agent
COPY configs ./configs
COPY scenarios ./scenarios
COPY README.md SECURITY.md LICENSE ./
RUN adduser --disabled-password --gecos '' careguard && mkdir -p /data && chown -R careguard:careguard /app /data
USER careguard
