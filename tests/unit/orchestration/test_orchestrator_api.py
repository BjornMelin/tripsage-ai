"""Tests for orchestration exports and singleton helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration import TripSageOrchestrator, get_orchestrator


def test_get_orchestrator_requires_registry():
    """get_orchestrator requires a configured registry when creating the singleton."""
    with (
        patch("tripsage.orchestration.graph._global_orchestrator", new=None),
        pytest.raises(ValueError),
    ):
        get_orchestrator()


def test_get_orchestrator_singleton():
    """get_orchestrator should instantiate the graph orchestrator only once."""
    fake_orchestrator = MagicMock(spec=TripSageOrchestrator)
    registry = MagicMock(spec=ServiceRegistry)

    with (
        patch("tripsage.orchestration.graph._global_orchestrator", new=None),
        patch(
            "tripsage.orchestration.graph.TripSageOrchestrator",
            return_value=fake_orchestrator,
        ) as mock_cls,
    ):
        first = get_orchestrator(service_registry=registry)
        second = get_orchestrator()

    assert first is fake_orchestrator
    assert second is fake_orchestrator
    mock_cls.assert_called_once_with(service_registry=registry)


def test_get_orchestrator_ignores_subsequent_registry_overrides(caplog):
    """Once created, registry overrides are ignored with a warning."""
    fake_orchestrator = MagicMock(spec=TripSageOrchestrator)
    sentinel_registry = MagicMock()

    with (
        patch("tripsage.orchestration.graph._global_orchestrator", new=None),
        patch(
            "tripsage.orchestration.graph.TripSageOrchestrator",
            return_value=fake_orchestrator,
        ),
    ):
        first = get_orchestrator(service_registry=sentinel_registry)
        fake_orchestrator.service_registry = sentinel_registry
        different_registry = MagicMock(spec=ServiceRegistry)
        second = get_orchestrator(service_registry=different_registry)

    assert first is fake_orchestrator
    assert second is fake_orchestrator
    assert "Ignoring service_registry override" in caplog.text
