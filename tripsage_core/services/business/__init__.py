"""Business services for TripSage core functionality."""

# Use async memory service as the default implementation
# (50-70% performance improvement)
from tripsage_core.services.business.memory_service_async import (
    AsyncMemoryService as MemoryService,
)
from tripsage_core.services.business.memory_service_async import (
    ConversationMemoryRequest,
    MemorySearchRequest,
    MemorySearchResult,
    PreferencesUpdateRequest,
    UserContextResponse,
)
from tripsage_core.services.business.memory_service_async import (
    get_async_memory_service as get_memory_service,
)

__all__ = [
    # Memory Service (Unified Async Implementation)
    "MemoryService",
    "get_memory_service",
    # Shared Models
    "ConversationMemoryRequest",
    "MemorySearchRequest",
    "MemorySearchResult",
    "UserContextResponse",
    "PreferencesUpdateRequest",
]
