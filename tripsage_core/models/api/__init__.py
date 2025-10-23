"""Aggregate exports for API-facing models with automatic module discovery."""

from collections.abc import Iterable
from importlib import import_module
from typing import Final


_MODULES = (
    "tripsage_core.models.api.accommodation_models",
    "tripsage_core.models.api.calendar_models",
    "tripsage_core.models.api.itinerary_models",
    "tripsage_core.models.api.maps_models",
    "tripsage_core.models.api.trip_models",
    "tripsage_core.models.api.weather_models",
)

__all__: list[str] = []

for module_path in _MODULES:
    module = import_module(module_path)
    exported_names: Iterable[str]
    if hasattr(module, "__all__"):
        exported_names = module.__all__
    else:
        exported_names = [
            name
            for name, value in module.__dict__.items()
            if not name.startswith("_")
            and getattr(value, "__module__", "").startswith(module.__name__)
        ]

    globals().update({name: getattr(module, name) for name in exported_names})
    __all__.extend(list(exported_names))

_unique_exports: Final[tuple[str, ...]] = tuple(sorted(dict.fromkeys(__all__)))
__all__ = list(_unique_exports)
