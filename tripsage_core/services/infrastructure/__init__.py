"""
Infrastructure services for TripSage Core.

This module provides core infrastructure services across TripSage:
- Database operations (Supabase/PostgreSQL)
- Database monitoring (health, performance, security)
- pgvector optimization and performance tuning
- Caching (DragonflyDB)
- WebSocket management
- API key monitoring
"""

from .cache_service import CacheService, get_cache_service
from .database_monitor import (
    ConsolidatedDatabaseMonitor,
    HealthStatus,
    MonitoringConfig,
    QueryStatus,
    QueryType,
    SecurityEvent,
    get_database_monitor,
)
from .database_service import DatabaseService, get_database_service
from .key_monitoring_service import (
    KeyMonitoringService,
    KeyOperation,
    KeyOperationRateLimitMiddleware,
    monitor_key_operation,
)
from .pgvector_service import (
    DistanceFunction,
    IndexConfig,
    IndexStats,
    OptimizationProfile,
    PGVectorService,
    optimize_vector_table,
)
from .websocket_broadcaster import WebSocketBroadcaster, websocket_broadcaster
from .websocket_manager import WebSocketManager, websocket_manager

__all__ = [
    # Database
    "DatabaseService",
    "get_database_service",
    # Database Monitor
    "ConsolidatedDatabaseMonitor",
    "get_database_monitor",
    "MonitoringConfig",
    "HealthStatus",
    "QueryType",
    "QueryStatus",
    "SecurityEvent",
    # pgvector Service (Modern, simplified approach)
    "PGVectorService",
    "DistanceFunction",
    "OptimizationProfile",
    "IndexConfig",
    "IndexStats",
    "optimize_vector_table",
    # Cache
    "CacheService",
    "get_cache_service",
    # WebSocket
    "WebSocketManager",
    "websocket_manager",
    "WebSocketBroadcaster",
    "websocket_broadcaster",
    # Key Monitoring
    "KeyMonitoringService",
    "KeyOperation",
    "KeyOperationRateLimitMiddleware",
    "monitor_key_operation",
]
