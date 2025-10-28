"""Utilities for managing export surfaces in API model modules."""

from collections.abc import Iterable
from typing import Any


def auto_all(module_name: str, module_globals: dict[str, Any]) -> list[str]:
    """Return a list of public attributes defined in ``module_name``.

    Args:
        module_name: Name of the module performing the export.
        module_globals: Globals dictionary from that module.

    Returns:
        Sorted list of exported attribute names.
    """
    exported: Iterable[str]
    explicit = module_globals.get("__all__")
    if isinstance(explicit, (list, tuple, set)):
        exported = explicit
    else:
        exported = (
            name
            for name, value in module_globals.items()
            if not name.startswith("_")
            and getattr(value, "__module__", "").startswith(module_name)
        )

    return sorted(set(exported))
