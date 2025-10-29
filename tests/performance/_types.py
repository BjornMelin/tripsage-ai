"""Typed helpers for performance tests to avoid ambiguous unions.

These dataclasses intentionally model the metrics shapes used in
`test_api_key_performance.py` to keep pyright strict mode happy.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class MemorySample:
    """Memory sample data."""

    timestamp: float
    memory_mb: float
    memory_percent: float


@dataclass
class CpuSample:
    """CPU sample data."""

    timestamp: float
    cpu_percent: float


@dataclass
class GcSample:
    """Garbage collection sample data."""

    timestamp: float
    collections: list[int]


@dataclass
class ResourceMetrics:
    """Resource metrics data."""

    memory_samples: list[MemorySample] = field(default_factory=list)
    cpu_samples: list[CpuSample] = field(default_factory=list)
    gc_collections: list[GcSample] = field(default_factory=list)
    peak_memory_mb: float = 0.0
    memory_leaks_detected: int = 0
    avg_memory_per_operation: float = 0.0
    resource_cleanup_time: float = 0.0


@dataclass
class CacheMetrics:
    """Cache metrics data."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    sets: int = 0
    deletes: int = 0
    memory_pressure_events: int = 0
    avg_hit_time: list[float] = field(default_factory=list)
    avg_miss_time: list[float] = field(default_factory=list)


@dataclass
class QueryMetrics:
    """Query metrics data."""

    response_times: list[float] = field(default_factory=list)


class BenchmarkFixture(Protocol):
    """Minimal protocol for pytest-benchmark's fixture.

    This avoids importing plugin-specific types while giving pyright
    enough structure for attribute and call typing.
    """

    stats: Mapping[str, float]

    def __call__(self, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
        """Run a benchmarked callable."""
        ...

    def pedantic(
        self, func: Callable[..., Any] | Any, /, *, rounds: int, warmup_rounds: int
    ) -> Any:
        """Run function repeatedly with warmup and return the function result."""
        ...
