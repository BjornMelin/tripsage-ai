"""
Web crawl persistence utilities.

This module provides functionality to persist web crawl results to Supabase and
the Memory MCP knowledge graph.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from src.db.factory import get_provider
from src.mcp.memory.client import get_client as get_memory_client
from src.utils.logging import get_logger

logger = get_logger(__name__)


class WebCrawlPersistence:
    """Handles persistence of web crawl results."""

    def __init__(self):
        """Initialize the web crawl persistence manager."""
        self.supabase = get_provider("supabase")
        self.memory_client = get_memory_client()

    async def store_crawl_result(
        self, result: Dict[str, Any], session_id: Optional[str] = None
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
        self, result: Dict[str, Any], session_id: Optional[str] = None
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
        result: Dict[str, Any],
        product_type: str,
        session_id: Optional[str] = None,
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
        self, result: Dict[str, Any], session_id: Optional[str] = None
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
        self, result: Dict[str, Any], session_id: Optional[str] = None
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
        self, result: Dict[str, Any], table: str, session_id: Optional[str] = None
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
                "created_at": datetime.utcnow().isoformat(),
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

            if response.get("error"):
                logger.error(f"Supabase storage error: {response.get('error')}")
                return False

            logger.info(f"Successfully stored result in Supabase table: {table}")
            return True

        except Exception as e:
            logger.error(f"Error storing result in Supabase: {str(e)}")
            return False

    async def _store_in_memory(self, result: Dict[str, Any]) -> bool:
        """Store a result in the Memory MCP knowledge graph.

        Args:
            result: The result to store

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Extract basic information for entity creation
            url = result.get("url", "")
            query = result.get("query", "")
            entity_name = url or query or f"WebCrawl_{datetime.utcnow().isoformat()}"

            # Determine entity type
            entity_type = "WebPage" if url else "WebSearch"
            if "product_type" in result:
                entity_type = f"{result['product_type'].capitalize()}Product"

            # Create observations from the content
            observations = []
            for item in result.get("items", []):
                # Include title in observation if present
                title = item.get("title", "")
                content = item.get("content", "")
                if title and content:
                    observations.append(f"{title}: {content}")
                elif content:
                    observations.append(content)
                elif title:
                    observations.append(title)

            # Add metadata as observations
            observations.append(f"Source: {result.get('source', 'Unknown')}")
            observations.append(
                f"Timestamp: {result.get('timestamp', datetime.utcnow().isoformat())}"
            )

            # Filter out empty observations
            observations = [obs for obs in observations if obs]

            # Create entity in knowledge graph
            await self.memory_client.create_entities(
                [
                    {
                        "name": entity_name,
                        "entityType": entity_type,
                        "observations": observations,
                    }
                ]
            )

            logger.info(
                f"Successfully stored result in Memory MCP knowledge graph: "
                f"{entity_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Error storing result in Memory MCP: {str(e)}")
            return False

    async def _store_events_in_memory(self, result: Dict[str, Any]) -> bool:
        """Store an events result in the Memory MCP knowledge graph.

        Args:
            result: The result to store

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Create destination entity
            destination_name = result.get("destination", "")
            if not destination_name:
                return await self._store_in_memory(result)

            # Create destination entity
            await self.memory_client.create_entities(
                [
                    {
                        "name": destination_name,
                        "entityType": "Destination",
                        "observations": [
                            f"Events were searched for this destination on "
                            f"{datetime.now(datetime.UTC).isoformat()}"
                        ],
                    }
                ]
            )

            # Create event entities and relations
            for item in result.get("items", []):
                event_name = item.get("title", f"Event_{datetime.utcnow().isoformat()}")

                # Create event entity
                await self.memory_client.create_entities(
                    [
                        {
                            "name": event_name,
                            "entityType": "Event",
                            "observations": [
                                item.get("description", ""),
                                f"Start date: {item.get('start_date', 'Unknown')}",
                                f"End date: {item.get('end_date', 'Unknown')}",
                                f"Venue: {item.get('venue', 'Unknown')}",
                                f"Event type: {item.get('event_type', 'Unknown')}",
                            ],
                        }
                    ]
                )

                # Create relation between event and destination
                await self.memory_client.create_relations(
                    [
                        {
                            "from": event_name,
                            "relationType": "takes_place_in",
                            "to": destination_name,
                        }
                    ]
                )

            logger.info(
                f"Successfully stored events in Memory MCP knowledge graph for "
                f"{destination_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Error storing events in Memory MCP: {str(e)}")
            return False

    async def _store_blog_in_memory(self, result: Dict[str, Any]) -> bool:
        """Store a blog crawl result in the Memory MCP knowledge graph.

        Args:
            result: The result to store

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Extract basic information
            url = result.get("url", "")
            extract_type = result.get("extract_type", "")

            if not url:
                return await self._store_in_memory(result)

            # Create blog entity
            blog_name = f"TravelBlog_{url.split('//')[1].split('/')[0]}"

            # Create observations based on extract_type
            observations = []
            for item in result.get("items", []):
                title = item.get("title", "")
                if title:
                    observations.append(f"Title: {title}")

                # Add specific extracted data based on extract_type
                if extract_type == "insights":
                    for insight in item.get("insights", []):
                        observations.append(f"Insight: {insight}")
                elif extract_type == "itinerary":
                    for day in item.get("itinerary", []):
                        observations.append(f"Itinerary: {day}")
                elif extract_type == "tips":
                    for tip in item.get("tips", []):
                        observations.append(f"Tip: {tip}")
                elif extract_type == "places":
                    for place in item.get("places", []):
                        observations.append(f"Place: {place}")
                else:
                    # Fallback to content if no specific extracted data
                    content = item.get("content", "")
                    if content:
                        observations.append(content[:1000])  # Limit content size

            # Create blog entity
            await self.memory_client.create_entities(
                [
                    {
                        "name": blog_name,
                        "entityType": "TravelBlog",
                        "observations": observations,
                    }
                ]
            )

            # Create places mentioned as separate entities
            if extract_type == "places":
                for item in result.get("items", []):
                    for place in item.get("places", []):
                        # Create place entity
                        await self.memory_client.create_entities(
                            [
                                {
                                    "name": place,
                                    "entityType": "Destination",
                                    "observations": [
                                        f"Mentioned in travel blog: {blog_name}"
                                    ],
                                }
                            ]
                        )

                        # Create relation between place and blog
                        await self.memory_client.create_relations(
                            [
                                {
                                    "from": blog_name,
                                    "relationType": "mentions",
                                    "to": place,
                                }
                            ]
                        )

            logger.info(
                f"Successfully stored blog in Memory MCP knowledge graph: {blog_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Error storing blog in Memory MCP: {str(e)}")
            return False

    async def _store_price_history(
        self, item: Dict[str, Any], product_type: str
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
                "timestamp": item.get("price_timestamp", datetime.utcnow().isoformat()),
                "product_type": product_type,
                "availability": item.get("availability", ""),
            }

            # Insert into Supabase
            response = await self.supabase.insert("price_history", data)

            if response.get("error"):
                logger.error(
                    f"Supabase price history storage error: {response.get('error')}"
                )
                return False

            logger.info(
                f"Successfully stored price history in Supabase for "
                f"{item.get('title', '')}"
            )
            return True

        except Exception as e:
            logger.error(f"Error storing price history in Supabase: {str(e)}")
            return False


# Singleton instance
persistence_manager = WebCrawlPersistence()


def get_persistence_manager() -> WebCrawlPersistence:
    """Get the singleton instance of the web crawl persistence manager.

    Returns:
        The persistence manager instance
    """
    return persistence_manager
