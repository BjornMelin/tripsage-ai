"""Helpers for persisting normalized web crawl results to storage backends."""

import json
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Any, cast

from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class WebCrawlPersistence:
    """Handles persistence of web crawl results."""

    def __init__(self):
        """Initialize the web crawl persistence manager."""
        # Import dynamically to avoid circular imports
        from tripsage.db.initialize import get_supabase_client

        self.supabase = get_supabase_client()
        # Memory operations use the high-level functions in tripsage.tools.memory_tools.
        # Avoid storing an un-awaited service here.

    async def store_crawl_result(
        self, result: dict[str, Any], session_id: str | None = None
    ) -> bool:
        """Store a web crawl result in Supabase and Memory MCP.

        Args:
            result: The normalized crawl result
            session_id: Optional session identifier for grouping related results

        Returns:
            True if storage was successful, False otherwise
        """
        success_supabase = await self._store_in_supabase(
            result, "web_crawl_results", session_id
        )
        success_memory = await self._store_in_memory(result)

        return success_supabase and success_memory

    async def store_search_result(
        self, result: dict[str, Any], session_id: str | None = None
    ) -> bool:
        """Store a web search result in Supabase and Memory MCP.

        Args:
            result: The normalized search result
            session_id: Optional session identifier for grouping related results

        Returns:
            True if storage was successful, False otherwise
        """
        success_supabase = await self._store_in_supabase(
            result, "web_search_results", session_id
        )
        success_memory = await self._store_in_memory(result)

        return success_supabase and success_memory

    async def store_price_result(
        self,
        result: dict[str, Any],
        product_type: str,
        session_id: str | None = None,
    ) -> bool:
        """Store a price monitoring result in Supabase and Memory MCP.

        Args:
            result: The normalized price result
            product_type: Type of product (flight, hotel, car_rental, etc.)
            session_id: Optional session identifier for grouping related results

        Returns:
            True if storage was successful, False otherwise
        """
        # Add product type to result for storage
        result_with_type = result.copy()
        result_with_type["product_type"] = product_type

        success_supabase = await self._store_in_supabase(
            result_with_type, "price_monitoring_results", session_id
        )
        success_memory = await self._store_in_memory(result_with_type)

        # Store price history specifically for each item
        for item in result.get("items", []):
            await self._store_price_history(item, product_type)

        return success_supabase and success_memory

    async def store_events_result(
        self, result: dict[str, Any], session_id: str | None = None
    ) -> bool:
        """Store an events result in Supabase and Memory MCP.

        Args:
            result: The normalized events result
            session_id: Optional session identifier for grouping related results

        Returns:
            True if storage was successful, False otherwise
        """
        success_supabase = await self._store_in_supabase(
            result, "events_results", session_id
        )
        success_memory = await self._store_events_in_memory(result)

        return success_supabase and success_memory

    async def store_blog_result(
        self, result: dict[str, Any], session_id: str | None = None
    ) -> bool:
        """Store a blog crawl result in Supabase and Memory MCP.

        Args:
            result: The normalized blog result
            session_id: Optional session identifier for grouping related results

        Returns:
            True if storage was successful, False otherwise
        """
        success_supabase = await self._store_in_supabase(
            result, "blog_crawl_results", session_id
        )
        success_memory = await self._store_blog_in_memory(result)

        return success_supabase and success_memory

    async def _store_in_supabase(
        self, result: dict[str, Any], table: str, session_id: str | None = None
    ) -> bool:
        """Store a result in Supabase.

        Args:
            result: The result to store
            table: The table to store the result in
            session_id: Optional session identifier

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Prepare data for storage
            data = {
                "result_data": json.dumps(result),
                "created_at": datetime.now(UTC).isoformat(),
                "success": result.get("success", False),
                "session_id": session_id,
            }

            # Add specific fields based on result type
            if "url" in result:
                data["url"] = result["url"]
            if "query" in result:
                data["query"] = result["query"]
            if "destination" in result:
                data["destination"] = result["destination"]
            if "extract_type" in result:
                data["extract_type"] = result["extract_type"]
            if "source" in result:
                data["source"] = result["source"]

            # Insert into Supabase
            try:
                self.supabase.table(table).insert(data).execute()
                logger.info("Successfully stored result in Supabase table: %s", table)
                return True
            except Exception:
                logger.exception("Supabase storage error")
                return False

        except Exception:
            logger.exception("Error storing result in Supabase")
            return False

    async def _store_in_memory(self, result: dict[str, Any]) -> bool:
        """Store a result in the Mem0 memory system.

        Args:
            result: The result to store

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Import conversation message for memory storage
            from tripsage.tools.memory_tools import (
                ConversationMessage,
                add_conversation_memory,
            )

            # Extract content for memory storage
            url = result.get("url", "")
            query = result.get("query", "")
            # source = result.get("source", "webcrawl")

            # Collect all content from items
            content_items = []
            for item in result.get("items", []):
                title = item.get("title", "")
                content = item.get("content", "")
                if title and content:
                    content_items.append(f"{title}: {content}")
                elif content:
                    content_items.append(content)
                elif title:
                    content_items.append(title)

            if not content_items:
                logger.warning("No content found to store in memory")
                return True  # Not an error, just nothing to store

            # Create conversation for memory extraction
            content_text = "\n".join(content_items[:5])  # Limit to first 5 items
            memory_messages = [
                ConversationMessage(
                    role="system",
                    content=(
                        "Extract travel-related information from web crawl results."
                    ),
                ),
                ConversationMessage(
                    role="user",
                    content=f"Web content from {url or query}: {content_text}",
                ),
            ]

            # Store in memory using system user ID for web crawl results
            mem_result = await cast(
                Awaitable[dict[str, Any]],
                add_conversation_memory(
                    messages=memory_messages,
                    user_id="system",  # Use system user for general web crawl data
                    context_type="web_crawl",
                ),
            )

            if mem_result.get("status") == "success":
                logger.info(
                    "Successfully stored web crawl result in memory: "
                    "%s memories extracted",
                    mem_result.get("memories_extracted", 0),
                )
                return True

            logger.warning(
                "Memory storage completed with issues: %s",
                mem_result.get("error", "Unknown"),
            )
            return False

        except Exception:
            logger.exception("Error storing result in memory")
            return False

    async def _store_events_in_memory(self, result: dict[str, Any]) -> bool:
        """Store an events result in the memory system.

        Args:
            result: The result to store

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            from tripsage.tools.memory_tools import (
                ConversationMessage,
                add_conversation_memory,
            )

            destination_name = result.get("destination", "")
            if not destination_name:
                return await self._store_in_memory(result)

            # Collect event information
            event_descriptions = []
            for item in result.get("items", []):
                event_info = []
                if item.get("title"):
                    event_info.append(f"Event: {item['title']}")
                if item.get("description"):
                    event_info.append(f"Description: {item['description']}")
                if item.get("start_date"):
                    event_info.append(f"Start: {item['start_date']}")
                if item.get("venue"):
                    event_info.append(f"Venue: {item['venue']}")
                if item.get("event_type"):
                    event_info.append(f"Type: {item['event_type']}")

                if event_info:
                    event_descriptions.append(" | ".join(event_info))

            if not event_descriptions:
                logger.warning("No event information found to store in memory")
                return True

            # Create conversation for memory extraction
            events_text = "\n".join(event_descriptions)
            memory_messages = [
                ConversationMessage(
                    role="system",
                    content=(
                        "Extract event and destination information from search results."
                    ),
                ),
                ConversationMessage(
                    role="user",
                    content=f"Events found in {destination_name}: {events_text}",
                ),
            ]

            # Store in memory
            mem_result = await cast(
                Awaitable[dict[str, Any]],
                add_conversation_memory(
                    messages=memory_messages,
                    user_id="system",
                    context_type="events_crawl",
                ),
            )

            if mem_result.get("status") == "success":
                logger.info(
                    "Successfully stored events in memory for %s: "
                    "%s memories extracted",
                    destination_name,
                    mem_result.get("memories_extracted", 0),
                )
                return True

            logger.warning(
                "Events memory storage had issues: %s",
                mem_result.get("error", "Unknown"),
            )
            return False

        except Exception:
            logger.exception("Error storing events in memory")
            return False

    async def _store_blog_in_memory(self, result: dict[str, Any]) -> bool:
        """Store a blog crawl result in the memory system.

        Args:
            result: The result to store

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            from tripsage.tools.memory_tools import (
                ConversationMessage,
                add_conversation_memory,
            )

            # Extract basic information
            url = result.get("url", "")
            extract_type = result.get("extract_type", "")

            if not url:
                return await self._store_in_memory(result)

            # Collect blog content based on extract_type
            blog_content = []
            for item in result.get("items", []):
                title = item.get("title", "")
                if title:
                    blog_content.append(f"Title: {title}")

                # Add specific extracted data based on extract_type
                if extract_type == "insights":
                    insights = item.get("insights", [])
                    if insights:
                        blog_content.append(f"Insights: {'; '.join(insights)}")
                elif extract_type == "itinerary":
                    itinerary = item.get("itinerary", [])
                    if itinerary:
                        blog_content.append(f"Itinerary: {'; '.join(itinerary)}")
                elif extract_type == "tips":
                    tips = item.get("tips", [])
                    if tips:
                        blog_content.append(f"Travel Tips: {'; '.join(tips)}")
                elif extract_type == "places":
                    places = item.get("places", [])
                    if places:
                        blog_content.append(f"Places Mentioned: {'; '.join(places)}")
                else:
                    # Fallback to content if no specific extracted data
                    content = item.get("content", "")
                    if content:
                        blog_content.append(content[:500])  # Limit content size

            if not blog_content:
                logger.warning("No blog content found to store in memory")
                return True

            # Create conversation for memory extraction
            content_text = "\n".join(blog_content)
            memory_messages = [
                ConversationMessage(
                    role="system",
                    content=(
                        "Extract travel insights, tips, and destination information "
                        "from travel blog content."
                    ),
                ),
                ConversationMessage(
                    role="user",
                    content=(
                        f"Travel blog content from {url} ({extract_type}): "
                        f"{content_text}"
                    ),
                ),
            ]

            # Store in memory
            mem_result = await cast(
                Awaitable[dict[str, Any]],
                add_conversation_memory(
                    messages=memory_messages,
                    user_id="system",
                    context_type="blog_crawl",
                ),
            )

            if mem_result.get("status") == "success":
                logger.info(
                    "Successfully stored blog in memory from %s: %s memories extracted",
                    url,
                    mem_result.get("memories_extracted", 0),
                )
                return True

            logger.warning(
                "Blog memory storage had issues: %s",
                mem_result.get("error", "Unknown"),
            )
            return False

        except Exception:
            logger.exception("Error storing blog in memory")
            return False

    async def _store_price_history(
        self, item: dict[str, Any], product_type: str
    ) -> bool:
        """Store a price history entry in Supabase.

        Args:
            item: The item with price data
            product_type: Type of product (flight, hotel, car_rental, etc.)

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Prepare data for storage
            data = {
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "price": item.get("price", 0),
                "currency": item.get("currency", "USD"),
                "timestamp": item.get("price_timestamp", datetime.now(UTC).isoformat()),
                "product_type": product_type,
                "availability": item.get("availability", ""),
            }

            # Insert into Supabase
            response: Any = self.supabase.table("price_history").insert(data).execute()

            if not cast(dict, response).get("data"):
                logger.exception(
                    "Supabase price history storage error: No data returned"
                )
                return False

            logger.info(
                "Successfully stored price history in Supabase for %s",
                item.get("title", ""),
            )
            return True

        except Exception:
            logger.exception("Error storing price history in Supabase")
            return False


# Singleton instance
persistence_manager = WebCrawlPersistence()


def get_persistence_manager() -> WebCrawlPersistence:
    """Get the singleton instance of the web crawl persistence manager.

    Returns:
        The persistence manager instance
    """
    return persistence_manager
