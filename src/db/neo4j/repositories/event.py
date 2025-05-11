"""
Event repository for Neo4j.

This module provides a repository implementation for Event entities in Neo4j.
"""

from datetime import datetime
from typing import List, Optional

from src.db.neo4j.repositories.base import BaseNeo4jRepository
from src.db.neo4j.schemas.event import Event
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class EventRepository(BaseNeo4jRepository[Event]):
    """Repository for Event entities in Neo4j."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(entity_class=Event, label="Event")

    async def find_by_destination(self, destination_name: str) -> List[Event]:
        """Find events by destination.

        Args:
            destination_name: Destination name

        Returns:
            List of events at the specified destination
        """
        try:
            # Build Cypher query
            query = """
            MATCH (e:Event)
            WHERE e.destination = $destination_name
            RETURN e
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"destination_name": destination_name}
            )

            # Convert to events
            events = []
            for record in result:
                event = Event.from_neo4j_node(record["e"])
                events.append(event)

            return events

        except Exception as e:
            logger.error("Failed to find events by destination: %s", str(e))
            raise

    async def find_by_type(
        self, event_type: str, destination: Optional[str] = None
    ) -> List[Event]:
        """Find events by type, optionally at a specific destination.

        Args:
            event_type: Event type
            destination: Optional destination name

        Returns:
            List of matching events
        """
        try:
            # Build parameters
            parameters = {"event_type": event_type}
            if destination:
                parameters["destination"] = destination
                where_clause = "e.type = $event_type AND e.destination = $destination"
            else:
                where_clause = "e.type = $event_type"

            # Build Cypher query
            query = f"""
            MATCH (e:Event)
            WHERE {where_clause}
            RETURN e
            ORDER BY e.start_date ASC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to events
            events = []
            for record in result:
                event = Event.from_neo4j_node(record["e"])
                events.append(event)

            return events

        except Exception as e:
            logger.error("Failed to find events by type: %s", str(e))
            raise

    async def create_event_destination_relationship(
        self, event_name: str, destination_name: str
    ) -> bool:
        """Create a relationship between an event and a destination.

        Args:
            event_name: Event name
            destination_name: Destination name

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build Cypher query
            query = """
            MATCH (e:Event {name: $event_name})
            MATCH (d:Destination {name: $destination_name})
            CREATE (e)-[r:TAKES_PLACE_IN]->(d)
            RETURN r
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query,
                parameters={
                    "event_name": event_name,
                    "destination_name": destination_name,
                },
            )

            return len(result) > 0

        except Exception as e:
            logger.error("Failed to create event-destination relationship: %s", str(e))
            raise

    async def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        destination: Optional[str] = None,
    ) -> List[Event]:
        """Find events within a date range.

        Args:
            start_date: Start date
            end_date: End date
            destination: Optional destination name

        Returns:
            List of matching events
        """
        try:
            # Build parameters
            parameters = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
            if destination:
                parameters["destination"] = destination
                where_clause = (
                    "e.start_date >= $start_date AND e.end_date <= $end_date "
                    "AND e.destination = $destination"
                )
            else:
                where_clause = "e.start_date >= $start_date AND e.end_date <= $end_date"

            # Build Cypher query
            query = f"""
            MATCH (e:Event)
            WHERE {where_clause}
            RETURN e
            ORDER BY e.start_date ASC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to events
            events = []
            for record in result:
                event = Event.from_neo4j_node(record["e"])
                events.append(event)

            return events

        except Exception as e:
            logger.error("Failed to find events by date range: %s", str(e))
            raise

    async def find_upcoming_events(
        self, days: int = 30, destination: Optional[str] = None
    ) -> List[Event]:
        """Find upcoming events for the next N days.

        Args:
            days: Number of days to look ahead
            destination: Optional destination name

        Returns:
            List of upcoming events
        """
        try:
            # Calculate dates
            now = datetime.utcnow()
            future = datetime(
                now.year, now.month, now.day + days, now.hour, now.minute, now.second
            )

            # Build parameters
            parameters = {
                "now": now.isoformat(),
                "future": future.isoformat(),
            }
            if destination:
                parameters["destination"] = destination
                where_clause = (
                    "e.start_date >= $now AND e.start_date <= $future "
                    "AND e.destination = $destination"
                )
            else:
                where_clause = "e.start_date >= $now AND e.start_date <= $future"

            # Build Cypher query
            query = f"""
            MATCH (e:Event)
            WHERE {where_clause}
            RETURN e
            ORDER BY e.start_date ASC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to events
            events = []
            for record in result:
                event = Event.from_neo4j_node(record["e"])
                events.append(event)

            return events

        except Exception as e:
            logger.error("Failed to find upcoming events: %s", str(e))
            raise

    async def find_by_price_range(
        self, min_price: float, max_price: float, destination: Optional[str] = None
    ) -> List[Event]:
        """Find events within a price range.

        Args:
            min_price: Minimum ticket price
            max_price: Maximum ticket price
            destination: Optional destination name

        Returns:
            List of matching events
        """
        try:
            # Build parameters
            parameters = {"min_price": min_price, "max_price": max_price}
            if destination:
                parameters["destination"] = destination
                where_clause = (
                    "e.ticket_price >= $min_price AND e.ticket_price <= $max_price "
                    "AND e.destination = $destination"
                )
            else:
                where_clause = (
                    "e.ticket_price >= $min_price AND e.ticket_price <= $max_price"
                )

            # Build Cypher query
            query = f"""
            MATCH (e:Event)
            WHERE {where_clause}
            RETURN e
            ORDER BY e.ticket_price ASC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to events
            events = []
            for record in result:
                event = Event.from_neo4j_node(record["e"])
                events.append(event)

            return events

        except Exception as e:
            logger.error("Failed to find events by price range: %s", str(e))
            raise
