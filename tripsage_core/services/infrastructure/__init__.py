"""
Infrastructure services for TripSage Core.

This module provides core infrastructure services across TripSage:
- Database operations (Supabase/PostgreSQL)
- pgvector HNSW optimization and performance tuning
- Caching (DragonflyDB)
- WebSocket management
- API key monitoring
"""

from .cache_service import CacheService, get_cache_service
from .database_service import DatabaseService, get_database_service
from .key_monitoring_service import (
    KeyMonitoringService,
    KeyOperation,
    KeyOperationRateLimitMiddleware,
    monitor_key_operation,
)
from .pgvector_optimizer import (
    DistanceFunction,
    HNSWParameters,
    IndexBuildProgress,
    IndexType,
    OptimizationProfile,
    ParallelIndexConfig,
    PGVectorOptimizer,
    QueryOptimizationStats,
    VectorCompressionConfig,
    quick_optimize_table,
)
from .websocket_broadcaster import WebSocketBroadcaster, websocket_broadcaster
from .websocket_manager import WebSocketManager, websocket_manager

__all__ = [
    # Database
    "DatabaseService",
    "get_database_service",
    # pgvector Optimization
    "PGVectorOptimizer",
    "HNSWParameters",
    "VectorCompressionConfig",
    "ParallelIndexConfig",
    "IndexBuildProgress",
    "QueryOptimizationStats",
    "DistanceFunction",
    "IndexType",
    "OptimizationProfile",
    "quick_optimize_table",
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
