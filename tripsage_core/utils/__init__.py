"""
TripSage Core utilities module.

This module provides common utility functions used across the TripSage Core library.
"""

# Cache utilities
from .cache_utils import (
    CacheStats,
    batch_cache_get,
    batch_cache_set,
    cache_lock,
    cached,
    cached_daily,
    cached_realtime,
    cached_semi_static,
    cached_static,
    cached_time_sensitive,
    delete_cache,
    generate_cache_key,
    get_cache,
    get_cache_stats,
    memory_cache,
    redis_cache,
    set_cache,
)

# Content utilities
from .content_utils import ContentType, get_ttl_for_content_type

# Database utilities
from .database_utils import DatabaseConnectionFactory, get_supabase_settings

# Decorator utilities
from .decorator_utils import (
    ensure_memory_client_initialized,
    retry_on_failure,
    with_error_handling,
)

# Error handling utilities
from .error_handling_utils import (
    TripSageError,
    TripSageErrorContext,
    create_api_error,
    create_database_error,
    create_mcp_error,
    create_validation_error,
    log_exception,
    safe_execute_with_logging,
    with_error_handling_and_logging,
)

# File utilities
from .file_utils import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    DEFAULT_STORAGE_ROOT,
    FILE_TYPE_MAPPING,
    MAX_FILE_SIZE,
    MAX_FILES_PER_REQUEST,
    MAX_SESSION_SIZE,
    PROCESSED_DIR,
    TEMP_UPLOAD_DIR,
    ValidationResult,
    generate_safe_filename,
    validate_batch_upload,
    validate_file,
)

# Logging utilities
from .logging_utils import (
    ContextAdapter,
    configure_logging,
    configure_root_logger,
    get_logger,
)
from .logging_utils import (
    log_exception as log_exception_util,
)

# Session utilities
from .session_utils import (
    ConversationMessage,
    SessionSummary,
    UserPreferences,
    get_session_memory_legacy,
    initialize_session_memory,
    store_session_summary,
    update_memory_legacy,
    update_session_memory,
)

__all__ = [
    # Cache utilities
    "CacheStats",
    "ContentType",
    "get_ttl_for_content_type",
    "memory_cache",
    "redis_cache",
    "get_cache",
    "set_cache",
    "delete_cache",
    "get_cache_stats",
    "generate_cache_key",
    "cached",
    "cached_realtime",
    "cached_time_sensitive",
    "cached_daily",
    "cached_semi_static",
    "cached_static",
    "batch_cache_set",
    "batch_cache_get",
    "cache_lock",
    # Database utilities
    "get_supabase_settings",
    "DatabaseConnectionFactory",
    # Decorator utilities
    "with_error_handling",
    "ensure_memory_client_initialized",
    "retry_on_failure",
    # Error handling utilities
    "TripSageError",
    "log_exception",
    "safe_execute_with_logging",
    "with_error_handling_and_logging",
    "create_mcp_error",
    "create_api_error",
    "create_validation_error",
    "create_database_error",
    "TripSageErrorContext",
    # File utilities
    "MAX_FILE_SIZE",
    "MAX_FILES_PER_REQUEST",
    "MAX_SESSION_SIZE",
    "ALLOWED_EXTENSIONS",
    "ALLOWED_MIME_TYPES",
    "FILE_TYPE_MAPPING",
    "DEFAULT_STORAGE_ROOT",
    "TEMP_UPLOAD_DIR",
    "PROCESSED_DIR",
    "ValidationResult",
    "validate_file",
    "validate_batch_upload",
    "generate_safe_filename",
    # Logging utilities
    "get_logger",
    "configure_logging",
    "configure_root_logger",
    "ContextAdapter",
    "log_exception_util",
    # Session utilities
    "ConversationMessage",
    "SessionSummary",
    "UserPreferences",
    "initialize_session_memory",
    "update_session_memory",
    "store_session_summary",
    "get_session_memory_legacy",
    "update_memory_legacy",
]
