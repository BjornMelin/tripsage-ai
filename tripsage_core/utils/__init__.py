"""TripSage Core utilities package.

This package intentionally avoids eager re-exports to keep import side-effects
and coupling low. Import needed modules directly, for example:

    from tripsage_core.utils.decorator_utils import with_error_handling
    from tripsage_core.utils.cache_utils import get_cache
"""

__all__: list[str] = []
