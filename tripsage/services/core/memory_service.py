"""
TripSage Memory Service - Mem0 Implementation

Production-ready memory service using Mem0 with pgvector backend.
Replaces the complex Neo4j/MCP memory system with a simpler, more efficient approach.

Based on comprehensive research from
docs/REFACTOR/MEMORY_SEARCH/RESEARCH_DB_MEMORY_SEARCH.md
showing Mem0 achieves:
- 91% lower latency than full-context approaches
- 26% higher accuracy than OpenAI's memory implementation
- $60-120/month cost vs $500+ for complex solutions
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from mem0 import Memory
from pydantic import BaseModel, Field

from tripsage_core.config.base_app_settings import get_settings
from tripsage_core.config.feature_flags import IntegrationMode, feature_flags
from tripsage_core.config.service_registry import ServiceAdapter, ServiceProtocol
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MemorySearchResult(BaseModel):
    """Memory search result with metadata."""

    id: str
    memory: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    categories: List[str] = Field(default_factory=list)
    similarity: float = 0.0
    created_at: datetime
    user_id: str


class ConversationMemory(BaseModel):
    """Conversation memory model."""

    messages: List[Dict[str, str]]
    user_id: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TripSageMemoryService(ServiceProtocol):
    """Production-ready memory service using Mem0 with pgvector backend.

    This service completely replaces the Neo4j/MCP memory approach with a simpler,
    more efficient Mem0-based implementation optimized for travel planning use cases.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the memory service.

        Args:
            config: Optional Mem0 configuration. Uses default if None.
        """
        self.config = config or self._get_default_config()
        self.memory: Optional[Memory] = None
        self._connected = False
        self._cache: Dict[str, Tuple[List[MemorySearchResult], float]] = {}
        self._cache_ttl = 300  # 5 minutes

        logger.info(
            f"TripSageMemoryService initialized with provider: "
            f"{self.config.get('vector_store', {}).get('provider')}"
        )

    def _get_default_config(self) -> Dict[str, Any]:
        """Get optimized configuration for TripSage using pgvector.

        Returns:
            Mem0 configuration optimized for travel planning domain
        """
        return {
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": "db.example.supabase.co",
                    "port": 5432,
                    "dbname": "postgres",
                    "user": "postgres",
                    "password": "test-password",
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
            "version": "v1.1",  # Mem0 version tracking
        }

    async def connect(self) -> None:
        """Initialize service connection (required by ServiceProtocol)."""
        if self._connected:
            return

        try:
            self.memory = Memory.from_config(self.config)
            self._connected = True
            logger.info("Memory service connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect memory service: {str(e)}")
            raise

    async def close(self) -> None:
        """Close service connection (required by ServiceProtocol)."""
        if not self._connected:
            return

        try:
            # Mem0 handles cleanup internally
            self._connected = False
            self._cache.clear()
            logger.info("Memory service closed successfully")
        except Exception as e:
            logger.error(f"Error closing memory service: {str(e)}")

    @property
    def is_connected(self) -> bool:
        """Check if service is connected."""
        return self._connected

    async def health_check(self) -> bool:
        """Health check for service monitoring.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not self._connected:
                await self.connect()

            # Simple test to verify memory service is working
            await asyncio.to_thread(
                self.memory.search,
                query="health_check_test",
                user_id="health_check_user",
                limit=1,
            )
            return True
        except Exception as e:
            logger.error(f"Memory service health check failed: {str(e)}")
            return False

    @with_error_handling
    async def add_conversation_memory(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract and store memories from conversation.

        Args:
            messages: List of conversation messages
            user_id: User identifier
            session_id: Optional session identifier
            metadata: Optional additional metadata

        Returns:
            Memory extraction result with usage statistics
        """
        if not self._connected:
            await self.connect()

        try:
            # Add travel-specific metadata
            enhanced_metadata = {
                "domain": "travel_planning",
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "conversation",
            }
            if metadata:
                enhanced_metadata.update(metadata)

            # Use Mem0's automatic extraction with travel domain optimization
            result = await asyncio.to_thread(
                self.memory.add,
                messages=messages,
                user_id=user_id,
                metadata=enhanced_metadata,
            )

            # Clear user's cache after adding new memories
            self._invalidate_user_cache(user_id)

            # Log memory extraction metrics
            memory_count = len(result.get("results", []))
            tokens_used = result.get("usage", {}).get("total_tokens", 0)

            logger.info(
                f"Memory extracted successfully for user {user_id}, "
                f"session {session_id}, memory_count={memory_count}, "
                f"tokens_used={tokens_used}"
            )

            return result

        except Exception as e:
            logger.error(f"Memory extraction failed for user {user_id}: {str(e)}")
            return {"results": [], "error": str(e)}

    @with_error_handling
    async def search_memories(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.3,
    ) -> List[MemorySearchResult]:
        """Search user memories with caching and optimization.

        Args:
            query: Search query
            user_id: User identifier
            limit: Maximum number of results
            filters: Optional metadata/category filters
            similarity_threshold: Minimum similarity score

        Returns:
            List of memory search results
        """
        if not self._connected:
            await self.connect()

        # Check cache first
        cache_key = f"{user_id}:{query}:{limit}:{hash(str(filters))}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result

        try:
            # Check feature flag for memory service
            if feature_flags.get_integration_mode("memory") == IntegrationMode.MCP:
                # Fall back to MCP if needed (during migration)
                return await self._search_via_mcp(query, user_id, filters, limit)

            # Direct SDK path (default)
            results = await asyncio.to_thread(
                self.memory.search,
                query=query,
                user_id=user_id,
                limit=limit,
                filters=filters or {},
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
                    created_at=datetime.fromisoformat(
                        result.get("created_at", datetime.now(timezone.utc).isoformat())
                    ),
                    user_id=user_id,
                )

                # Filter by similarity threshold
                if memory_result.similarity >= similarity_threshold:
                    memory_results.append(memory_result)

            # Cache the results
            self._cache_result(cache_key, memory_results)

            # Enrich with travel context if needed
            enriched_results = await self._enrich_travel_memories(memory_results)

            logger.debug(
                "Memory search completed",
                user_id=user_id,
                query=query,
                results_count=len(enriched_results),
            )

            return enriched_results

        except Exception as e:
            logger.error(
                f"Memory search failed for user {user_id}, query '{query}': {str(e)}"
            )
            return []

    @with_error_handling
    async def get_user_context(
        self, user_id: str, context_type: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        """Get comprehensive user context for personalization.

        Args:
            user_id: User identifier
            context_type: Optional context type filter
            limit: Maximum memories to retrieve

        Returns:
            Organized user context with categories and insights
        """
        if not self._connected:
            await self.connect()

        try:
            # Retrieve all user memories
            all_memories = await asyncio.to_thread(
                self.memory.get_all, user_id=user_id, limit=limit
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
                # metadata = memory.get("metadata", {})

                # Categorize memories based on categories and content analysis
                for category in categories:
                    if category in context:
                        context[category].append(memory)

                # Additional categorization based on content
                memory_content = memory.get("memory", "").lower()
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
            context["insights"] = await self._derive_travel_insights(context)
            context["summary"] = self._generate_context_summary(context)

            return context

        except Exception as e:
            logger.error(f"Failed to get user context for user {user_id}: {str(e)}")
            # Return default context structure on error
            return {
                "preferences": [],
                "past_trips": [],
                "saved_destinations": [],
                "budget_patterns": [],
                "travel_style": [],
                "dietary_restrictions": [],
                "accommodation_preferences": [],
                "activity_preferences": [],
                "insights": {
                    "preferred_destinations": {
                        "most_visited": [],
                        "destination_count": 0,
                    },
                    "budget_range": {"budget_info": "No budget data available"},
                    "travel_frequency": {
                        "total_trips": 0,
                        "estimated_frequency": "Occasional",
                    },
                    "preferred_activities": {
                        "preferred_activities": [],
                        "activity_style": "Adventure",
                    },
                    "travel_style": {"travel_styles": [], "primary_style": "general"},
                },
                "summary": "New user with limited travel history",
            }

    @with_error_handling
    async def update_user_preferences(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user travel preferences in memory.

        Args:
            user_id: User identifier
            preferences: Dictionary of preferences to update

        Returns:
            Update result
        """
        if not self._connected:
            await self.connect()

        try:
            # Create conversation messages for preference update
            preference_messages = [
                {
                    "role": "system",
                    "content": (
                        "Extract and update user travel preferences from the following "
                        "information."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"My travel preferences: {json.dumps(preferences, indent=2)}"
                    ),
                },
            ]

            result = await self.add_conversation_memory(
                messages=preference_messages,
                user_id=user_id,
                metadata={
                    "type": "preferences_update",
                    "category": "travel_preferences",
                    "source": "preference_api",
                },
            )

            logger.info(
                f"User preferences updated for user {user_id}, "
                f"preferences_count={len(preferences)}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to update user preferences for user {user_id}: {str(e)}"
            )
            return {"error": str(e)}

    @with_error_handling
    async def delete_user_memories(
        self, user_id: str, memory_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Delete user memories (GDPR compliance).

        Args:
            user_id: User identifier
            memory_ids: Optional list of specific memory IDs to delete

        Returns:
            Deletion result
        """
        if not self._connected:
            await self.connect()

        try:
            if memory_ids:
                # Delete specific memories
                deleted_count = 0
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
                    limit=1000,  # Get all memories
                )

                deleted_count = 0
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
                f"User memories deleted for user {user_id}, "
                f"deleted_count={deleted_count}"
            )
            return {"deleted_count": deleted_count, "success": True}

        except Exception as e:
            logger.error(f"Failed to delete user memories for user {user_id}: {str(e)}")
            return {"error": str(e), "success": False}

    def _get_cached_result(self, cache_key: str) -> Optional[List[MemorySearchResult]]:
        """Get cached search result if still valid.

        Args:
            cache_key: Cache key

        Returns:
            Cached result if valid, None otherwise
        """
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: List[MemorySearchResult]) -> None:
        """Cache search result.

        Args:
            cache_key: Cache key
            result: Search result to cache
        """
        self._cache[cache_key] = (result, time.time())

        # Simple cache size management
        if len(self._cache) > 1000:
            # Remove oldest 200 entries
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:200]:
                del self._cache[key]

    def _invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate cache entries for a specific user.

        Args:
            user_id: User identifier
        """
        keys_to_remove = [
            key for key in self._cache.keys() if key.startswith(f"{user_id}:")
        ]
        for key in keys_to_remove:
            del self._cache[key]

    async def _enrich_travel_memories(
        self, memories: List[MemorySearchResult]
    ) -> List[MemorySearchResult]:
        """Enrich memories with travel-specific context.

        Args:
            memories: List of memory results

        Returns:
            Enriched memory results
        """
        # Add travel-specific enrichment logic here
        # Could integrate with maps/weather services for location-based memories
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
        """Derive insights from user's travel history and preferences.

        Args:
            context: Organized user context

        Returns:
            Travel insights dictionary
        """
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
            # Extract common travel activities
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
            "activity_style": (
                "Cultural"
                if "museum" in activities or "culture" in activities
                else "Adventure"
            ),
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

    def _generate_context_summary(self, context: Dict[str, Any]) -> str:
        """Generate a human-readable summary of user context.

        Args:
            context: User context dictionary

        Returns:
            Summary string
        """
        insights = context.get("insights", {})

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

    async def _search_via_mcp(
        self, query: str, user_id: str, filters: Optional[Dict[str, Any]], limit: int
    ) -> List[MemorySearchResult]:
        """Fallback to MCP memory search during migration.

        Args:
            query: Search query
            user_id: User identifier
            filters: Search filters
            limit: Result limit

        Returns:
            Memory search results via MCP
        """
        # Placeholder for MCP fallback during migration
        # This would use the existing Neo4j MCP client if needed
        logger.warning("MCP memory fallback not implemented - using empty results")
        return []


class MemoryServiceAdapter(ServiceAdapter):
    """Service adapter for memory service supporting both MCP and direct integration."""

    def __init__(self):
        super().__init__("memory")
        self._memory_service = None

    async def get_mcp_client(self):
        """Get MCP client instance (fallback during migration)."""
        # This would return the Neo4j MCP client if needed during migration
        # For now, we're doing a complete replacement
        raise NotImplementedError("MCP memory client deprecated - use direct service")

    async def get_direct_service(self) -> TripSageMemoryService:
        """Get direct service instance."""
        if self._memory_service is None:
            self._memory_service = TripSageMemoryService()
            await self._memory_service.connect()

        return self._memory_service


# Global memory service instance for easy access
_memory_service: Optional[TripSageMemoryService] = None


async def get_memory_service() -> TripSageMemoryService:
    """Get the global memory service instance.

    Returns:
        TripSageMemoryService instance
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = TripSageMemoryService()
        await _memory_service.connect()

    return _memory_service


def create_memory_hash(content: str) -> str:
    """Create a hash for memory content deduplication.

    Args:
        content: Memory content

    Returns:
        SHA-256 hash of the content
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
