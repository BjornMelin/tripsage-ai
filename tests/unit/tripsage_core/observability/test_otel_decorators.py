"""Tests for the otel decorators."""

import asyncio
from typing import Any

import pytest

from tripsage_core.observability.otel import record_histogram, trace_span


def test_trace_span_sync_executes_and_returns_value():
    """trace_span executes sync function and returns value."""
    call_attrs: dict[str, Any] = {}

    def attrs(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        call_attrs["args_len"] = len(args)
        call_attrs["kwargs_len"] = len(kwargs)
        return {"component": "test"}

    @trace_span(name="unit.sync", attrs=attrs)
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5
    assert call_attrs["args_len"] == 2
    assert call_attrs["kwargs_len"] == 0


@pytest.mark.asyncio
async def test_trace_span_async_executes_and_returns_value():
    """trace_span executes async function and returns value."""

    @trace_span(name="unit.async")
    async def mul(a: int, b: int) -> int:
        await asyncio.sleep(0)
        return a * b

    res = mul(2, 4)
    if asyncio.iscoroutine(res):
        res = await res
    assert res == 8


def test_record_histogram_sync_executes():
    """record_histogram executes sync function and records histogram."""

    @record_histogram("unit.duration", unit="s", description="test")
    def f(x: int) -> int:
        return x + 1

    assert f(1) == 2
