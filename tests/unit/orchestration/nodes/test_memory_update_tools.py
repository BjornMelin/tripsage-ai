"""MemoryUpdateNode tools init selects memory tool by name."""

from __future__ import annotations

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.memory_update import MemoryUpdateNode


def test_initialize_tools_selects_memory_tool() -> None:
    """_initialize_tools should pick a tool whose name contains 'memory'."""
    node = MemoryUpdateNode(AppServiceContainer())
    node._initialize_tools()  # type: ignore[reportPrivateUsage]
    assert node.memory_tool is not None
