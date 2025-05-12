"""
Neo4j client interface.

This module provides a client interface for Neo4j operations,
exposing high-level methods for working with the knowledge graph.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.db.neo4j.connection import Neo4jConnection
from src.db.neo4j.exceptions import Neo4jConnectionError, Neo4jQueryError
from src.db.neo4j.repositories.accommodation import AccommodationRepository
from src.db.neo4j.repositories.activity import ActivityRepository
from src.db.neo4j.repositories.destination import DestinationRepository
from src.db.neo4j.repositories.event import EventRepository
from src.db.neo4j.repositories.transportation import TransportationRepository
from src.db.neo4j.schemas.accommodation import Accommodation
from src.db.neo4j.schemas.activity import Activity
from src.db.neo4j.schemas.destination import Destination
from src.db.neo4j.schemas.event import Event
from src.db.neo4j.schemas.transportation import Transportation
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class Neo4jClient:
    """Client interface for Neo4j operations."""

    def __init__(self):
        """Initialize the Neo4j client."""
        self.connection = Neo4jConnection()
        self.destination_repo = DestinationRepository()
        self.activity_repo = ActivityRepository()
        self.accommodation_repo = AccommodationRepository()
        self.event_repo = EventRepository()
        self.transportation_repo = TransportationRepository()

    async def initialize(self) -> None:
        """Initialize the Neo4j database."""
        # Ensure connection
        if not self.connection.is_connected():
            raise Neo4jConnectionError("Cannot initialize: Not connected to Neo4j")

        # Create constraints and indexes
        await self.ensure_indexes_and_constraints()

        # Seed initial data
        await self.seed_initial_data()

        logger.info("Neo4j database initialized successfully")

    async def ensure_indexes_and_constraints(self) -> None:
        """Ensure all required indexes and constraints are created."""
        from src.db.neo4j.migrations.constraints import create_constraints
        from src.db.neo4j.migrations.indexes import create_indexes

        # Execute constraints first
        create_constraints(self.connection)

        # Then create indexes
        create_indexes(self.connection)

        logger.info("Neo4j indexes and constraints created successfully")

    async def seed_initial_data(self) -> None:
        """Seed initial data into the database."""
        from src.db.neo4j.migrations.initial_data import seed_initial_data

        seed_initial_data(self.connection)
        logger.info("Neo4j initial data seeded successfully")

    async def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            Query results
        """
        return await self.connection.run_query_async(query, parameters)

    async def execute_transaction(
        self, statements: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Execute multiple statements in a transaction.

        Args:
            statements: List of statement dictionaries, each containing
            'query' and 'parameters'

        Returns:
            List of results for each statement
        """
        return await self.connection.run_transaction_async(statements)

    # Destination operations

    async def add_destination(self, destination: Dict[str, Any]) -> Destination:
        """Add a new destination.

        Args:
            destination: Destination data

        Returns:
            Created destination
        """
        # Create Destination model
        destination_model = Destination(**destination)

        # Save to Neo4j
        return await self.destination_repo.create(destination_model)

    async def update_destination(
        self, name: str, destination: Dict[str, Any]
    ) -> Optional[Destination]:
        """Update an existing destination.

        Args:
            name: Destination name to update
            destination: Updated destination data

        Returns:
            Updated destination if successful, None if not found
        """
        # Create Destination model
        destination_model = Destination(**destination)

        # Update in Neo4j
        return await self.destination_repo.update(name, destination_model)

    async def delete_destination(self, name: str) -> bool:
        """Delete a destination.

        Args:
            name: Destination name

        Returns:
            True if deleted, False if not found
        """
        return await self.destination_repo.delete(name)

    async def get_destination(self, name: str) -> Optional[Destination]:
        """Get a destination by name.

        Args:
            name: Destination name

        Returns:
            Destination if found, None otherwise
        """
        return await self.destination_repo.get_by_id(name)

    async def get_all_destinations(
        self, limit: int = 100, skip: int = 0
    ) -> List[Destination]:
        """Get all destinations with pagination.

        Args:
            limit: Maximum number of destinations to return
            skip: Number of destinations to skip

        Returns:
            List of destinations
        """
        return await self.destination_repo.get_all(limit, skip)

    async def find_destinations_by_country(self, country: str) -> List[Destination]:
        """Find destinations by country.

        Args:
            country: Country name

        Returns:
            List of destinations
        """
        return await self.destination_repo.find_by_country(country)

    async def find_nearby_destinations(
        self, latitude: float, longitude: float, distance_km: float = 50
    ) -> List[Destination]:
        """Find destinations near a location.

        Args:
            latitude: Latitude
            longitude: Longitude
            distance_km: Maximum distance in kilometers

        Returns:
            List of nearby destinations
        """
        return await self.destination_repo.find_nearby(latitude, longitude, distance_km)

    async def create_destination_relationship(
        self,
        from_destination: str,
        relationship_type: str,
        to_destination: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a relationship between destinations.

        Args:
            from_destination: Source destination name
            relationship_type: Relationship type
            to_destination: Target destination name
            properties: Relationship properties

        Returns:
            True if successful
        """
        return await self.destination_repo.create_relationship(
            from_destination, relationship_type, to_destination, properties
        )

    async def find_destinations_by_popularity(
        self, min_rating: float = 3.0, limit: int = 10
    ) -> List[Destination]:
        """Find destinations by popularity rating.

        Args:
            min_rating: Minimum safety rating
            limit: Maximum number of results

        Returns:
            List of popular destinations
        """
        return await self.destination_repo.find_by_popularity(min_rating, limit)

    async def find_destinations_by_interests(
        self, interests: List[str], limit: int = 10
    ) -> List[Destination]:
        """Find destinations by interests.

        Args:
            interests: List of interests
            limit: Maximum number of results

        Returns:
            List of matching destinations
        """
        return await self.destination_repo.search_by_interests(interests, limit)

    # Activity operations

    async def add_activity(self, activity: Dict[str, Any]) -> Activity:
        """Add a new activity.

        Args:
            activity: Activity data

        Returns:
            Created activity
        """
        # Create Activity model
        activity_model = Activity(**activity)

        # Save to Neo4j
        return await self.activity_repo.create(activity_model)

    async def update_activity(
        self, name: str, activity: Dict[str, Any]
    ) -> Optional[Activity]:
        """Update an existing activity.

        Args:
            name: Activity name to update
            activity: Updated activity data

        Returns:
            Updated activity if successful, None if not found
        """
        # Create Activity model
        activity_model = Activity(**activity)

        # Update in Neo4j
        return await self.activity_repo.update(name, activity_model)

    async def delete_activity(self, name: str) -> bool:
        """Delete an activity.

        Args:
            name: Activity name

        Returns:
            True if deleted, False if not found
        """
        return await self.activity_repo.delete(name)

    async def get_activity(self, name: str) -> Optional[Activity]:
        """Get an activity by name.

        Args:
            name: Activity name

        Returns:
            Activity if found, None otherwise
        """
        return await self.activity_repo.get_by_id(name)

    async def get_activities_by_destination(
        self, destination_name: str
    ) -> List[Activity]:
        """Get activities by destination.

        Args:
            destination_name: Destination name

        Returns:
            List of activities at the destination
        """
        return await self.activity_repo.find_by_destination(destination_name)

    async def get_top_rated_activities(
        self, limit: int = 10, destination: Optional[str] = None
    ) -> List[Activity]:
        """Get top-rated activities.

        Args:
            limit: Maximum number of activities to return
            destination: Optional destination name filter

        Returns:
            List of top-rated activities
        """
        return await self.activity_repo.find_top_rated(limit, destination)

    # Accommodation operations

    async def add_accommodation(self, accommodation: Dict[str, Any]) -> Accommodation:
        """Add a new accommodation.

        Args:
            accommodation: Accommodation data

        Returns:
            Created accommodation
        """
        # Create Accommodation model
        accommodation_model = Accommodation(**accommodation)

        # Save to Neo4j
        return await self.accommodation_repo.create(accommodation_model)

    async def update_accommodation(
        self, name: str, accommodation: Dict[str, Any]
    ) -> Optional[Accommodation]:
        """Update an existing accommodation.

        Args:
            name: Accommodation name to update
            accommodation: Updated accommodation data

        Returns:
            Updated accommodation if successful, None if not found
        """
        # Create Accommodation model
        accommodation_model = Accommodation(**accommodation)

        # Update in Neo4j
        return await self.accommodation_repo.update(name, accommodation_model)

    async def delete_accommodation(self, name: str) -> bool:
        """Delete an accommodation.

        Args:
            name: Accommodation name

        Returns:
            True if deleted, False if not found
        """
        return await self.accommodation_repo.delete(name)

    async def get_accommodation(self, name: str) -> Optional[Accommodation]:
        """Get an accommodation by name.

        Args:
            name: Accommodation name

        Returns:
            Accommodation if found, None otherwise
        """
        return await self.accommodation_repo.get_by_id(name)

    async def get_accommodations_by_destination(
        self, destination_name: str
    ) -> List[Accommodation]:
        """Get accommodations by destination.

        Args:
            destination_name: Destination name

        Returns:
            List of accommodations at the destination
        """
        return await self.accommodation_repo.find_by_destination(destination_name)

    async def get_accommodations_with_amenities(
        self, amenities: List[str], destination: Optional[str] = None
    ) -> List[Accommodation]:
        """Get accommodations with specific amenities.

        Args:
            amenities: List of required amenities
            destination: Optional destination name filter

        Returns:
            List of accommodations with the required amenities
        """
        return await self.accommodation_repo.find_with_amenities(amenities, destination)

    # Event operations

    async def add_event(self, event: Dict[str, Any]) -> Event:
        """Add a new event.

        Args:
            event: Event data

        Returns:
            Created event
        """
        # Create Event model
        event_model = Event(**event)

        # Save to Neo4j
        return await self.event_repo.create(event_model)

    async def update_event(
        self, name: str, event: Dict[str, Any]
    ) -> Optional[Event]:
        """Update an existing event.

        Args:
            name: Event name to update
            event: Updated event data

        Returns:
            Updated event if successful, None if not found
        """
        # Create Event model
        event_model = Event(**event)

        # Update in Neo4j
        return await self.event_repo.update(name, event_model)

    async def delete_event(self, name: str) -> bool:
        """Delete an event.

        Args:
            name: Event name

        Returns:
            True if deleted, False if not found
        """
        return await self.event_repo.delete(name)

    async def get_event(self, name: str) -> Optional[Event]:
        """Get an event by name.

        Args:
            name: Event name

        Returns:
            Event if found, None otherwise
        """
        return await self.event_repo.get_by_id(name)

    async def get_events_by_destination(self, destination_name: str) -> List[Event]:
        """Get events by destination.

        Args:
            destination_name: Destination name

        Returns:
            List of events at the destination
        """
        return await self.event_repo.find_by_destination(destination_name)

    async def get_upcoming_events(
        self, days: int = 30, destination: Optional[str] = None
    ) -> List[Event]:
        """Get upcoming events.

        Args:
            days: Number of days to look ahead
            destination: Optional destination name filter

        Returns:
            List of upcoming events
        """
        return await self.event_repo.find_upcoming_events(days, destination)

    # Transportation operations

    async def add_transportation(
        self, transportation: Dict[str, Any]
    ) -> Transportation:
        """Add a new transportation option.

        Args:
            transportation: Transportation data

        Returns:
            Created transportation
        """
        # Create Transportation model
        transportation_model = Transportation(**transportation)

        # Save to Neo4j
        return await self.transportation_repo.create(transportation_model)

    async def update_transportation(
        self, name: str, transportation: Dict[str, Any]
    ) -> Optional[Transportation]:
        """Update an existing transportation option.

        Args:
            name: Transportation name to update
            transportation: Updated transportation data

        Returns:
            Updated transportation if successful, None if not found
        """
        # Create Transportation model
        transportation_model = Transportation(**transportation)

        # Update in Neo4j
        return await self.transportation_repo.update(name, transportation_model)

    async def delete_transportation(self, name: str) -> bool:
        """Delete a transportation option.

        Args:
            name: Transportation name

        Returns:
            True if deleted, False if not found
        """
        return await self.transportation_repo.delete(name)

    async def get_transportation(self, name: str) -> Optional[Transportation]:
        """Get a transportation option by name.

        Args:
            name: Transportation name

        Returns:
            Transportation if found, None otherwise
        """
        return await self.transportation_repo.get_by_id(name)

    async def find_transportation_routes(
        self, origin: str, destination: str, transportation_type: Optional[str] = None
    ) -> List[Transportation]:
        """Find transportation routes between origin and destination.

        Args:
            origin: Origin location
            destination: Destination location
            transportation_type: Optional transportation type filter

        Returns:
            List of matching transportation options
        """
        return await self.transportation_repo.find_routes(
            origin, destination, transportation_type
        )

    # Travel planning operations

    async def find_travel_routes(
        self, from_destination: str, to_destination: str, max_stops: int = 2
    ) -> List[List[Dict[str, Any]]]:
        """Find travel routes between two destinations.

        Args:
            from_destination: Starting destination name
            to_destination: Ending destination name
            max_stops: Maximum number of intermediate stops

        Returns:
            List of routes, each a list of connections
        """
        try:
            # Build Cypher query using variable length path
            query = """
            MATCH path = (start:Destination {name: $from})
            -[connections:CONNECTED_TO*..${max_stops}]->
            (end:Destination {name: $to})
            WITH path, connections, [node IN nodes(path) | node.name] AS places
            RETURN places,
                   [rel IN connections | {
                       from: startNode(rel).name,
                       to: endNode(rel).name,
                       type: type(rel),
                       properties: properties(rel)
                   }] AS route_connections,
                   length(path) AS total_stops
            ORDER BY total_stops
            LIMIT 10
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query,
                parameters={
                    "from": from_destination,
                    "to": to_destination,
                    "max_stops": max_stops
                    + 1,  # Add 1 because the path includes start and end
                },
            )

            return result
        except Exception as e:
            logger.error("Failed to find travel routes: %s", str(e))
            raise Neo4jQueryError(f"Failed to find travel routes: {str(e)}") from e

    async def get_related_destinations(
        self, destination_name: str, relationship_types: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get destinations related to a given destination.

        Args:
            destination_name: The destination name
            relationship_types: Optional list of relationship types to filter by

        Returns:
            Dictionary of relationships and related destinations
        """
        try:
            parameters = {"name": destination_name}

            # Build WHERE clause for relationship types if provided
            type_filter = ""
            if relationship_types:
                type_list = ", ".join([f"'{t}'" for t in relationship_types])
                type_filter = f"WHERE type(r) IN [{type_list}]"

            # Build Cypher query
            query = f"""
            MATCH (d:Destination {{name: $name}})-[r]->(related:Destination)
            {type_filter}
            RETURN type(r) AS relationship,
                   related.name AS destination,
                   properties(r) AS properties,
                   related.type AS type,
                   related.country AS country
            ORDER BY type(r), related.name
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Organize results by relationship type
            related_by_type = {}
            for record in result:
                rel_type = record["relationship"]
                if rel_type not in related_by_type:
                    related_by_type[rel_type] = []

                related_by_type[rel_type].append(
                    {
                        "name": record["destination"],
                        "type": record["type"],
                        "country": record["country"],
                        "properties": record["properties"],
                    }
                )

            return related_by_type

        except Exception as e:
            logger.error("Failed to get related destinations: %s", str(e))
            raise Neo4jQueryError(
                f"Failed to get related destinations: {str(e)}"
            ) from e

    # Knowledge graph operations

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get knowledge graph statistics.

        Returns:
            Dictionary with graph statistics
        """
        try:
            # Build Cypher queries for statistics
            statements = [
                {
                    "query": """
                    MATCH (n)
                    RETURN count(n) AS node_count
                    """
                },
                {
                    "query": """
                    MATCH ()-[r]->()
                    RETURN count(r) AS relationship_count
                    """
                },
                {
                    "query": """
                    MATCH (n)
                    RETURN labels(n) AS label, count(*) AS count
                    ORDER BY count DESC
                    """
                },
                {
                    "query": """
                    MATCH ()-[r]->()
                    RETURN type(r) AS type, count(*) AS count
                    ORDER BY count DESC
                    """
                },
            ]

            # Execute queries in a transaction
            results = await self.connection.run_transaction_async(statements)

            # Extract statistics
            node_count = results[0][0]["node_count"]
            relationship_count = results[1][0]["relationship_count"]

            # Process node labels
            node_labels = {}
            for record in results[2]:
                label = record["label"][0]  # Get first label (primary)
                count = record["count"]
                node_labels[label] = count

            # Process relationship types
            relationship_types = {}
            for record in results[3]:
                r_type = record["type"]
                count = record["count"]
                relationship_types[r_type] = count

            return {
                "node_count": node_count,
                "relationship_count": relationship_count,
                "node_labels": node_labels,
                "relationship_types": relationship_types,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get graph statistics: %s", str(e))
            raise Neo4jQueryError(f"Failed to get graph statistics: {str(e)}") from e

    async def run_knowledge_graph_search(
        self, search_term: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Run a full-text search across the knowledge graph.

        Args:
            search_term: Search term
            limit: Maximum number of results

        Returns:
            List of matching nodes with scores
        """
        try:
            # Build Cypher query for search
            query = """
            CALL db.index.fulltext.queryNodes(
                "destination_description_index", 
                $search_term
            ) YIELD node, score
            RETURN
                node.name AS name,
                labels(node)[0] AS type,
                score,
                node.country AS country,
                node.description AS description
            ORDER BY score DESC
            LIMIT $limit
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"search_term": search_term, "limit": limit}
            )

            return result

        except Exception as e:
            logger.error("Failed to run knowledge graph search: %s", str(e))
            raise Neo4jQueryError(
                f"Failed to run knowledge graph search: {str(e)}"
            ) from e

    async def find_travel_recommendations(
        self,
        interests: List[str],
        preferred_countries: Optional[List[str]] = None,
        budget_level: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Find travel recommendations based on interests and constraints.

        Args:
            interests: List of traveler interests
            preferred_countries: Optional list of preferred countries
            budget_level: Optional budget level constraint (1-5)

        Returns:
            List of recommended destinations with scores
        """
        try:
            # Build conditions based on parameters
            conditions = ["d.popular_for IS NOT NULL"]
            parameters = {"interests": interests, "limit": 10}

            if preferred_countries:
                conditions.append("d.country IN $preferred_countries")
                parameters["preferred_countries"] = preferred_countries

            if budget_level is not None:
                conditions.append("d.cost_level <= $budget_level")
                parameters["budget_level"] = budget_level

            where_clause = " AND ".join(conditions)

            # Build Cypher query
            query = f"""
            MATCH (d:Destination)
            WHERE {where_clause}
            WITH d,
                 size([x IN $interests WHERE x IN d.popular_for]) AS interest_matches,
                 size(d.popular_for) AS total_interests
            WHERE interest_matches > 0
            RETURN
                d.name AS name,
                d.country AS country,
                d.type AS type,
                d.description AS description,
                d.cost_level AS cost_level,
                d.safety_rating AS safety_rating,
                d.popular_for AS popular_for,
                interest_matches,
                toFloat(interest_matches) / size($interests) AS match_score
            ORDER BY match_score DESC, d.safety_rating DESC
            LIMIT $limit
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            return result

        except Exception as e:
            logger.error("Failed to find travel recommendations: %s", str(e))
            raise Neo4jQueryError(
                f"Failed to find travel recommendations: {str(e)}"
            ) from e

    # Sync with relational database

    async def sync_destination_from_relational(
        self, destination_data: Dict[str, Any]
    ) -> Tuple[Destination, bool]:
        """Sync a destination from relational database to knowledge graph.

        Args:
            destination_data: Destination data from relational database

        Returns:
            Tuple of (destination, created) where created is True if created,
                False if updated
        """
        try:
            name = destination_data.get("name")
            if not name:
                raise ValueError("Destination data must include a name")

            # Check if destination already exists
            existing = await self.get_destination(name)

            if existing:
                # Update existing destination
                destination = await self.update_destination(name, destination_data)
                return destination, False
            else:
                # Create new destination
                destination = await self.add_destination(destination_data)
                return destination, True

        except Exception as e:
            logger.error("Failed to sync destination from relational DB: %s", str(e))
            raise

    # Session and maintenance

    async def run_maintenance(self) -> Dict[str, Any]:
        """Run database maintenance operations.

        Returns:
            Dictionary with maintenance results
        """
        try:
            # Define maintenance queries
            statements = [
                {
                    "query": """
                    MATCH (n)
                    WHERE n:Destination AND NOT exists(n.updated_at)
                    SET n.updated_at = datetime()
                    RETURN count(n) AS updated_timestamps
                    """
                },
                {
                    "query": """
                    MATCH ()-[r:CONNECTED_TO]-()
                    WHERE NOT exists(r.last_verified)
                    SET r.last_verified = datetime()
                    RETURN count(r) AS updated_relationships
                    """
                },
            ]

            # Execute maintenance queries
            results = await self.connection.run_transaction_async(statements)

            return {
                "updated_timestamps": results[0][0]["updated_timestamps"],
                "updated_relationships": results[1][0]["updated_relationships"],
                "ran_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to run maintenance: %s", str(e))
            raise Neo4jQueryError(f"Failed to run maintenance: {str(e)}") from e

    async def close(self) -> None:
        """Close the Neo4j connection."""
        self.connection.close()
        logger.info("Neo4j client closed")


# Create a singleton instance
neo4j_client = Neo4jClient()