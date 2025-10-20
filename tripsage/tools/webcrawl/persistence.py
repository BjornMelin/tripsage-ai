"""Web crawl persistence utilities.

This module provides functionality to persist web crawl results to Supabase and
the Memory MCP knowledge graph.
"""

import json
from datetime import UTC, datetime
from typing import Any

from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class WebCrawlPersistence:
    """Handles persistence of web crawl results."""

    def __init__(self):
        """Initialize the web crawl persistence manager."""
        # Import dynamically to avoid circular imports
        from tripsage.tools.memory_tools import get_memory_service
        from tripsage.tools.supabase_tools import get_supabase_client

        self.supabase = get_supabase_client()
        self.memory_service = get_memory_service()

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
            response = await self.supabase.insert(table, data)

            if "error" in response:
                logger.exception(f"Supabase storage error: {response.get('error')}")
                return False

            logger.info(f"Successfully stored result in Supabase table: {table}")
            return True

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
            memory_result = await add_conversation_memory(
                messages=memory_messages,
                user_id="system",  # Use system user for general web crawl data
                context_type="web_crawl",
            )

            if memory_result.get("status") == "success":
                logger.info(
                    f"Successfully stored web crawl result in memory: "
                    f"{memory_result.get('memories_extracted', 0)} memories extracted"
                )
                return True
            else:
                logger.warning(
                    f"Memory storage completed with issues: "
                    f"{memory_result.get('error', 'Unknown')}"
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
            memory_result = await add_conversation_memory(
                messages=memory_messages, user_id="system", context_type="events_crawl"
            )

            if memory_result.get("status") == "success":
                logger.info(
                    f"Successfully stored events in memory for {destination_name}: "
                    f"{memory_result.get('memories_extracted', 0)} memories extracted"
                )
                return True
            else:
                logger.warning(
                    f"Events memory storage had issues: "
                    f"{memory_result.get('error', 'Unknown')}"
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
            memory_result = await add_conversation_memory(
                messages=memory_messages, user_id="system", context_type="blog_crawl"
            )

            if memory_result.get("status") == "success":
                logger.info(
                    f"Successfully stored blog in memory from {url}: "
                    f"{memory_result.get('memories_extracted', 0)} memories extracted"
                )
                return True
            else:
                logger.warning(
                    f"Blog memory storage had issues: "
                    f"{memory_result.get('error', 'Unknown')}"
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
            response = await self.supabase.insert("price_history", data)

            if "error" in response:
                logger.exception(
                    f"Supabase price history storage error: {response.get('error')}"
                )
                return False

            logger.info(
                f"Successfully stored price history in Supabase for "
                f"{item.get('title', '')}"
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
