"""Outbound HTTP mocking helpers for tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast

import pytest
from pytest_httpx import HTTPXMock


class MockResponseAdder(Protocol):
    """Callable protocol for registering outbound HTTP responses."""

    def __call__(
        self,
        method: str,
        url: str,
        *,
        status_code: int = 200,
        json: Any | None = None,
        text: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPXMock:
        """Register a canned response for the provided request."""
        ...


class _AssertAllCalled(Protocol):
    """Protocol describing the assertion helper exposed by pytest-httpx."""

    def assert_all_called(self) -> None:
        """Assert that all registered outbound expectations were met."""
        ...


@pytest.fixture()
def mock_external_request(httpx_mock: HTTPXMock) -> MockResponseAdder:
    """Return a helper to stub outbound HTTP requests deterministically.

    Args:
        httpx_mock: Pytest-httpx fixture that intercepts HTTPX outbound calls.

    Returns:
        MockResponseAdder: Callable that registers a canned response for a request.
    """

    def _add_response(
        method: str,
        url: str,
        *,
        status_code: int = 200,
        json: Any | None = None,
        text: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPXMock:
        httpx_mock.add_response(
            method=method,
            url=url,
            status_code=status_code,
            json=json,
            text=text,
            headers=headers,
        )
        return httpx_mock

    return _add_response


@pytest.fixture()
def assert_external_calls(httpx_mock: HTTPXMock) -> Callable[[], None]:
    """Ensure all registered outbound HTTP expectations are satisfied.

    Args:
        httpx_mock: Pytest-httpx fixture with recorded outbound calls.

    Returns:
        Callable[[], None]: Assertion callable to validate expected call count.
    """

    def _assert() -> None:
        cast(_AssertAllCalled, httpx_mock).assert_all_called()

    return _assert
