"""Knowledge graph storage implementation for WebCrawl MCP."""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Import Memory MCP client
try:
    from src.utils.mcp import call_mcp_tool

    MEMORY_MCP_AVAILABLE = True
except ImportError:
    MEMORY_MCP_AVAILABLE = False
    logger.warning("Memory MCP tools not available")


class KnowledgeGraphStorage:
    """Knowledge graph storage service for WebCrawl MCP.

    This service implements the semantic storage layer using Memory MCP
    for TripSage's web crawling data.
    """

    async def store_page_content(
        self,
        url: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store extracted page content in the knowledge graph.

        Args:
            url: The URL of the webpage
            title: The title of the webpage
            content: The extracted content
            metadata: Optional metadata about the extraction

        Returns:
            Entity name in the knowledge graph or None if storage failed
        """
        if not MEMORY_MCP_AVAILABLE:
            logger.error("Memory MCP tools not available")
            return None

        try:
            # Create entity name
            entity_name = f"webpage-{hash(url) & 0xFFFFFFFF}"

            # Create entity with observations
            result = await call_mcp_tool(
                "mcp__memory__create_entities",
                {
                    "entities": [
                        {
                            "name": entity_name,
                            "entityType": "Webpage",
                            "observations": [
                                f"Title: {title}",
                                f"URL: {url}",
                                (
                                    f"Content summary: {content[:500]}..."
                                    if len(content) > 500
                                    else f"Content: {content}"
                                ),
                            ],
                        }
                    ]
                },
            )

            # Add metadata as observations if available
            if metadata:
                observations = []
                for key, value in metadata.items():
                    if value:
                        observations.append(
                            {
                                "entityName": entity_name,
                                "contents": [f"Metadata - {key}: {value}"],
                            }
                        )

                if observations:
                    await call_mcp_tool(
                        "mcp__memory__add_observations", {"observations": observations}
                    )

            return entity_name
        except Exception as e:
            logger.error(f"Error storing page content in knowledge graph: {str(e)}")
            return None

    async def store_destination_info(
        self,
        destination: str,
        topics: Dict[str, List[Dict[str, Any]]],
        sources: List[str],
    ) -> Optional[List[str]]:
        """Store destination information in the knowledge graph.

        Args:
            destination: The name of the destination
            topics: Information by topic
            sources: List of source names

        Returns:
            List of created entity names or None if storage failed
        """
        if not MEMORY_MCP_AVAILABLE:
            logger.error("Memory MCP tools not available")
            return None

        try:
            # Create destination entity if it doesn't exist
            destination_entity = await self._get_or_create_destination(destination)

            # Create entities for each topic
            created_entities = []
            relations = []

            for topic_name, topic_results in topics.items():
                # Clean topic name for use as entity name
                clean_topic = topic_name.lower().replace(" ", "_")

                # Create topic entity name
                topic_entity_name = f"{destination}-{clean_topic}"

                # Prepare observations for this topic
                topic_observations = [f"Topic: {topic_name} for {destination}"]

                for result in topic_results:
                    topic_observations.append(
                        f"From {result.get('source', 'unknown')}: {result.get('title', '')} - {result.get('content', '')[:300]}..."
                    )

                # Create topic entity
                await call_mcp_tool(
                    "mcp__memory__create_entities",
                    {
                        "entities": [
                            {
                                "name": topic_entity_name,
                                "entityType": "DestinationTopic",
                                "observations": topic_observations,
                            }
                        ]
                    },
                )

                created_entities.append(topic_entity_name)

                # Create relation between destination and topic
                relations.append(
                    {
                        "from": destination_entity,
                        "to": topic_entity_name,
                        "relationType": "has_information_about",
                    }
                )

            # Create relations
            if relations:
                await call_mcp_tool(
                    "mcp__memory__create_relations", {"relations": relations}
                )

            return created_entities
        except Exception as e:
            logger.error(f"Error storing destination info in knowledge graph: {str(e)}")
            return None

    async def store_price_monitor(
        self,
        url: str,
        price_selector: str,
        monitoring_id: str,
        frequency: str,
        initial_price: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store price monitoring configuration in the knowledge graph.

        Args:
            url: The URL of the webpage to monitor
            price_selector: The CSS selector for the price element
            monitoring_id: Unique monitoring ID
            frequency: Monitoring frequency (hourly, daily, weekly)
            initial_price: Initial price data (amount, currency, timestamp)

        Returns:
            Entity name in the knowledge graph or None if storage failed
        """
        if not MEMORY_MCP_AVAILABLE:
            logger.error("Memory MCP tools not available")
            return None

        try:
            # Create entity name for price monitor
            entity_name = f"price-monitor-{monitoring_id}"

            # Prepare observations
            observations = [
                f"URL: {url}",
                f"Price selector: {price_selector}",
                f"Monitoring ID: {monitoring_id}",
                f"Frequency: {frequency}",
            ]

            # Add initial price if available
            if initial_price:
                price_str = f"Initial price: {initial_price.get('amount')} {initial_price.get('currency')} at {initial_price.get('timestamp')}"
                observations.append(price_str)

            # Create entity
            result = await call_mcp_tool(
                "mcp__memory__create_entities",
                {
                    "entities": [
                        {
                            "name": entity_name,
                            "entityType": "PriceMonitor",
                            "observations": observations,
                        }
                    ]
                },
            )

            return entity_name
        except Exception as e:
            logger.error(f"Error storing price monitor in knowledge graph: {str(e)}")
            return None

    async def store_price_check(
        self,
        monitoring_id: str,
        price_data: Dict[str, Any],
        change_percent: Optional[float] = None,
    ) -> bool:
        """Store a price check result in the knowledge graph.

        Args:
            monitoring_id: The monitoring ID
            price_data: Price data (amount, currency, timestamp)
            change_percent: Percentage change from previous check

        Returns:
            True if successful, False otherwise
        """
        if not MEMORY_MCP_AVAILABLE:
            logger.error("Memory MCP tools not available")
            return False

        try:
            # Get entity name for the price monitor
            entity_name = f"price-monitor-{monitoring_id}"

            # Prepare observation
            price_str = f"Price check: {price_data.get('amount')} {price_data.get('currency')} at {price_data.get('timestamp')}"

            if change_percent is not None:
                price_str += f" (change: {change_percent:+.2f}%)"

            # Add observation to the price monitor entity
            await call_mcp_tool(
                "mcp__memory__add_observations",
                {
                    "observations": [
                        {"entityName": entity_name, "contents": [price_str]}
                    ]
                },
            )

            return True
        except Exception as e:
            logger.error(f"Error storing price check in knowledge graph: {str(e)}")
            return False

    async def store_events(
        self, destination: str, date_range: Dict[str, str], events: List[Dict[str, Any]]
    ) -> Optional[List[str]]:
        """Store events in the knowledge graph.

        Args:
            destination: The name of the destination
            date_range: Start and end dates
            events: List of events

        Returns:
            List of created entity names or None if storage failed
        """
        if not MEMORY_MCP_AVAILABLE:
            logger.error("Memory MCP tools not available")
            return None

        try:
            # Create destination entity if it doesn't exist
            destination_entity = await self._get_or_create_destination(destination)

            # Create entities for each event
            created_entities = []
            relations = []

            for event in events:
                # Create a unique entity name for the event
                name = event.get("name", "")
                if not name:
                    continue

                # Clean name for use as entity name
                clean_name = name.lower().replace(" ", "_")[:30]
                date = event.get("date", "").replace("-", "")

                # Create event entity name
                event_entity_name = f"event-{destination}-{clean_name}-{date}"

                # Prepare observations for this event
                observations = [
                    f"Event: {name}",
                    f"Date: {event.get('date', '')}",
                    f"Time: {event.get('time', '')}" if event.get("time") else "",
                    f"Venue: {event.get('venue', '')}" if event.get("venue") else "",
                    (
                        f"Category: {event.get('category', '')}"
                        if event.get("category")
                        else ""
                    ),
                    (
                        f"Description: {event.get('description', '')}"
                        if event.get("description")
                        else ""
                    ),
                ]

                # Remove empty observations
                observations = [obs for obs in observations if obs]

                # Create event entity
                await call_mcp_tool(
                    "mcp__memory__create_entities",
                    {
                        "entities": [
                            {
                                "name": event_entity_name,
                                "entityType": "Event",
                                "observations": observations,
                            }
                        ]
                    },
                )

                created_entities.append(event_entity_name)

                # Create relation between destination and event
                relations.append(
                    {
                        "from": destination_entity,
                        "to": event_entity_name,
                        "relationType": "hosts",
                    }
                )

            # Create relations
            if relations:
                await call_mcp_tool(
                    "mcp__memory__create_relations", {"relations": relations}
                )

            return created_entities
        except Exception as e:
            logger.error(f"Error storing events in knowledge graph: {str(e)}")
            return None

    async def store_blog_insights(
        self,
        destination: str,
        topics: Dict[str, List[Dict[str, Any]]],
        sources: List[Dict[str, Any]],
    ) -> Optional[List[str]]:
        """Store blog insights in the knowledge graph.

        Args:
            destination: The name of the destination
            topics: Insights by topic
            sources: List of blog sources

        Returns:
            List of created entity names or None if storage failed
        """
        if not MEMORY_MCP_AVAILABLE:
            logger.error("Memory MCP tools not available")
            return None

        try:
            # Create destination entity if it doesn't exist
            destination_entity = await self._get_or_create_destination(destination)

            # Create entities for each topic
            created_entities = []
            relations = []

            for topic_name, topic_insights in topics.items():
                # Clean topic name for use as entity name
                clean_topic = topic_name.lower().replace(" ", "_")

                # Create topic entity name
                topic_entity_name = f"{destination}-blog-{clean_topic}"

                # Prepare observations for this topic
                topic_observations = [
                    f"Blog insights on {topic_name} for {destination}"
                ]

                for insight in topic_insights:
                    source = insight.get("source", {})
                    source_name = source.get("title", source.get("url", "unknown"))

                    summary = insight.get("summary", "")
                    key_points = insight.get("key_points", [])
                    key_points_str = ", ".join(key_points) if key_points else ""

                    # Add source's insight
                    topic_observations.append(f"From {source_name}: {summary}")

                    if key_points_str:
                        topic_observations.append(f"Key points: {key_points_str}")

                # Create topic entity
                await call_mcp_tool(
                    "mcp__memory__create_entities",
                    {
                        "entities": [
                            {
                                "name": topic_entity_name,
                                "entityType": "BlogInsight",
                                "observations": topic_observations,
                            }
                        ]
                    },
                )

                created_entities.append(topic_entity_name)

                # Create relation between destination and blog insight
                relations.append(
                    {
                        "from": destination_entity,
                        "to": topic_entity_name,
                        "relationType": "has_blog_insight",
                    }
                )

            # Create relations
            if relations:
                await call_mcp_tool(
                    "mcp__memory__create_relations", {"relations": relations}
                )

            return created_entities
        except Exception as e:
            logger.error(f"Error storing blog insights in knowledge graph: {str(e)}")
            return None

    async def _get_or_create_destination(self, destination: str) -> str:
        """Get or create a destination entity in the knowledge graph.

        Args:
            destination: The name of the destination

        Returns:
            Entity name in the knowledge graph
        """
        # Clean destination name for use as entity name
        clean_destination = destination.lower().replace(" ", "_").replace(",", "")
        destination_entity = f"destination-{clean_destination}"

        try:
            # Check if entity already exists
            search_result = await call_mcp_tool(
                "mcp__memory__search_nodes", {"query": destination_entity}
            )

            if (
                search_result
                and "nodes" in search_result
                and len(search_result["nodes"]) > 0
            ):
                # Entity already exists
                return destination_entity

            # Create new destination entity
            await call_mcp_tool(
                "mcp__memory__create_entities",
                {
                    "entities": [
                        {
                            "name": destination_entity,
                            "entityType": "Destination",
                            "observations": [f"Name: {destination}"],
                        }
                    ]
                },
            )

            return destination_entity
        except Exception as e:
            logger.error(f"Error in get_or_create_destination: {str(e)}")
            # Return the entity name anyway, in case the error was with searching
            return destination_entity
