from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import Request

T = TypeVar("T", bound=Callable[..., Any])

class Limiter:
    """Typed surface of SlowAPI's Limiter for decorators.

    This stub intentionally models only the attributes and methods used by
    TripSage to keep maintenance minimal while satisfying Pyright.
    """

    key_func: Callable[[Request], str]
    headers_enabled: bool
    default_limits: list[str]
    storage_uri: str | None
    storage_options: dict[str, Any]
    enabled: bool

    def __init__(
        self,
        *,
        key_func: Callable[[Request], str],
        default_limits: list[str] | None = ...,
        storage_uri: str | None = ...,
        headers_enabled: bool = ...,
        enabled: bool = ...,
        **kwargs: Any,
    ) -> None: ...
    def limit(
        self, limit_value: str | Callable[[Request], str]
    ) -> Callable[[T], T]: ...
    def shared_limit(
        self,
        limit_value: str | Callable[[Request], str],
        scope: str | Callable[[Request], str],
    ) -> Callable[[T], T]: ...
    def exempt(self, func: T) -> T: ...

def _rate_limit_exceeded_handler(request: Request, exc: Exception) -> Any: ...
