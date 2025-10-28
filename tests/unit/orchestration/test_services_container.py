"""Tests for AppServiceContainer helpers."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from tripsage.app_state import AppServiceContainer
from tripsage_core.services.business.flight_service import FlightService


def test_get_required_service_returns_instance() -> None:
    """get_required_service should return stored service instances."""
    container = AppServiceContainer(
        flight_service=Mock(spec=FlightService),
    )

    service = container.get_required_service(
        "flight_service", expected_type=FlightService
    )

    assert isinstance(service, FlightService)


def test_get_required_service_missing_raises() -> None:
    """get_required_service should raise ValueError for absent services."""
    container = AppServiceContainer()

    with pytest.raises(ValueError, match="flight_service"):
        container.get_required_service("flight_service")


def test_get_required_service_type_mismatch_raises() -> None:
    """get_required_service should enforce expected types."""
    container = AppServiceContainer(flight_service=Mock())

    with pytest.raises(TypeError):
        container.get_required_service("flight_service", expected_type=FlightService)


def test_get_optional_service_returns_none() -> None:
    """get_optional_service should return None when unset."""
    container = AppServiceContainer()

    assert container.get_optional_service("memory_service") is None
