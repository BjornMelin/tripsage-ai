"""Infrastructure services - migrated to tripsage_core.services.infrastructure."""

# Re-export from Core for compatibility
from tripsage_core.services.infrastructure import (
    CacheService,
    DatabaseService,
    WebSocketBroadcaster,
    WebSocketManager,
    get_cache_service,
    get_database_service,
)

# Legacy aliases
DragonflyService = CacheService
SupabaseService = DatabaseService

__all__ = [
    "DatabaseService",
    "CacheService",
    "DragonflyService",
    "SupabaseService",
    "WebSocketBroadcaster",
    "WebSocketManager",
    "get_database_service",
    "get_cache_service",
]
