"""Global pytest fixtures for tests.

Provides shared helpers for building synthetic FastAPI Request objects, useful
for unit-testing endpoints decorated with SlowAPI limiters without going
through an HTTP client.
"""

from collections.abc import Callable

import pytest
from fastapi import Request


@pytest.fixture
def request_builder() -> Callable[[str, str], Request]:
    """Build a synthetic FastAPI ``Request`` for unit tests.

    Args:
        method: HTTP method (e.g., "GET", "POST")
        path: URL path (e.g., "/api/memory/search")

    Returns:
        A minimally viable FastAPI ``Request`` instance suitable for SlowAPI.
    """

    def _build(method: str, path: str) -> Request:
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "scheme": "http",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "query_string": b"",
        }

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        return Request(scope, receive)

    return _build
