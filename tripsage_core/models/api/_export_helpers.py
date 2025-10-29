"""Utilities for managing export surfaces in API model modules."""

from collections.abc import Iterable
from typing import Any, cast


def auto_all(module_name: str, module_globals: dict[str, Any]) -> list[str]:
    """Return a list of public attributes defined in ``module_name``.

    Args:
        module_name: Name of the module performing the export.
        module_globals: Globals dictionary from that module.

    Returns:
        Sorted list of exported attribute names.
    """
    explicit = module_globals.get("__all__")
    if isinstance(explicit, (list, tuple, set)):
        seq: Iterable[object] = cast(Iterable[object], explicit)
        exported_list: list[str] = [str(x) for x in seq]
    else:
        exported_list = [
            str(name)
            for name, value in module_globals.items()
            if not name.startswith("_")
            and getattr(value, "__module__", "").startswith(module_name)
        ]

    return sorted(set(exported_list))
