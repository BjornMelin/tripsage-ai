# Neo4j Knowledge Graph Implementation Guide

This document provides a step-by-step implementation guide for setting up and configuring the Neo4j knowledge graph for TripSage, building on the existing documentation in `neo4j_implementation.md`.

## Prerequisites

Before implementing the Neo4j knowledge graph, ensure you have:

1. Python development environment with uv set up
2. Neo4j Desktop installed (for local development) or access to Neo4j AuraDB (for production)
3. Basic understanding of graph databases and Cypher query language
4. Required permissions to install Python packages and create database connections
5. Access to TripSage repository with proper permissions

## Implementation Workflow

### Step 1: Install Required Dependencies

First, install the necessary Python packages:

```bash
# From the TripSage project root
uv pip install neo4j
uv pip install python-dotenv  # for environment variable management
```

Add these dependencies to `requirements.txt` or `pyproject.toml`:

```toml
# Add to pyproject.toml dependencies
neo4j = "^5.15.0"
python-dotenv = "^1.0.0"
```

### Step 2: Set Up Environment Variables

Create or update your `.env` file with Neo4j connection information:

```bash
# Neo4j Connection Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
NEO4J_DATABASE=neo4j  # Default database name
```

Create a `.env.example` file without sensitive information:

```bash
# Neo4j Connection Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

### Step 3: Create Directory Structure

Create the necessary directory structure for the Neo4j implementation:

```bash
# From the TripSage project root
mkdir -p src/db/neo4j/{schemas,repositories,migrations,utils}
touch src/db/neo4j/__init__.py
touch src/db/neo4j/client.py
touch src/db/neo4j/config.py
touch src/db/neo4j/connection.py
touch src/db/neo4j/exceptions.py

# Create schema files
touch src/db/neo4j/schemas/__init__.py
touch src/db/neo4j/schemas/destination.py
touch src/db/neo4j/schemas/accommodation.py
touch src/db/neo4j/schemas/transportation.py
touch src/db/neo4j/schemas/user.py
touch src/db/neo4j/schemas/trip.py

# Create repository files
touch src/db/neo4j/repositories/__init__.py
touch src/db/neo4j/repositories/base.py
touch src/db/neo4j/repositories/destination.py
touch src/db/neo4j/repositories/accommodation.py
touch src/db/neo4j/repositories/transportation.py
touch src/db/neo4j/repositories/user.py
touch src/db/neo4j/repositories/trip.py

# Create migration files
touch src/db/neo4j/migrations/__init__.py
touch src/db/neo4j/migrations/constraints.py
touch src/db/neo4j/migrations/indexes.py
touch src/db/neo4j/migrations/initial_data.py

# Create utility files
touch src/db/neo4j/utils/__init__.py
touch src/db/neo4j/utils/validators.py
touch src/db/neo4j/utils/converters.py

# Create test files
mkdir -p tests/db/neo4j
touch tests/db/neo4j/__init__.py
touch tests/db/neo4j/test_connection.py
touch tests/db/neo4j/test_repositories.py
```

### Step 4: Implement Configuration Module

Create the configuration module for Neo4j:

```python
# src/db/neo4j/config.py
from typing import Dict, Any, Optional
import os
from src.utils.config import get_config

class Neo4jConfig:
    """Configuration for Neo4j connection."""

    def __init__(self):
        """Initialize the Neo4j configuration from environment variables."""
        # Get base configuration
        config = get_config()

        # Neo4j connection settings
        self.uri = config.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = config.get("NEO4J_USER", "neo4j")
        self.password = config.get("NEO4J_PASSWORD", "")
        self.database = config.get("NEO4J_DATABASE", "neo4j")

        # Connection pool settings
        self.max_connection_lifetime = int(config.get("NEO4J_MAX_CONNECTION_LIFETIME", 3600))
        self.max_connection_pool_size = int(config.get("NEO4J_MAX_CONNECTION_POOL_SIZE", 50))
        self.connection_acquisition_timeout = int(config.get("NEO4J_CONNECTION_ACQUISITION_TIMEOUT", 60))

        # Query settings
        self.default_query_timeout = int(config.get("NEO4J_DEFAULT_QUERY_TIMEOUT", 60))

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if not self.uri:
            raise ValueError("NEO4J_URI is required")

        if not self.user:
            raise ValueError("NEO4J_USER is required")

        if not self.password:
            raise ValueError("NEO4J_PASSWORD is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary with configuration values
        """
        return {
            "uri": self.uri,
            "user": self.user,
            "password": "****" if self.password else None,
            "database": self.database,
            "max_connection_lifetime": self.max_connection_lifetime,
            "max_connection_pool_size": self.max_connection_pool_size,
            "connection_acquisition_timeout": self.connection_acquisition_timeout,
            "default_query_timeout": self.default_query_timeout
        }

# Create a singleton instance
neo4j_config = Neo4jConfig()
```

### Step 5: Implement Connection Management

Create the connection module for Neo4j:

```python
# src/db/neo4j/connection.py
from typing import Dict, Any, Optional, List
import logging
import time
from neo4j import GraphDatabase, Driver, Session, Result, graph

from src.db.neo4j.config import neo4j_config
from src.db.neo4j.exceptions import Neo4jConnectionError, Neo4jQueryError

logger = logging.getLogger(__name__)

class Neo4jConnection:
    """Manages Neo4j database connections and query execution."""

    _instance = None
    _driver = None

    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(Neo4jConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the Neo4j connection."""
        if self._initialized:
            return

        self._initialized = True
        self._config = neo4j_config
        self._driver = None
        self._connect()

    def _connect(self) -> None:
        """Establish a connection to the Neo4j database.

        Raises:
            Neo4jConnectionError: If connection fails
        """
        try:
            # Validate configuration
            self._config.validate()

            # Create the driver
            self._driver = GraphDatabase.driver(
                self._config.uri,
                auth=(self._config.user, self._config.password),
                max_connection_lifetime=self._config.max_connection_lifetime,
                max_connection_pool_size=self._config.max_connection_pool_size,
                connection_acquisition_timeout=self._config.connection_acquisition_timeout
            )

            # Verify the connection by running a simple query
            with self._driver.session(database=self._config.database) as session:
                result = session.run("RETURN 1 AS test")
                assert result.single()["test"] == 1

            logger.info("Successfully connected to Neo4j database at %s", self._config.uri)
        except Exception as e:
            logger.error("Failed to connect to Neo4j database: %s", str(e))
            raise Neo4jConnectionError(f"Failed to connect to Neo4j database: {str(e)}")

    def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    def get_driver(self) -> Driver:
        """Get the Neo4j driver.

        Returns:
            Neo4j driver instance

        Raises:
            Neo4jConnectionError: If connection is not established
        """
        if not self._driver:
            self._connect()
        return self._driver

    def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None,
                 database: Optional[str] = None, timeout: Optional[int] = None) -> List[Dict[str, Any]]:
        """Run a Cypher query and return the results.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (defaults to configuration)
            timeout: Query timeout in seconds (defaults to configuration)

        Returns:
            List of dictionaries with query results

        Raises:
            Neo4jQueryError: If query execution fails
        """
        if not self._driver:
            self._connect()

        # Use default values from configuration if not provided
        if database is None:
            database = self._config.database

        if timeout is None:
            timeout = self._config.default_query_timeout

        parameters = parameters or {}
        start_time = time.time()

        try:
            with self._driver.session(database=database) as session:
                result = session.run(query, parameters, timeout=timeout)
                records = [record.data() for record in result]

                execution_time = time.time() - start_time
                logger.debug("Query executed in %.2f seconds: %s", execution_time, query)

                return records
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Query failed after %.2f seconds: %s - %s", execution_time, query, str(e))
            raise Neo4jQueryError(f"Query execution failed: {str(e)}")

    def run_transaction(self, statements: List[Dict[str, Any]], database: Optional[str] = None,
                       timeout: Optional[int] = None) -> List[List[Dict[str, Any]]]:
        """Run multiple statements in a transaction.

        Args:
            statements: List of statement dictionaries, each containing 'query' and 'parameters'
            database: Database name (defaults to configuration)
            timeout: Transaction timeout in seconds (defaults to configuration)

        Returns:
            List of results for each statement

        Raises:
            Neo4jQueryError: If transaction execution fails
        """
        if not self._driver:
            self._connect()

        # Use default values from configuration if not provided
        if database is None:
            database = self._config.database

        if timeout is None:
            timeout = self._config.default_query_timeout

        start_time = time.time()

        try:
            with self._driver.session(database=database) as session:
                def _run_transaction(tx):
                    results = []
                    for statement in statements:
                        query = statement["query"]
                        parameters = statement.get("parameters", {})
                        result = tx.run(query, parameters)
                        results.append([record.data() for record in result])
                    return results

                results = session.execute_write(_run_transaction)

                execution_time = time.time() - start_time
                logger.debug("Transaction executed in %.2f seconds with %d statements",
                            execution_time, len(statements))

                return results
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Transaction failed after %.2f seconds: %s", execution_time, str(e))
            raise Neo4jQueryError(f"Transaction execution failed: {str(e)}")

    def ensure_indexes_and_constraints(self) -> None:
        """Ensure that all required indexes and constraints are created."""
        from src.db.neo4j.migrations.constraints import create_constraints
        from src.db.neo4j.migrations.indexes import create_indexes

        # Execute constraints first
        create_constraints(self)

        # Then create indexes
        create_indexes(self)

        logger.info("Neo4j indexes and constraints created successfully")

    def is_connected(self) -> bool:
        """Check if the connection to Neo4j is active.

        Returns:
            True if connected, False otherwise
        """
        if not self._driver:
            return False

        try:
            with self._driver.session(database=self._config.database) as session:
                result = session.run("RETURN 1 AS test")
                return result.single()["test"] == 1
        except Exception:
            return False
```

### Step 6: Implement Custom Exceptions

Create custom exceptions for Neo4j:

```python
# src/db/neo4j/exceptions.py
class Neo4jError(Exception):
    """Base class for Neo4j-related exceptions."""
    pass

class Neo4jConnectionError(Neo4jError):
    """Raised when connection to Neo4j fails."""
    pass

class Neo4jQueryError(Neo4jError):
    """Raised when a Cypher query fails."""
    pass

class Neo4jValidationError(Neo4jError):
    """Raised when data validation fails."""
    pass

class Neo4jSchemaError(Neo4jError):
    """Raised when there's a schema-related error."""
    pass

class Neo4jDataError(Neo4jError):
    """Raised when there's a data-related error."""
    pass

class Neo4jTransactionError(Neo4jError):
    """Raised when a transaction fails."""
    pass
```

### Step 7: Implement Entity Schemas

Create entity schemas for the knowledge graph:

#### Destination Schema

```python
# src/db/neo4j/schemas/destination.py
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime

class Coordinate(BaseModel):
    """Geographical coordinates."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class Weather(BaseModel):
    """Weather information."""
    climate: str
    best_time_to_visit: List[str]
    average_temperature: Dict[str, float]  # Month -> temperature

class Destination(BaseModel):
    """Destination entity schema."""
    name: str = Field(..., min_length=1)
    country: str
    region: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    type: str = Field(..., regex="^(city|country|landmark|region|national_park)$")
    coordinates: Optional[Coordinate] = None
    popular_for: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    weather: Optional[Weather] = None
    safety_rating: Optional[float] = Field(None, ge=1, le=5)
    cost_level: Optional[int] = Field(None, ge=1, le=5)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("name")
    def name_must_be_valid(cls, v):
        """Validate destination name."""
        if not v.strip():
            raise ValueError("Destination name cannot be empty")
        return v.strip()

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties.

        Returns:
            Properties dictionary for Neo4j node
        """
        properties = self.dict(exclude={"coordinates", "weather", "popular_for",
                                         "languages", "created_at", "updated_at"})

        # Add flattened coordinates
        if self.coordinates:
            properties["latitude"] = self.coordinates.latitude
            properties["longitude"] = self.coordinates.longitude

        # Handle dates (Neo4j expects ISO format strings)
        properties["created_at"] = self.created_at.isoformat()
        properties["updated_at"] = self.updated_at.isoformat()

        # Arrays are handled directly by Neo4j driver
        if self.popular_for:
            properties["popular_for"] = self.popular_for

        if self.languages:
            properties["languages"] = self.languages

        # Nested objects need to be serialized
        if self.weather:
            properties["weather_climate"] = self.weather.climate
            properties["weather_best_time"] = self.weather.best_time_to_visit
            properties["weather_avg_temp"] = str(self.weather.average_temperature)

        return properties

    @classmethod
    def from_neo4j_node(cls, node: Dict[str, Any]) -> "Destination":
        """Create Destination from Neo4j node.

        Args:
            node: Node data from Neo4j

        Returns:
            Destination instance
        """
        properties = dict(node)

        # Handle coordinates
        coordinates = None
        if "latitude" in properties and "longitude" in properties:
            coordinates = Coordinate(
                latitude=properties.pop("latitude"),
                longitude=properties.pop("longitude")
            )

        # Handle weather
        weather = None
        if "weather_climate" in properties and "weather_best_time" in properties:
            import json
            weather = Weather(
                climate=properties.pop("weather_climate"),
                best_time_to_visit=properties.pop("weather_best_time"),
                average_temperature=json.loads(properties.pop("weather_avg_temp"))
            )

        # Handle dates
        if "created_at" in properties and isinstance(properties["created_at"], str):
            properties["created_at"] = datetime.fromisoformat(properties["created_at"])

        if "updated_at" in properties and isinstance(properties["updated_at"], str):
            properties["updated_at"] = datetime.fromisoformat(properties["updated_at"])

        # Remove any Neo4j-specific properties
        properties.pop("elementId", None)

        # Add back complex objects
        properties["coordinates"] = coordinates
        properties["weather"] = weather

        return cls(**properties)
```

### Step 8: Implement Base Repository

Create a base repository for Neo4j operations:

```python
# src/db/neo4j/repositories/base.py
from typing import Dict, Any, List, Optional, TypeVar, Generic, Type
import logging
from datetime import datetime
from pydantic import BaseModel

from src.db.neo4j.connection import Neo4jConnection
from src.db.neo4j.exceptions import Neo4jQueryError, Neo4jValidationError

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

class BaseNeo4jRepository(Generic[T]):
    """Base repository for Neo4j entities."""

    def __init__(self, entity_class: Type[T], label: str):
        """Initialize the repository.

        Args:
            entity_class: The Pydantic model class for entities
            label: The Neo4j node label
        """
        self.entity_class = entity_class
        self.label = label
        self.connection = Neo4jConnection()

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: The entity to create

        Returns:
            The created entity with any generated fields

        Raises:
            Neo4jValidationError: If entity validation fails
            Neo4jQueryError: If creation fails
        """
        try:
            # Ensure entity has updated timestamps
            if hasattr(entity, "created_at"):
                entity.created_at = datetime.utcnow()

            if hasattr(entity, "updated_at"):
                entity.updated_at = datetime.utcnow()

            # Convert to Neo4j properties
            properties = entity.to_neo4j_properties()

            # Build Cypher query
            query = f"""
            CREATE (n:{self.label} $properties)
            RETURN n
            """

            # Execute query
            result = self.connection.run_query(
                query=query,
                parameters={"properties": properties}
            )

            if not result or len(result) == 0:
                raise Neo4jQueryError(f"Failed to create {self.label}")

            # Return the created entity
            return self.entity_class.from_neo4j_node(result[0]["n"])

        except Exception as e:
            logger.error("Failed to create %s: %s", self.label, str(e))
            raise

    async def get_by_id(self, id_value: str, id_field: str = "name") -> Optional[T]:
        """Get an entity by ID.

        Args:
            id_value: The ID value to search for
            id_field: The field to use as ID (default: "name")

        Returns:
            The entity if found, None otherwise

        Raises:
            Neo4jQueryError: If query fails
        """
        try:
            # Build Cypher query
            query = f"""
            MATCH (n:{self.label})
            WHERE n.{id_field} = $id_value
            RETURN n
            """

            # Execute query
            result = self.connection.run_query(
                query=query,
                parameters={"id_value": id_value}
            )

            if not result or len(result) == 0:
                return None

            # Return the entity
            return self.entity_class.from_neo4j_node(result[0]["n"])

        except Exception as e:
            logger.error("Failed to get %s by ID: %s", self.label, str(e))
            raise

    async def get_all(self, limit: int = 100, skip: int = 0) -> List[T]:
        """Get all entities with pagination.

        Args:
            limit: Maximum number of entities to return
            skip: Number of entities to skip

        Returns:
            List of entities

        Raises:
            Neo4jQueryError: If query fails
        """
        try:
            # Build Cypher query
            query = f"""
            MATCH (n:{self.label})
            RETURN n
            SKIP $skip
            LIMIT $limit
            """

            # Execute query
            result = self.connection.run_query(
                query=query,
                parameters={"skip": skip, "limit": limit}
            )

            # Convert to entities
            entities = []
            for record in result:
                entity = self.entity_class.from_neo4j_node(record["n"])
                entities.append(entity)

            return entities

        except Exception as e:
            logger.error("Failed to get all %s: %s", self.label, str(e))
            raise

    async def update(self, id_value: str, entity: T, id_field: str = "name") -> T:
        """Update an entity.

        Args:
            id_value: The ID value to update
            entity: The updated entity
            id_field: The field to use as ID (default: "name")

        Returns:
            The updated entity

        Raises:
            Neo4jValidationError: If entity validation fails
            Neo4jQueryError: If update fails
        """
        try:
            # Ensure entity has updated timestamp
            if hasattr(entity, "updated_at"):
                entity.updated_at = datetime.utcnow()

            # Convert to Neo4j properties
            properties = entity.to_neo4j_properties()

            # Build Cypher query
            query = f"""
            MATCH (n:{self.label})
            WHERE n.{id_field} = $id_value
            SET n = $properties
            RETURN n
            """

            # Execute query
            result = self.connection.run_query(
                query=query,
                parameters={"id_value": id_value, "properties": properties}
            )

            if not result or len(result) == 0:
                raise Neo4jQueryError(f"Failed to update {self.label}: Not found")

            # Return the updated entity
            return self.entity_class.from_neo4j_node(result[0]["n"])

        except Exception as e:
            logger.error("Failed to update %s: %s", self.label, str(e))
            raise

    async def delete(self, id_value: str, id_field: str = "name") -> bool:
        """Delete an entity.

        Args:
            id_value: The ID value to delete
            id_field: The field to use as ID (default: "name")

        Returns:
            True if deleted, False if not found

        Raises:
            Neo4jQueryError: If deletion fails
        """
        try:
            # Build Cypher query
            query = f"""
            MATCH (n:{self.label})
            WHERE n.{id_field} = $id_value
            DETACH DELETE n
            RETURN count(*) as deleted
            """

            # Execute query
            result = self.connection.run_query(
                query=query,
                parameters={"id_value": id_value}
            )

            # Check if anything was deleted
            return result[0]["deleted"] > 0

        except Exception as e:
            logger.error("Failed to delete %s: %s", self.label, str(e))
            raise

    async def search(self, properties: Dict[str, Any], limit: int = 100) -> List[T]:
        """Search for entities by properties.

        Args:
            properties: Properties to search for
            limit: Maximum number of entities to return

        Returns:
            List of matching entities

        Raises:
            Neo4jQueryError: If search fails
        """
        try:
            # Build Cypher query with property conditions
            conditions = []
            parameters = {}

            for key, value in properties.items():
                if value is not None:
                    conditions.append(f"n.{key} = ${key}")
                    parameters[key] = value

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            query = f"""
            MATCH (n:{self.label})
            WHERE {where_clause}
            RETURN n
            LIMIT $limit
            """

            # Add limit to parameters
            parameters["limit"] = limit

            # Execute query
            result = self.connection.run_query(
                query=query,
                parameters=parameters
            )

            # Convert to entities
            entities = []
            for record in result:
                entity = self.entity_class.from_neo4j_node(record["n"])
                entities.append(entity)

            return entities

        except Exception as e:
            logger.error("Failed to search %s: %s", self.label, str(e))
            raise
```

### Step 9: Implement Destination Repository

Create a repository implementation for destinations:

```python
# src/db/neo4j/repositories/destination.py
from typing import Dict, Any, List, Optional
import logging

from src.db.neo4j.repositories.base import BaseNeo4jRepository
from src.db.neo4j.schemas.destination import Destination

logger = logging.getLogger(__name__)

class DestinationRepository(BaseNeo4jRepository[Destination]):
    """Repository for Destination entities."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Destination, "Destination")

    async def find_by_country(self, country: str) -> List[Destination]:
        """Find destinations by country.

        Args:
            country: The country to search for

        Returns:
            List of destinations in the country
        """
        try:
            # Build Cypher query
            query = """
            MATCH (d:Destination)
            WHERE d.country = $country
            RETURN d
            """

            # Execute query
            result = self.connection.run_query(
                query=query,
                parameters={"country": country}
            )

            # Convert to entities
            destinations = []
            for record in result:
                destination = Destination.from_neo4j_node(record["d"])
                destinations.append(destination)

            return destinations

        except Exception as e:
            logger.error("Failed to find destinations by country: %s", str(e))
            raise

    async def find_nearby(self, latitude: float, longitude: float,
                         distance_km: float = 50) -> List[Destination]:
        """Find destinations near a location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            distance_km: Maximum distance in kilometers

        Returns:
            List of nearby destinations
        """
        try:
            # Build Cypher query
            # This uses the Haversine formula to calculate distance
            query = """
            MATCH (d:Destination)
            WHERE d.latitude IS NOT NULL AND d.longitude IS NOT NULL
            WITH d,
                 6371 * acos(
                     cos(radians($latitude)) *
                     cos(radians(d.latitude)) *
                     cos(radians(d.longitude) - radians($longitude)) +
                     sin(radians($latitude)) *
                     sin(radians(d.latitude))
                 ) AS distance
            WHERE distance <= $distance_km
            RETURN d, distance
            ORDER BY distance
            """

            # Execute query
            result = self.connection.run_query(
                query=query,
                parameters={
                    "latitude": latitude,
                    "longitude": longitude,
                    "distance_km": distance_km
                }
            )

            # Convert to entities
            destinations = []
            for record in result:
                destination = Destination.from_neo4j_node(record["d"])
                destinations.append(destination)

            return destinations

        except Exception as e:
            logger.error("Failed to find nearby destinations: %s", str(e))
            raise

    async def create_relationship(self, from_destination: str,
                                 relationship_type: str,
                                 to_destination: str,
                                 properties: Optional[Dict[str, Any]] = None) -> bool:
        """Create a relationship between destinations.

        Args:
            from_destination: Name of the source destination
            relationship_type: Type of relationship (e.g., NEAR, CONNECTS_TO)
            to_destination: Name of the target destination
            properties: Optional relationship properties

        Returns:
            True if relationship created successfully
        """
        try:
            # Build Cypher query
            query = """
            MATCH (a:Destination), (b:Destination)
            WHERE a.name = $from_name AND b.name = $to_name
            CREATE (a)-[r:`{}`]->(b)
            SET r = $properties
            RETURN r
            """.format(relationship_type)

            # Execute query
            result = self.connection.run_query(
                query=query,
                parameters={
                    "from_name": from_destination,
                    "to_name": to_destination,
                    "properties": properties or {}
                }
            )

            return len(result) > 0

        except Exception as e:
            logger.error("Failed to create relationship: %s", str(e))
            raise
```

### Step 10: Implement Migrations for Constraints and Indexes

Create migrations for Neo4j constraints and indexes:

```python
# src/db/neo4j/migrations/constraints.py
def create_constraints(connection):
    """Create Neo4j constraints.

    Args:
        connection: Neo4j connection instance
    """
    # Define constraints
    constraints = [
        # Uniqueness constraints
        """
        CREATE CONSTRAINT destination_name_unique IF NOT EXISTS
        FOR (d:Destination)
        REQUIRE d.name IS UNIQUE
        """,

        """
        CREATE CONSTRAINT user_email_unique IF NOT EXISTS
        FOR (u:User)
        REQUIRE u.email IS UNIQUE
        """,

        """
        CREATE CONSTRAINT trip_id_unique IF NOT EXISTS
        FOR (t:Trip)
        REQUIRE t.id IS UNIQUE
        """,

        # Existence constraints
        """
        CREATE CONSTRAINT destination_country_exists IF NOT EXISTS
        FOR (d:Destination)
        REQUIRE d.country IS NOT NULL
        """,

        """
        CREATE CONSTRAINT user_name_exists IF NOT EXISTS
        FOR (u:User)
        REQUIRE u.name IS NOT NULL
        """,
    ]

    # Create each constraint
    for constraint in constraints:
        connection.run_query(constraint)

    return True
```

```python
# src/db/neo4j/migrations/indexes.py
def create_indexes(connection):
    """Create Neo4j indexes.

    Args:
        connection: Neo4j connection instance
    """
    # Define indexes
    indexes = [
        # B-tree indexes for exact lookups
        """
        CREATE INDEX destination_country_index IF NOT EXISTS
        FOR (d:Destination)
        ON (d.country)
        """,

        """
        CREATE INDEX destination_type_index IF NOT EXISTS
        FOR (d:Destination)
        ON (d.type)
        """,

        """
        CREATE INDEX trip_user_id_index IF NOT EXISTS
        FOR (t:Trip)
        ON (t.user_id)
        """,

        # Text indexes for text search
        """
        CREATE TEXT INDEX destination_description_index IF NOT EXISTS
        FOR (d:Destination)
        ON (d.description)
        """,

        # Composite indexes
        """
        CREATE INDEX destination_location_index IF NOT EXISTS
        FOR (d:Destination)
        ON (d.latitude, d.longitude)
        """
    ]

    # Create each index
    for index in indexes:
        connection.run_query(index)

    return True
```

### Step 11: Implement Initial Data Seeder

Create a data seeder for initial travel data:

```python
# src/db/neo4j/migrations/initial_data.py
from typing import List, Dict, Any
from datetime import datetime

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
            "description": "The City of Light, known for the Eiffel Tower and Louvre Museum.",
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
            "cost_level": 4
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
            "cost_level": 4
        },
        {
            "name": "New York City",
            "country": "United States",
            "region": "New York",
            "city": "New York",
            "description": "Major commercial and cultural center known for iconic landmarks.",
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
            "cost_level": 5
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
            "cost_level": 3
        }
    ]

def seed_initial_data(connection) -> bool:
    """Seed initial data into Neo4j.

    Args:
        connection: Neo4j connection instance

    Returns:
        True if successful
    """
    # Create destinations
    destinations = get_initial_destinations()
    for destination in destinations:
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

    # Create relationships between destinations (e.g., nearby, connected_to)
    relationships = [
        {
            "from": "Paris",
            "to": "London",
            "type": "CONNECTED_TO",
            "properties": {"distance_km": 344, "transport": ["train", "flight"]}
        },
        {
            "from": "New York City",
            "to": "Washington D.C.",
            "type": "CONNECTED_TO",
            "properties": {"distance_km": 361, "transport": ["train", "flight", "bus"]}
        }
    ]

    for rel in relationships:
        # Check if destinations exist
        query = """
        MATCH (a:Destination {name: $from}), (b:Destination {name: $to})
        RETURN count(a) > 0 AND count(b) > 0 AS both_exist
        """
        result = connection.run_query(query, {"from": rel["from"], "to": rel["to"]})

        if result and result[0]["both_exist"]:
            # Check if relationship already exists
            check_query = """
            MATCH (a:Destination {name: $from})-[r:`{}`]->(b:Destination {name: $to})
            RETURN count(r) > 0 AS exists
            """.format(rel["type"])
            check_result = connection.run_query(check_query, {"from": rel["from"], "to": rel["to"]})

            if not check_result[0]["exists"]:
                # Create relationship
                create_query = """
                MATCH (a:Destination {name: $from}), (b:Destination {name: $to})
                CREATE (a)-[r:`{}`]->(b)
                SET r = $properties
                RETURN r
                """.format(rel["type"])
                connection.run_query(
                    create_query,
                    {"from": rel["from"], "to": rel["to"], "properties": rel["properties"]}
                )

    return True
```

### Step 12: Implement Client Interface

Create a client interface for Neo4j:

```python
# src/db/neo4j/client.py
from typing import Dict, Any, List, Optional, Type, TypeVar
import logging
from datetime import datetime

from src.db.neo4j.connection import Neo4jConnection
from src.db.neo4j.exceptions import Neo4jConnectionError, Neo4jQueryError
from src.db.neo4j.repositories.destination import DestinationRepository
from src.db.neo4j.schemas.destination import Destination

from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class Neo4jClient:
    """Client interface for Neo4j operations."""

    def __init__(self):
        """Initialize the Neo4j client."""
        self.connection = Neo4jConnection()
        self.destination_repo = DestinationRepository()

    async def initialize(self) -> None:
        """Initialize the Neo4j database."""
        # Ensure connection
        if not self.connection.is_connected():
            raise Neo4jConnectionError("Cannot initialize: Not connected to Neo4j")

        # Create constraints and indexes
        self.connection.ensure_indexes_and_constraints()

        # Seed initial data
        from src.db.neo4j.migrations.initial_data import seed_initial_data
        seed_initial_data(self.connection)

        logger.info("Neo4j database initialized successfully")

    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            Query results
        """
        return self.connection.run_query(query, parameters)

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

    async def get_destination(self, name: str) -> Optional[Destination]:
        """Get a destination by name.

        Args:
            name: Destination name

        Returns:
            Destination if found, None otherwise
        """
        return await self.destination_repo.get_by_id(name)

    async def find_destinations_by_country(self, country: str) -> List[Destination]:
        """Find destinations by country.

        Args:
            country: Country name

        Returns:
            List of destinations
        """
        return await self.destination_repo.find_by_country(country)

    async def find_nearby_destinations(self, latitude: float, longitude: float,
                                     distance_km: float = 50) -> List[Destination]:
        """Find destinations near a location.

        Args:
            latitude: Latitude
            longitude: Longitude
            distance_km: Maximum distance in kilometers

        Returns:
            List of nearby destinations
        """
        return await self.destination_repo.find_nearby(latitude, longitude, distance_km)

    async def create_destination_relationship(self, from_destination: str,
                                           relationship_type: str,
                                           to_destination: str,
                                           properties: Optional[Dict[str, Any]] = None) -> bool:
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

    async def close(self) -> None:
        """Close the Neo4j connection."""
        self.connection.close()
        logger.info("Neo4j client closed")

# Create a singleton instance
neo4j_client = Neo4jClient()
```

### Step 13: Implement Tests

Create tests for the Neo4j implementation:

```python
# tests/db/neo4j/test_connection.py
import pytest
import os
from unittest.mock import patch, MagicMock

from src.db.neo4j.connection import Neo4jConnection
from src.db.neo4j.exceptions import Neo4jConnectionError, Neo4jQueryError

@pytest.fixture
def mock_driver():
    """Mock Neo4j driver."""
    mock = MagicMock()

    # Mock session context manager
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=None)

    # Mock run method
    mock_result = MagicMock()
    mock_record = MagicMock()
    mock_record.data.return_value = {"test": 1}
    mock_result.single.return_value = {"test": 1}
    mock_result.__iter__ = MagicMock(return_value=iter([mock_record]))
    mock_session.run.return_value = mock_result

    # Set up driver methods
    mock.session.return_value = mock_session

    return mock

@pytest.fixture
def neo4j_connection(mock_driver):
    """Neo4j connection with mocked driver."""
    with patch("neo4j.GraphDatabase.driver", return_value=mock_driver):
        connection = Neo4jConnection()
        yield connection
        connection.close()

def test_connection_initialization(neo4j_connection):
    """Test connection initialization."""
    assert neo4j_connection._driver is not None
    assert neo4j_connection.is_connected()

def test_run_query(neo4j_connection, mock_driver):
    """Test running a query."""
    query = "MATCH (n) RETURN n"
    params = {"param": "value"}

    result = neo4j_connection.run_query(query, params)

    # Check that session was created with correct database
    mock_driver.session.assert_called_once()

    # Check that run was called with correct query and parameters
    mock_session = mock_driver.session.return_value.__enter__.return_value
    mock_session.run.assert_called_once_with(query, params, timeout=60)

    # Check that result was processed correctly
    assert len(result) == 1
    assert result[0] == {"test": 1}

def test_run_transaction(neo4j_connection, mock_driver):
    """Test running a transaction."""
    statements = [
        {"query": "MATCH (n) RETURN n", "parameters": {"param1": "value1"}},
        {"query": "CREATE (n) RETURN n", "parameters": {"param2": "value2"}}
    ]

    # Mock session execute_write method
    mock_session = mock_driver.session.return_value.__enter__.return_value
    mock_session.execute_write.return_value = [[{"test": 1}], [{"test": 2}]]

    result = neo4j_connection.run_transaction(statements)

    # Check that session was created with correct database
    mock_driver.session.assert_called_once()

    # Check that execute_write was called
    mock_session.execute_write.assert_called_once()

    # Check that result was processed correctly
    assert len(result) == 2
    assert result[0] == [{"test": 1}]
    assert result[1] == [{"test": 2}]

def test_connection_failure():
    """Test connection failure."""
    with patch("neo4j.GraphDatabase.driver", side_effect=Exception("Connection failed")):
        with pytest.raises(Neo4jConnectionError):
            Neo4jConnection()

def test_query_failure(neo4j_connection, mock_driver):
    """Test query failure."""
    # Mock session run method to raise exception
    mock_session = mock_driver.session.return_value.__enter__.return_value
    mock_session.run.side_effect = Exception("Query failed")

    with pytest.raises(Neo4jQueryError):
        neo4j_connection.run_query("MATCH (n) RETURN n")
```

```python
# tests/db/neo4j/test_repositories.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.db.neo4j.schemas.destination import Destination, Coordinate, Weather
from src.db.neo4j.repositories.destination import DestinationRepository
from src.db.neo4j.exceptions import Neo4jQueryError

@pytest.fixture
def destination_data():
    """Sample destination data."""
    return {
        "name": "Test City",
        "country": "Test Country",
        "region": "Test Region",
        "city": "Test City",
        "description": "A test city for unit tests",
        "type": "city",
        "coordinates": Coordinate(latitude=10.0, longitude=20.0),
        "popular_for": ["testing", "unit tests"],
        "languages": ["English"],
        "currency": "USD",
        "timezone": "UTC",
        "weather": Weather(
            climate="Temperate",
            best_time_to_visit=["Spring", "Fall"],
            average_temperature={"January": 5, "July": 25}
        ),
        "safety_rating": 4.5,
        "cost_level": 3
    }

@pytest.fixture
def destination_model(destination_data):
    """Sample destination model."""
    return Destination(**destination_data)

@pytest.fixture
def mock_connection():
    """Mock Neo4j connection."""
    mock = MagicMock()
    return mock

@pytest.fixture
def destination_repository(mock_connection):
    """Destination repository with mocked connection."""
    repo = DestinationRepository()
    repo.connection = mock_connection
    return repo

@pytest.mark.asyncio
async def test_create_destination(destination_repository, destination_model, mock_connection):
    """Test creating a destination."""
    # Mock run_query to return a result with a node
    mock_connection.run_query.return_value = [{"n": destination_model.to_neo4j_properties()}]

    # Create destination
    result = await destination_repository.create(destination_model)

    # Verify query was executed
    mock_connection.run_query.assert_called_once()

    # Verify result
    assert isinstance(result, Destination)
    assert result.name == destination_model.name
    assert result.country == destination_model.country

@pytest.mark.asyncio
async def test_get_destination_by_id(destination_repository, destination_model, mock_connection):
    """Test getting a destination by ID."""
    # Mock run_query to return a result with a node
    mock_connection.run_query.return_value = [{"n": destination_model.to_neo4j_properties()}]

    # Get destination
    result = await destination_repository.get_by_id("Test City")

    # Verify query was executed
    mock_connection.run_query.assert_called_once()

    # Verify result
    assert isinstance(result, Destination)
    assert result.name == destination_model.name
    assert result.country == destination_model.country

@pytest.mark.asyncio
async def test_get_destination_by_id_not_found(destination_repository, mock_connection):
    """Test getting a non-existent destination."""
    # Mock run_query to return an empty result
    mock_connection.run_query.return_value = []

    # Get destination
    result = await destination_repository.get_by_id("Nonexistent City")

    # Verify query was executed
    mock_connection.run_query.assert_called_once()

    # Verify result
    assert result is None

@pytest.mark.asyncio
async def test_update_destination(destination_repository, destination_model, mock_connection):
    """Test updating a destination."""
    # Mock run_query to return a result with a node
    mock_connection.run_query.return_value = [{"n": destination_model.to_neo4j_properties()}]

    # Update destination
    updated_model = destination_model.copy()
    updated_model.description = "Updated description"
    result = await destination_repository.update("Test City", updated_model)

    # Verify query was executed
    mock_connection.run_query.assert_called_once()

    # Verify result
    assert isinstance(result, Destination)
    assert result.name == updated_model.name
    assert result.description == updated_model.description

@pytest.mark.asyncio
async def test_delete_destination(destination_repository, mock_connection):
    """Test deleting a destination."""
    # Mock run_query to return a result with deleted count
    mock_connection.run_query.return_value = [{"deleted": 1}]

    # Delete destination
    result = await destination_repository.delete("Test City")

    # Verify query was executed
    mock_connection.run_query.assert_called_once()

    # Verify result
    assert result is True

@pytest.mark.asyncio
async def test_find_by_country(destination_repository, destination_model, mock_connection):
    """Test finding destinations by country."""
    # Mock run_query to return a result with nodes
    mock_connection.run_query.return_value = [{"d": destination_model.to_neo4j_properties()}]

    # Find destinations
    result = await destination_repository.find_by_country("Test Country")

    # Verify query was executed
    mock_connection.run_query.assert_called_once()

    # Verify result
    assert len(result) == 1
    assert isinstance(result[0], Destination)
    assert result[0].name == destination_model.name
    assert result[0].country == destination_model.country

@pytest.mark.asyncio
async def test_find_nearby(destination_repository, destination_model, mock_connection):
    """Test finding nearby destinations."""
    # Mock run_query to return a result with nodes
    mock_connection.run_query.return_value = [
        {"d": destination_model.to_neo4j_properties(), "distance": 10.5}
    ]

    # Find nearby destinations
    result = await destination_repository.find_nearby(10.0, 20.0, 50)

    # Verify query was executed
    mock_connection.run_query.assert_called_once()

    # Verify result
    assert len(result) == 1
    assert isinstance(result[0], Destination)
    assert result[0].name == destination_model.name
```

### Step 14: Implement Memory MCP Integration

Now that we have the Neo4j infrastructure set up, we can implement the Memory MCP integration:

```python
# src/mcp/memory/client.py
from typing import Dict, Any, List, Optional
import logging
import asyncio

from src.db.neo4j.client import neo4j_client
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class MemoryClient:
    """Client for Memory MCP Server operations."""

    def __init__(self):
        """Initialize the Memory MCP client."""
        self.neo4j = neo4j_client
        logger.info("Initialized Memory MCP Client")

    async def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple new entities in the knowledge graph.

        Args:
            entities: List of entity objects with name, entityType, and observations

        Returns:
            Result with created entity information
        """
        try:
            created = []

            for entity in entities:
                # Convert MCP entity format to Neo4j entity format
                entity_type = entity.get("entityType")

                if entity_type == "Destination":
                    # Create destination
                    destination_data = {
                        "name": entity.get("name"),
                        "country": "Unknown",  # Default value
                        "type": "destination",
                        "description": "\n".join(entity.get("observations", []))
                    }

                    # Create in Neo4j
                    created_entity = await self.neo4j.add_destination(destination_data)
                    created.append({
                        "name": created_entity.name,
                        "type": entity_type,
                        "id": created_entity.name
                    })

                # Handle other entity types as needed

            return {
                "success": True,
                "created": created,
                "count": len(created)
            }

        except Exception as e:
            logger.error("Error creating entities: %s", str(e))
            return {
                "success": False,
                "error": f"Failed to create entities: {str(e)}"
            }

    async def create_relations(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple new relations between entities in the knowledge graph.

        Args:
            relations: List of relation objects with from, to, and relationType

        Returns:
            Result with created relation information
        """
        try:
            created = []

            for relation in relations:
                from_entity = relation.get("from")
                to_entity = relation.get("to")
                relation_type = relation.get("relationType")

                # Create relationship in Neo4j
                success = await self.neo4j.create_destination_relationship(
                    from_entity, relation_type, to_entity
                )

                if success:
                    created.append({
                        "from": from_entity,
                        "to": to_entity,
                        "type": relation_type
                    })

            return {
                "success": True,
                "created": created,
                "count": len(created)
            }

        except Exception as e:
            logger.error("Error creating relations: %s", str(e))
            return {
                "success": False,
                "error": f"Failed to create relations: {str(e)}"
            }

    async def add_observations(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add new observations to existing entities in the knowledge graph.

        Args:
            observations: List of observation objects with entityName and contents

        Returns:
            Result with added observation information
        """
        try:
            updated = []

            for observation in observations:
                entity_name = observation.get("entityName")
                contents = observation.get("contents", [])

                # Get existing entity
                entity = await self.neo4j.get_destination(entity_name)

                if entity:
                    # Update description with new observations
                    new_description = entity.description or ""
                    for content in contents:
                        new_description += f"\n{content}"

                    # Update entity
                    entity_data = entity.dict()
                    entity_data["description"] = new_description.strip()

                    # Save updated entity
                    await self.neo4j.add_destination(entity_data)

                    updated.append({
                        "name": entity_name,
                        "observations_added": len(contents)
                    })

            return {
                "success": True,
                "updated": updated,
                "count": len(updated)
            }

        except Exception as e:
            logger.error("Error adding observations: %s", str(e))
            return {
                "success": False,
                "error": f"Failed to add observations: {str(e)}"
            }

    async def search_nodes(self, query: str) -> Dict[str, Any]:
        """Search for nodes in the knowledge graph based on a query.

        Args:
            query: The search query to match against entity properties

        Returns:
            Matching nodes
        """
        try:
            # Create Cypher query for text search
            cypher_query = """
            CALL db.index.fulltext.queryNodes("destination_description_index", $query)
            YIELD node, score
            RETURN node, score
            ORDER BY score DESC
            LIMIT 10
            """

            # Execute query
            results = await self.neo4j.execute_query(cypher_query, {"query": query})

            # Format results
            nodes = []
            for result in results:
                node_data = result.get("node", {})

                # Convert to Memory MCP format
                nodes.append({
                    "name": node_data.get("name"),
                    "type": "Destination",
                    "observations": [
                        node_data.get("description", "")
                    ],
                    "score": result.get("score", 0.0)
                })

            return {
                "query": query,
                "results": nodes,
                "count": len(nodes)
            }

        except Exception as e:
            logger.error("Error searching nodes: %s", str(e))
            return {
                "query": query,
                "results": [],
                "error": f"Search failed: {str(e)}"
            }

    async def read_graph(self) -> Dict[str, Any]:
        """Read the entire knowledge graph.

        Returns:
            Graph data with entities and relations
        """
        try:
            # Get all destinations
            destinations = await self.neo4j.destination_repo.get_all(limit=100)

            # Get all relationships
            cypher_query = """
            MATCH (a:Destination)-[r]->(b:Destination)
            RETURN a.name AS from, type(r) AS type, b.name AS to, properties(r) AS properties
            LIMIT 100
            """
            relationships = await self.neo4j.execute_query(cypher_query)

            # Format results
            entities = []
            for destination in destinations:
                entities.append({
                    "name": destination.name,
                    "type": "Destination",
                    "observations": [
                        f"Located in {destination.country}",
                        destination.description or ""
                    ]
                })

            relations = []
            for rel in relationships:
                relations.append({
                    "from": rel.get("from"),
                    "type": rel.get("type"),
                    "to": rel.get("to")
                })

            return {
                "entities": entities,
                "relations": relations,
                "entity_count": len(entities),
                "relation_count": len(relations)
            }

        except Exception as e:
            logger.error("Error reading graph: %s", str(e))
            return {
                "entities": [],
                "relations": [],
                "error": f"Failed to read graph: {str(e)}"
            }
```

### Step 15: Create Initialization Script

Create a script to initialize the Neo4j database:

```python
# scripts/initialize_neo4j.py
import asyncio
import logging
from src.db.neo4j.client import neo4j_client
from src.utils.logging import setup_logging

async def initialize_neo4j():
    """Initialize Neo4j database."""
    try:
        # Set up logging
        setup_logging()

        # Initialize Neo4j
        await neo4j_client.initialize()

        print("Neo4j database initialized successfully")
    except Exception as e:
        logging.error("Failed to initialize Neo4j: %s", str(e))
        print(f"Error: {str(e)}")
    finally:
        # Close connection
        await neo4j_client.close()

if __name__ == "__main__":
    asyncio.run(initialize_neo4j())
```

### Step 16: Update Docker Configuration

Add Neo4j to the Docker Compose configuration:

```yaml
# docker-compose.yml
version: "3.8"

services:
  # Existing services...

  neo4j:
    image: neo4j:5-enterprise
    container_name: tripsage-neo4j
    ports:
      - "7474:7474" # HTTP
      - "7687:7687" # Bolt
    environment:
      - NEO4J_AUTH=neo4j/your_password
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
    volumes:
      - ./data/neo4j/data:/data
      - ./data/neo4j/logs:/logs
    networks:
      - tripsage-network
```

## Testing and Validation

### Running the Initialization Script

```bash
# From the TripSage project root
python scripts/initialize_neo4j.py
```

### Running the Tests

```bash
# From the TripSage project root
pytest tests/db/neo4j/
```

## Using the Neo4j Knowledge Graph

### Storing Travel Knowledge

```python
from src.db.neo4j.client import neo4j_client

async def store_travel_knowledge(destination_data):
    """Store travel knowledge in Neo4j."""
    # Add a new destination
    destination = await neo4j_client.add_destination(destination_data)

    # Create relationships to related destinations
    for related_dest in destination_data.get("related_destinations", []):
        await neo4j_client.create_destination_relationship(
            destination.name,
            "CONNECTED_TO",
            related_dest["name"],
            {"distance_km": related_dest.get("distance", 0)}
        )

    return destination
```

### Querying Travel Knowledge

```python
from src.db.neo4j.client import neo4j_client

async def find_travel_recommendations(location, interests, distance_km=100):
    """Find travel recommendations based on location and interests."""
    # Get the destination
    destination = await neo4j_client.get_destination(location)

    if not destination:
        return []

    # Find nearby destinations
    nearby = await neo4j_client.find_nearby_destinations(
        destination.coordinates.latitude,
        destination.coordinates.longitude,
        distance_km
    )

    # Filter by interests (for a real implementation, this would use a more sophisticated query)
    recommendations = []
    for dest in nearby:
        if dest.name != location and dest.popular_for:
            # Check if any interests match
            if any(interest in dest.popular_for for interest in interests):
                recommendations.append(dest)

    return recommendations
```

## Conclusion

This implementation guide provides a comprehensive approach to setting up Neo4j as the knowledge graph for TripSage, including:

1. **Infrastructure**: Connection management, configuration, and error handling
2. **Schema**: Entity definitions with validation using Pydantic
3. **Repositories**: Generic repository pattern for entity operations
4. **Migrations**: Indexes, constraints, and initial data loading
5. **Integration**: Memory MCP client for graph operations
6. **Testing**: Unit tests for the implementation

Follow this guide step-by-step to implement a robust, scalable, and maintainable Neo4j knowledge graph for the TripSage travel planning system.
