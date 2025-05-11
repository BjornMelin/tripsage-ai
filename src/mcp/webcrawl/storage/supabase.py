"""Supabase storage implementation for WebCrawl MCP."""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Import Supabase client
try:
    from src.db.client import get_supabase_client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not available")


class SupabaseStorage:
    """Supabase storage service for WebCrawl MCP.

    This service implements the persistent storage layer using Supabase
    for TripSage's web crawling data.
    """

    def __init__(self):
        """Initialize the Supabase storage service."""
        self._client = None

        if SUPABASE_AVAILABLE:
            try:
                self._client = get_supabase_client()
                logger.info("Supabase storage initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")

    async def store_page_content(
        self,
        url: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store extracted page content in Supabase.

        Args:
            url: The URL of the webpage
            title: The title of the webpage
            content: The extracted content
            metadata: Optional metadata about the extraction

        Returns:
            ID of the created record or None if storage failed
        """
        if not self._client:
            logger.error("Supabase client not available")
            return None

        try:
            # Prepare data
            data = {
                "url": url,
                "title": title,
                "content": content,
                "metadata": json.dumps(metadata) if metadata else json.dumps({}),
                "crawled_at": "now()",
            }

            # Insert data
            result = await self._client.table("webcrawl_content").insert(data).execute()

            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("id")

            return None
        except Exception as e:
            logger.error(f"Error storing page content in Supabase: {str(e)}")
            return None

    async def store_destination_info(
        self,
        destination: str,
        topics: Dict[str, List[Dict[str, Any]]],
        sources: List[str],
    ) -> Optional[str]:
        """Store destination information in Supabase.

        Args:
            destination: The name of the destination
            topics: Information by topic
            sources: List of source names

        Returns:
            ID of the created record or None if storage failed
        """
        if not self._client:
            logger.error("Supabase client not available")
            return None

        try:
            # Prepare data
            data = {
                "destination": destination,
                "topics": json.dumps(topics),
                "sources": json.dumps(sources),
                "crawled_at": "now()",
            }

            # Insert data
            result = (
                await self._client.table("destination_insights").insert(data).execute()
            )

            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("id")

            return None
        except Exception as e:
            logger.error(f"Error storing destination info in Supabase: {str(e)}")
            return None

    async def create_price_monitor(
        self,
        url: str,
        price_selector: str,
        monitoring_id: str,
        frequency: str,
        notification_threshold: float,
        initial_price: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create a price monitoring record in Supabase.

        Args:
            url: The URL of the webpage to monitor
            price_selector: The CSS selector for the price element
            monitoring_id: Unique monitoring ID
            frequency: Monitoring frequency (hourly, daily, weekly)
            notification_threshold: Percentage change to trigger notification
            initial_price: Initial price data (amount, currency, timestamp)

        Returns:
            ID of the created record or None if creation failed
        """
        if not self._client:
            logger.error("Supabase client not available")
            return None

        try:
            # Prepare data
            data = {
                "url": url,
                "price_selector": price_selector,
                "monitoring_id": monitoring_id,
                "frequency": frequency,
                "notification_threshold": notification_threshold,
                "initial_price": json.dumps(initial_price) if initial_price else None,
                "created_at": "now()",
                "last_checked": "now()",
                "status": "scheduled",
            }

            # Insert data
            result = await self._client.table("price_monitors").insert(data).execute()

            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("id")

            return None
        except Exception as e:
            logger.error(f"Error creating price monitor in Supabase: {str(e)}")
            return None

    async def store_price_check(
        self,
        monitoring_id: str,
        price_data: Dict[str, Any],
        change_percent: Optional[float] = None,
    ) -> Optional[str]:
        """Store a price check result in Supabase.

        Args:
            monitoring_id: The monitoring ID
            price_data: Price data (amount, currency, timestamp)
            change_percent: Percentage change from previous check

        Returns:
            ID of the created record or None if storage failed
        """
        if not self._client:
            logger.error("Supabase client not available")
            return None

        try:
            # Prepare data
            data = {
                "monitoring_id": monitoring_id,
                "price_data": json.dumps(price_data),
                "change_percent": change_percent,
                "checked_at": "now()",
            }

            # Insert data
            result = await self._client.table("price_checks").insert(data).execute()

            # Update the price monitor's last_checked timestamp
            await self._client.table("price_monitors").update(
                {
                    "last_checked": "now()",
                    "current_price": json.dumps(price_data) if price_data else None,
                }
            ).eq("monitoring_id", monitoring_id).execute()

            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("id")

            return None
        except Exception as e:
            logger.error(f"Error storing price check in Supabase: {str(e)}")
            return None

    async def store_events(
        self,
        destination: str,
        date_range: Dict[str, str],
        events: List[Dict[str, Any]],
        sources: List[str],
    ) -> Optional[str]:
        """Store events in Supabase.

        Args:
            destination: The name of the destination
            date_range: Start and end dates
            events: List of events
            sources: List of source names

        Returns:
            ID of the created record or None if storage failed
        """
        if not self._client:
            logger.error("Supabase client not available")
            return None

        try:
            # Prepare data
            data = {
                "destination": destination,
                "date_range": json.dumps(date_range),
                "events": json.dumps(events),
                "sources": json.dumps(sources),
                "event_count": len(events),
                "crawled_at": "now()",
            }

            # Insert data
            result = (
                await self._client.table("destination_events").insert(data).execute()
            )

            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("id")

            return None
        except Exception as e:
            logger.error(f"Error storing events in Supabase: {str(e)}")
            return None

    async def store_blog_insights(
        self,
        destination: str,
        topics: Dict[str, List[Dict[str, Any]]],
        sources: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Store blog insights in Supabase.

        Args:
            destination: The name of the destination
            topics: Insights by topic
            sources: List of blog sources

        Returns:
            ID of the created record or None if storage failed
        """
        if not self._client:
            logger.error("Supabase client not available")
            return None

        try:
            # Prepare data
            data = {
                "destination": destination,
                "topics": json.dumps(topics),
                "sources": json.dumps(sources),
                "crawled_at": "now()",
            }

            # Insert data
            result = await self._client.table("blog_insights").insert(data).execute()

            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("id")

            return None
        except Exception as e:
            logger.error(f"Error storing blog insights in Supabase: {str(e)}")
            return None
