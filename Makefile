.PHONY: install test check demo-api careguard-api audit report

install:
	python -m pip install -e '.[dev]'

test:
	pytest

check:
	python -m compileall careguard demo_health_agent careguard_guard
	python -m careguard.cli check-config
	docker compose config

demo-api:
	uvicorn demo_health_agent.api.app:app --reload --port 8001

careguard-api:
	uvicorn careguard.api.app:app --reload --port 8000

guard-api:
	uvicorn careguard_guard.api.app:app --reload --port 8002

audit:
	python -m careguard.cli run-audit --target demo

report:
	python -m careguard.cli generate-report --latest
