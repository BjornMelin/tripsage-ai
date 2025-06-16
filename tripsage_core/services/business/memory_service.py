"""
Memory service for AI conversation memory and user context management.

This service consolidates memory-related operations using Mem0 with pgvector backend,
providing efficient storage and retrieval of conversation context, user preferences,
and travel-specific insights.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field, field_validator

from tripsage_core.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.models.base_core_model import TripSageModel

logger = logging.getLogger(__name__)


class MemorySearchResult(TripSageModel):
    """Memory search result with metadata."""

    id: str = Field(..., description="Memory ID")
    memory: str = Field(..., description="Memory content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Memory metadata"
    )
    categories: List[str] = Field(default_factory=list, description="Memory categories")
    similarity: float = Field(default=0.0, description="Similarity score")
    created_at: datetime = Field(..., description="Creation timestamp")
    user_id: str = Field(..., description="User ID")


class ConversationMemoryRequest(TripSageModel):
    """Request model for conversation memory extraction."""

    messages: List[Dict[str, str]] = Field(..., description="Conversation messages")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MemorySearchRequest(TripSageModel):
    """Request model for memory search."""

    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    similarity_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum similarity"
    )


class UserContextResponse(TripSageModel):
    """Response model for user context."""

    preferences: List[Dict[str, Any]] = Field(
        default_factory=list, description="User preferences"
    )
    past_trips: List[Dict[str, Any]] = Field(
        default_factory=list, description="Past trip memories"
    )
    saved_destinations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Saved destinations"
    )
    budget_patterns: List[Dict[str, Any]] = Field(
        default_factory=list, description="Budget patterns"
    )
    travel_style: List[Dict[str, Any]] = Field(
        default_factory=list, description="Travel style memories"
    )
    dietary_restrictions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Dietary restrictions"
    )
    accommodation_preferences: List[Dict[str, Any]] = Field(
        default_factory=list, description="Accommodation preferences"
    )
    activity_preferences: List[Dict[str, Any]] = Field(
        default_factory=list, description="Activity preferences"
    )
    insights: Dict[str, Any] = Field(
        default_factory=dict, description="Derived insights"
    )
    summary: str = Field(default="", description="Context summary")


class PreferencesUpdateRequest(TripSageModel):
    """Request model for preferences update."""

    preferences: Dict[str, Any] = Field(..., description="Preferences to update")
    category: Optional[str] = Field(None, description="Preference category")

    @field_validator("preferences")
    @classmethod
    def validate_preferences(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate preferences data."""
        if not v:
            raise ValueError("Preferences cannot be empty")
        return v


class MemoryService:
    """
    Comprehensive memory service using Mem0 with travel-specific optimizations.

    This service handles:
    - Conversation memory extraction and storage
    - User context and preference management
    - Travel-specific memory categorization
    - Efficient search and retrieval
    - Memory cleanup and GDPR compliance

    Features:
    - Optimized for travel planning use cases
    - Intelligent categorization of memories
    - Caching for performance
    - Rate limiting for external API calls
    """

    def __init__(
        self,
        database_service=None,
        memory_backend_config: Optional[Dict[str, Any]] = None,
        cache_ttl: int = 300,
    ):
        """
        Initialize the memory service.

        Args:
            database_service: Database service for persistence
            memory_backend_config: Mem0 configuration
            cache_ttl: Cache TTL in seconds
        """
        # Import here to avoid circular imports
        if database_service is None:
            from tripsage_core.services.infrastructure import get_database_service

            database_service = get_database_service()

        self.db = database_service
        self.cache_ttl = cache_ttl

        # Initialize memory backend
        self._initialize_memory_backend(memory_backend_config)

        # In-memory cache for search results
        self._cache: Dict[str, Tuple[List[MemorySearchResult], float]] = {}
        self._connected = False

    def _initialize_memory_backend(self, config: Optional[Dict[str, Any]]) -> None:
        """
        Initialize Mem0 memory backend.

        Args:
            config: Mem0 configuration
        """
        try:
            # Use default config if none provided
            if config is None:
                config = self._get_default_config()

            # Import Mem0 here to avoid startup dependency
            from mem0 import Memory

            self.memory = Memory.from_config(config)
            self._memory_config = config

            logger.info("Memory backend initialized successfully")

        except ImportError:
            logger.warning("Mem0 not available, using fallback memory implementation")
            self.memory = None
        except Exception as e:
            logger.error(f"Failed to initialize memory backend: {str(e)}")
            self.memory = None

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default Mem0 configuration optimized for TripSage.

        Returns:
            Mem0 configuration dictionary
        """
        # Get settings for API keys
        from tripsage_core.config import get_settings

        settings = get_settings()

        return {
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": settings.database_url.split("@")[1]
                    .split("/")[0]
                    .split(":")[0],
                    "port": 5432,
                    "dbname": "postgres",
                    "user": "postgres",
                    "password": settings.database_password,
                    "collection_name": "memories",
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                    "max_tokens": 500,
                    "api_key": settings.openai_api_key,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small",
                    "api_key": settings.openai_api_key,
                },
            },
            "version": "v1.1",
        }

    async def connect(self) -> None:
        """Initialize service connection."""
        if self._connected or not self.memory:
            return

        try:
            # Test connection with a simple operation
            await asyncio.to_thread(
                self.memory.search,
                query="health_check_test",
                user_id="health_check_user",
                limit=1,
            )
            self._connected = True
            logger.info("Memory service connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect memory service: {str(e)}")
            raise ServiceError("Memory service connection failed") from e

    async def close(self) -> None:
        """Close service connection."""
        if not self._connected:
            return

        try:
            self._connected = False
            self._cache.clear()
            logger.info("Memory service closed successfully")

        except Exception as e:
            logger.error(f"Error closing memory service: {str(e)}")

    async def add_conversation_memory(
        self, user_id: str, memory_request: ConversationMemoryRequest
    ) -> Dict[str, Any]:
        """
        Extract and store memories from conversation.

        Args:
            user_id: User identifier
            memory_request: Conversation memory request

        Returns:
            Memory extraction result with usage statistics
        """
        if not await self._ensure_connected():
            return {"results": [], "error": "Memory service not available"}

        try:
            # Add travel-specific metadata
            enhanced_metadata = {
                "domain": "travel_planning",
                "session_id": memory_request.session_id,
                "trip_id": memory_request.trip_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "conversation",
            }

            if memory_request.metadata:
                enhanced_metadata.update(memory_request.metadata)

            # Use Mem0's automatic extraction
            result = await asyncio.to_thread(
                self.memory.add,
                messages=memory_request.messages,
                user_id=user_id,
                metadata=enhanced_metadata,
            )

            # Clear user's cache after adding new memories
            self._invalidate_user_cache(user_id)

            # Log memory extraction metrics
            memory_count = len(result.get("results", []))
            tokens_used = result.get("usage", {}).get("total_tokens", 0)

            logger.info(
                "Memory extracted successfully",
                extra={
                    "user_id": user_id,
                    "session_id": memory_request.session_id,
                    "memory_count": memory_count,
                    "tokens_used": tokens_used,
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Memory extraction failed", extra={"user_id": user_id, "error": str(e)}
            )
            return {"results": [], "error": str(e)}

    async def search_memories(
        self, user_id: str, search_request: MemorySearchRequest
    ) -> List[MemorySearchResult]:
        """
        Search user memories with caching and optimization.

        Args:
            user_id: User identifier
            search_request: Memory search request

        Returns:
            List of memory search results
        """
        if not await self._ensure_connected():
            return []

        # Check cache first
        cache_key = self._generate_cache_key(user_id, search_request)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result

        try:
            # Direct Mem0 search
            results = await asyncio.to_thread(
                self.memory.search,
                query=search_request.query,
                user_id=user_id,
                limit=search_request.limit,
                filters=search_request.filters or {},
            )

            # Convert to our result model
            memory_results = []
            for result in results.get("results", []):
                memory_result = MemorySearchResult(
                    id=result.get("id", ""),
                    memory=result.get("memory", ""),
                    metadata=result.get("metadata", {}),
                    categories=result.get("categories", []),
                    similarity=result.get("score", 0.0),
                    created_at=self._parse_datetime(
                        result.get("created_at", datetime.now(timezone.utc).isoformat())
                    ),
                    user_id=user_id,
                )

                # Filter by similarity threshold
                if memory_result.similarity >= search_request.similarity_threshold:
                    memory_results.append(memory_result)

            # Cache the results
            self._cache_result(cache_key, memory_results)

            # Enrich with travel context
            enriched_results = await self._enrich_travel_memories(memory_results)

            logger.debug(
                "Memory search completed",
                extra={
                    "user_id": user_id,
                    "query": search_request.query,
                    "results_count": len(enriched_results),
                },
            )

            return enriched_results

        except Exception as e:
            logger.error(
                "Memory search failed",
                extra={
                    "user_id": user_id,
                    "query": search_request.query,
                    "error": str(e),
                },
            )
            return []

    async def get_user_context(
        self, user_id: str, context_type: Optional[str] = None
    ) -> UserContextResponse:
        """
        Get comprehensive user context for personalization.

        Args:
            user_id: User identifier
            context_type: Optional context type filter

        Returns:
            Organized user context with categories and insights
        """
        if not await self._ensure_connected():
            return UserContextResponse()

        try:
            # Retrieve all user memories
            all_memories = await asyncio.to_thread(
                self.memory.get_all, user_id=user_id, limit=100
            )

            # Organize by category
            context = {
                "preferences": [],
                "past_trips": [],
                "saved_destinations": [],
                "budget_patterns": [],
                "travel_style": [],
                "dietary_restrictions": [],
                "accommodation_preferences": [],
                "activity_preferences": [],
            }

            for memory in all_memories.get("results", []):
                categories = memory.get("categories", [])
                memory_content = memory.get("memory", "").lower()

                # Categorize memories based on categories and content analysis
                for category in categories:
                    if category in context:
                        context[category].append(memory)

                # Additional categorization based on content
                if any(
                    word in memory_content
                    for word in ["prefer", "like", "dislike", "favorite"]
                ):
                    if "preferences" not in [cat for cat in categories]:
                        context["preferences"].append(memory)

                if any(
                    word in memory_content
                    for word in ["budget", "cost", "price", "expensive", "cheap"]
                ):
                    if "budget_patterns" not in [cat for cat in categories]:
                        context["budget_patterns"].append(memory)

            # Add derived insights
            insights = await self._derive_travel_insights(context)
            summary = self._generate_context_summary(context, insights)

            return UserContextResponse(
                preferences=context["preferences"],
                past_trips=context["past_trips"],
                saved_destinations=context["saved_destinations"],
                budget_patterns=context["budget_patterns"],
                travel_style=context["travel_style"],
                dietary_restrictions=context["dietary_restrictions"],
                accommodation_preferences=context["accommodation_preferences"],
                activity_preferences=context["activity_preferences"],
                insights=insights,
                summary=summary,
            )

        except Exception as e:
            logger.error(
                "Failed to get user context",
                extra={"user_id": user_id, "error": str(e)},
            )
            return UserContextResponse(summary="Error retrieving user context")

    async def update_user_preferences(
        self, user_id: str, preferences_request: PreferencesUpdateRequest
    ) -> Dict[str, Any]:
        """
        Update user travel preferences in memory.

        Args:
            user_id: User identifier
            preferences_request: Preferences update request

        Returns:
            Update result
        """
        if not await self._ensure_connected():
            return {"error": "Memory service not available"}

        try:
            # Create conversation messages for preference update
            preference_messages = [
                {
                    "role": "system",
                    "content": (
                        "Extract and update user travel preferences from "
                        "the following information."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"My travel preferences: "
                        f"{json.dumps(preferences_request.preferences, indent=2)}"
                    ),
                },
            ]

            memory_request = ConversationMemoryRequest(
                messages=preference_messages,
                metadata={
                    "type": "preferences_update",
                    "category": preferences_request.category or "travel_preferences",
                    "source": "preference_api",
                },
            )

            result = await self.add_conversation_memory(user_id, memory_request)

            logger.info(
                "User preferences updated",
                extra={
                    "user_id": user_id,
                    "preferences_count": len(preferences_request.preferences),
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to update user preferences",
                extra={"user_id": user_id, "error": str(e)},
            )
            return {"error": str(e)}

    async def delete_user_memories(
        self, user_id: str, memory_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Delete user memories (GDPR compliance).

        Args:
            user_id: User identifier
            memory_ids: Optional list of specific memory IDs to delete

        Returns:
            Deletion result
        """
        if not await self._ensure_connected():
            return {"error": "Memory service not available"}

        try:
            deleted_count = 0

            if memory_ids:
                # Delete specific memories
                for memory_id in memory_ids:
                    try:
                        await asyncio.to_thread(self.memory.delete, memory_id=memory_id)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete memory {memory_id}: {str(e)}")
            else:
                # Delete all user memories
                all_memories = await asyncio.to_thread(
                    self.memory.get_all,
                    user_id=user_id,
                    limit=1000,
                )

                for memory in all_memories.get("results", []):
                    try:
                        await asyncio.to_thread(
                            self.memory.delete, memory_id=memory.get("id")
                        )
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to delete memory {memory.get('id')}: {str(e)}"
                        )

            # Clear user's cache
            self._invalidate_user_cache(user_id)

            logger.info(
                "User memories deleted",
                extra={"user_id": user_id, "deleted_count": deleted_count},
            )

            return {"deleted_count": deleted_count, "success": True}

        except Exception as e:
            logger.error(
                "Failed to delete user memories",
                extra={"user_id": user_id, "error": str(e)},
            )
            return {"error": str(e), "success": False}

    async def _ensure_connected(self) -> bool:
        """Ensure memory service is connected."""
        if not self.memory:
            return False

        if not self._connected:
            try:
                await self.connect()
            except Exception:
                return False

        return self._connected

    def _generate_cache_key(
        self, user_id: str, search_request: MemorySearchRequest
    ) -> str:
        """Generate cache key for search request."""
        key_data = (
            f"{user_id}:{search_request.query}:{search_request.limit}:"
            f"{hash(str(search_request.filters))}"
        )
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _get_cached_result(self, cache_key: str) -> Optional[List[MemorySearchResult]]:
        """Get cached search result if still valid."""
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                del self._cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: List[MemorySearchResult]) -> None:
        """Cache search result."""
        self._cache[cache_key] = (result, time.time())

        # Simple cache size management
        if len(self._cache) > 1000:
            # Remove oldest 200 entries
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:200]:
                del self._cache[key]

    def _invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate cache entries for a specific user."""
        keys_to_remove = [
            key
            for key in self._cache.keys()
            if any(cached_user_id == user_id for cached_user_id, *_ in [key.split(":")])
        ]
        for key in keys_to_remove:
            del self._cache[key]

    def _parse_datetime(self, dt_string: str) -> datetime:
        """Parse datetime string safely."""
        try:
            return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)

    async def _enrich_travel_memories(
        self, memories: List[MemorySearchResult]
    ) -> List[MemorySearchResult]:
        """Enrich memories with travel-specific context."""
        for memory in memories:
            memory_content = memory.memory.lower()

            # Add travel context flags
            if any(
                word in memory_content
                for word in ["destination", "city", "country", "place"]
            ):
                memory.metadata["has_location"] = True

            if any(
                word in memory_content for word in ["budget", "cost", "price", "money"]
            ):
                memory.metadata["has_budget"] = True

            if any(
                word in memory_content
                for word in ["hotel", "accommodation", "stay", "room"]
            ):
                memory.metadata["has_accommodation"] = True

        return memories

    async def _derive_travel_insights(self, context: Dict[str, List]) -> Dict[str, Any]:
        """Derive insights from user's travel history and preferences."""
        insights = {
            "preferred_destinations": self._analyze_destinations(context),
            "budget_range": self._analyze_budgets(context),
            "travel_frequency": self._analyze_frequency(context),
            "preferred_activities": self._analyze_activities(context),
            "travel_style": self._analyze_travel_style(context),
        }

        return insights

    def _analyze_destinations(self, context: Dict[str, List]) -> Dict[str, Any]:
        """Analyze destination preferences from context."""
        destinations = []
        for memory in context.get("past_trips", []) + context.get(
            "saved_destinations", []
        ):
            content = memory.get("memory", "").lower()
            # Simple destination extraction (could be enhanced with NER)
            for word in content.split():
                if word.capitalize() in [
                    "Japan",
                    "France",
                    "Italy",
                    "Spain",
                    "Thailand",
                    "USA",
                    "UK",
                ]:
                    destinations.append(word.capitalize())

        return {
            "most_visited": list(set(destinations)),
            "destination_count": len(set(destinations)),
        }

    def _analyze_budgets(self, context: Dict[str, List]) -> Dict[str, Any]:
        """Analyze budget patterns from context."""
        budgets = []
        for memory in context.get("budget_patterns", []):
            content = memory.get("memory", "")
            # Extract budget numbers (simplified)
            import re

            budget_matches = re.findall(r"\$(\d+)", content)
            budgets.extend([int(b) for b in budget_matches])

        if budgets:
            return {
                "average_budget": sum(budgets) / len(budgets),
                "max_budget": max(budgets),
                "min_budget": min(budgets),
            }
        return {"budget_info": "No budget data available"}

    def _analyze_frequency(self, context: Dict[str, List]) -> Dict[str, Any]:
        """Analyze travel frequency from context."""
        trips = context.get("past_trips", [])
        return {
            "total_trips": len(trips),
            "estimated_frequency": "Regular" if len(trips) > 5 else "Occasional",
        }

    def _analyze_activities(self, context: Dict[str, List]) -> Dict[str, Any]:
        """Analyze activity preferences from context."""
        activities = []
        for memory in context.get("activity_preferences", []) + context.get(
            "preferences", []
        ):
            content = memory.get("memory", "").lower()
            activity_keywords = [
                "museum",
                "beach",
                "hiking",
                "shopping",
                "dining",
                "nightlife",
                "culture",
            ]
            for keyword in activity_keywords:
                if keyword in content:
                    activities.append(keyword)

        return {
            "preferred_activities": list(set(activities)),
            "activity_style": "Cultural"
            if "museum" in activities or "culture" in activities
            else "Adventure",
        }

    def _analyze_travel_style(self, context: Dict[str, List]) -> Dict[str, Any]:
        """Analyze overall travel style from context."""
        style_indicators = {
            "luxury": ["luxury", "expensive", "high-end", "premium"],
            "budget": ["budget", "cheap", "affordable", "backpack"],
            "family": ["family", "kids", "children"],
            "solo": ["solo", "alone", "independent"],
            "group": ["group", "friends", "together"],
        }

        all_content = " ".join(
            [
                memory.get("memory", "").lower()
                for memory_list in context.values()
                if isinstance(memory_list, list)
                for memory in memory_list
            ]
        )

        detected_styles = []
        for style, keywords in style_indicators.items():
            if any(keyword in all_content for keyword in keywords):
                detected_styles.append(style)

        return {
            "travel_styles": detected_styles,
            "primary_style": detected_styles[0] if detected_styles else "general",
        }

    def _generate_context_summary(
        self, context: Dict[str, Any], insights: Dict[str, Any]
    ) -> str:
        """Generate a human-readable summary of user context."""
        summary_parts = []

        # Destination preferences
        destinations = insights.get("preferred_destinations", {}).get(
            "most_visited", []
        )
        if destinations:
            summary_parts.append(
                f"Frequently travels to: {', '.join(destinations[:3])}"
            )

        # Travel style
        travel_style = insights.get("travel_style", {}).get("primary_style")
        if travel_style and travel_style != "general":
            summary_parts.append(f"Travel style: {travel_style}")

        # Budget range
        budget_info = insights.get("budget_range", {})
        if "average_budget" in budget_info:
            avg_budget = budget_info["average_budget"]
            summary_parts.append(f"Average budget: ${avg_budget:.0f}")

        # Activity preferences
        activities = insights.get("preferred_activities", {}).get(
            "preferred_activities", []
        )
        if activities:
            summary_parts.append(f"Enjoys: {', '.join(activities[:3])}")

        return (
            ". ".join(summary_parts)
            if summary_parts
            else "New user with limited travel history"
        )


# Dependency function for FastAPI
async def get_memory_service() -> MemoryService:
    """
    Get memory service instance for dependency injection.

    Returns:
        MemoryService instance
    """
    return MemoryService()
