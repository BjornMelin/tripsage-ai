"""
Neo4j initial data seeder.

This module provides functions to seed initial travel data into the Neo4j database,
providing a baseline of destinations and relationships for the knowledge graph.
"""

from datetime import datetime
from typing import Any, Dict, List

from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


def get_initial_destinations() -> List[Dict[str, Any]]:
    """Get initial destination data.

    Returns:
        List of destination dictionaries
    """
    return [
        {
            "name": "Paris",
            "country": "France",
            "region": "Île-de-France",
            "city": "Paris",
            "description": (
                "The City of Light, known for the Eiffel Tower and Louvre Museum."
            ),
            "type": "city",
            "latitude": 48.8566,
            "longitude": 2.3522,
            "popular_for": ["art", "cuisine", "romance", "architecture", "fashion"],
            "languages": ["French"],
            "currency": "EUR",
            "timezone": "Europe/Paris",
            "weather_climate": "Temperate",
            "weather_best_time": ["April", "May", "June", "September", "October"],
            "weather_avg_temp": '{"January": 5, "July": 25}',
            "safety_rating": 4.0,
            "cost_level": 4,
        },
        {
            "name": "Tokyo",
            "country": "Japan",
            "region": "Kanto",
            "city": "Tokyo",
            "description": "Japan's busy capital, mixing ultramodern with traditional.",
            "type": "city",
            "latitude": 35.6762,
            "longitude": 139.6503,
            "popular_for": ["technology", "cuisine", "shopping", "culture", "gardens"],
            "languages": ["Japanese"],
            "currency": "JPY",
            "timezone": "Asia/Tokyo",
            "weather_climate": "Temperate",
            "weather_best_time": ["March", "April", "October", "November"],
            "weather_avg_temp": '{"January": 5, "July": 25}',
            "safety_rating": 5.0,
            "cost_level": 4,
        },
        {
            "name": "New York City",
            "country": "United States",
            "region": "New York",
            "city": "New York",
            "description": (
                "Major commercial and cultural center known for " "iconic landmarks."
            ),
            "type": "city",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "popular_for": ["shopping", "arts", "dining", "theater", "museums"],
            "languages": ["English"],
            "currency": "USD",
            "timezone": "America/New_York",
            "weather_climate": "Continental",
            "weather_best_time": ["April", "May", "September", "October"],
            "weather_avg_temp": '{"January": 0, "July": 25}',
            "safety_rating": 3.5,
            "cost_level": 5,
        },
        {
            "name": "London",
            "country": "United Kingdom",
            "region": "England",
            "city": "London",
            "description": (
                "Historic city on the Thames with iconic architecture and culture."
            ),
            "type": "city",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "popular_for": ["history", "museums", "theater", "shopping", "parks"],
            "languages": ["English"],
            "currency": "GBP",
            "timezone": "Europe/London",
            "weather_climate": "Temperate",
            "weather_best_time": ["May", "June", "September"],
            "weather_avg_temp": '{"January": 4, "July": 19}',
            "safety_rating": 4.0,
            "cost_level": 4,
        },
        {
            "name": "Grand Canyon",
            "country": "United States",
            "region": "Arizona",
            "description": "A steep-sided canyon carved by the Colorado River.",
            "type": "landmark",
            "latitude": 36.0544,
            "longitude": -112.2401,
            "popular_for": ["hiking", "photography", "nature", "adventure"],
            "languages": ["English"],
            "currency": "USD",
            "timezone": "America/Phoenix",
            "weather_climate": "Desert",
            "weather_best_time": ["March", "April", "May", "September", "October"],
            "weather_avg_temp": '{"January": 2, "July": 35}',
            "safety_rating": 4.0,
            "cost_level": 3,
        },
        {
            "name": "Barcelona",
            "country": "Spain",
            "region": "Catalonia",
            "city": "Barcelona",
            "description": "Vibrant city known for architecture, beaches, and cuisine.",
            "type": "city",
            "latitude": 41.3851,
            "longitude": 2.1734,
            "popular_for": ["architecture", "beaches", "cuisine", "nightlife", "art"],
            "languages": ["Spanish", "Catalan"],
            "currency": "EUR",
            "timezone": "Europe/Madrid",
            "weather_climate": "Mediterranean",
            "weather_best_time": ["May", "June", "September", "October"],
            "weather_avg_temp": '{"January": 10, "July": 28}',
            "safety_rating": 3.5,
            "cost_level": 3,
        },
        {
            "name": "Kyoto",
            "country": "Japan",
            "region": "Kansai",
            "city": "Kyoto",
            "description": (
                "Former capital known for classical Buddhist temples and gardens."
            ),
            "type": "city",
            "latitude": 35.0116,
            "longitude": 135.7681,
            "popular_for": ["temples", "gardens", "history", "culture", "cuisine"],
            "languages": ["Japanese"],
            "currency": "JPY",
            "timezone": "Asia/Tokyo",
            "weather_climate": "Temperate",
            "weather_best_time": ["March", "April", "October", "November"],
            "weather_avg_temp": '{"January": 4, "July": 29}',
            "safety_rating": 5.0,
            "cost_level": 3,
        },
    ]


def get_initial_relationships() -> List[Dict[str, Any]]:
    """Get initial relationship data.

    Returns:
        List of relationship dictionaries
    """
    return [
        {
            "from": "Paris",
            "to": "London",
            "type": "CONNECTED_TO",
            "properties": {"distance_km": 344, "transport": ["train", "flight"]},
        },
        {
            "from": "New York City",
            "to": "London",
            "type": "CONNECTED_TO",
            "properties": {"distance_km": 5567, "transport": ["flight"]},
        },
        {
            "from": "Tokyo",
            "to": "Kyoto",
            "type": "CONNECTED_TO",
            "properties": {"distance_km": 372, "transport": ["train", "flight", "bus"]},
        },
        {
            "from": "Paris",
            "to": "Barcelona",
            "type": "CONNECTED_TO",
            "properties": {"distance_km": 831, "transport": ["flight", "train"]},
        },
        {
            "from": "London",
            "to": "Barcelona",
            "type": "CONNECTED_TO",
            "properties": {"distance_km": 1137, "transport": ["flight"]},
        },
        {
            "from": "New York City",
            "to": "Grand Canyon",
            "type": "TRAVEL_ROUTE",
            "properties": {"popularity": "high", "travel_time_hours": 5.5},
        },
    ]


def seed_initial_data(connection) -> bool:
    """Seed initial data into Neo4j.

    Args:
        connection: Neo4j connection instance

    Returns:
        True if successful

    Raises:
        Neo4jQueryError: If seeding fails
    """
    # Create destinations
    destinations = get_initial_destinations()
    for destination in destinations:
        try:
            # Check if destination already exists
            query = """
            MATCH (d:Destination {name: $name})
            RETURN count(d) > 0 AS exists
            """
            result = connection.run_query(query, {"name": destination["name"]})

            if not result[0]["exists"]:
                # Add timestamps
                destination["created_at"] = datetime.utcnow().isoformat()
                destination["updated_at"] = datetime.utcnow().isoformat()

                # Create destination
                create_query = """
                CREATE (d:Destination $properties)
                RETURN d
                """
                connection.run_query(create_query, {"properties": destination})
                logger.info("Created destination: %s", destination["name"])
        except Exception as e:
            logger.error(
                "Failed to create destination %s: %s", destination["name"], str(e)
            )
            raise

    # Create relationships between destinations
    relationships = get_initial_relationships()
    for rel in relationships:
        try:
            # Check if destinations exist
            query = """
            MATCH (a:Destination {name: $from}), (b:Destination {name: $to})
            RETURN count(a) > 0 AND count(b) > 0 AS both_exist
            """
            result = connection.run_query(query, {"from": rel["from"], "to": rel["to"]})

            if result and result[0]["both_exist"]:
                # Check if relationship already exists
                check_query = f"""
                MATCH (a:Destination {{name: $from}})
                -[r:{rel["type"]}]->(b:Destination {{name: $to}})
                RETURN count(r) > 0 AS exists
                """
                check_result = connection.run_query(
                    check_query, {"from": rel["from"], "to": rel["to"]}
                )

                if not check_result[0]["exists"]:
                    # Create relationship
                    create_query = f"""
                    MATCH (a:Destination {{name: $from}}), (b:Destination {{name: $to}})
                    CREATE (a)-[r:{rel["type"]}]->(b)
                    SET r = $properties
                    RETURN r
                    """
                    connection.run_query(
                        create_query,
                        {
                            "from": rel["from"],
                            "to": rel["to"],
                            "properties": rel["properties"],
                        },
                    )
                    logger.info(
                        "Created relationship: %s -[%s]-> %s",
                        rel["from"],
                        rel["type"],
                        rel["to"],
                    )
        except Exception as e:
            logger.error(
                "Failed to create relationship %s -[%s]-> %s: %s",
                rel["from"],
                rel["type"],
                rel["to"],
                str(e),
            )
            raise

    logger.info("Initial data seeding completed successfully")
    return True
