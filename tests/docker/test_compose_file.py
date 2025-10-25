"""Smoke tests for Docker configuration files."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


COMPOSE_PATH = Path(__file__).resolve().parents[2] / "docker-compose.yml"


@pytest.mark.docker
def test_docker_compose_exists() -> None:
    """Ensure the project Docker Compose manifest is present."""
    assert COMPOSE_PATH.exists(), "docker-compose.yml should exist"


@pytest.mark.docker
def test_core_services_present() -> None:
    """Validate that required infrastructure services are defined."""
    with COMPOSE_PATH.open(encoding="utf-8") as handle:
        compose = yaml.safe_load(handle)

    services = set(compose.get("services", {}))
    expected = {"otel-collector", "jaeger"}
    missing = expected.difference(services)
    assert not missing, f"Missing services in docker-compose.yml: {sorted(missing)}"
