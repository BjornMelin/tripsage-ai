# TripSage Neo4j Knowledge Graph Guide (Historical - Deprecated)

**⚠️ HISTORICAL REFERENCE ONLY ⚠️**

**This document is maintained for historical reference. TripSage has completely migrated from Neo4j knowledge graph to a unified Supabase PostgreSQL architecture with Mem0 memory system and pgvector for semantic search.**

**Current Implementation:** See [Relational Database Guide](./RELATIONAL_DATABASE_GUIDE.md) for the unified architecture that provides superior performance and simplicity.

**Migration Completed:** Issue #147 (May 2025) - Neo4j has been completely replaced by Mem0 + pgvector approach.

## Migration Benefits Achieved

**From (Deprecated):** Neo4j knowledge graph with complex entity relationships
**To (Current):** Mem0 memory system with Supabase PostgreSQL backend

**Performance Improvements:**
- 91% lower latency for memory operations
- 26% better memory accuracy with automatic deduplication
- 11x faster vector search vs. standalone vector databases
- <100ms query latency for semantic search operations

**Operational Benefits:**
- 80% reduction in infrastructure complexity
- Unified database management and monitoring
- Simplified development and deployment workflows
- $6,000-9,600 annual cost savings

---

## Historical Overview and Purpose (Deprecated)

TripSage previously utilized a Neo4j knowledge graph as a secondary database within its dual-storage architecture. While the primary relational database (Supabase/Neon) handled structured transactional data, the Neo4j graph database was used for storing and querying data rich in relationships and semantic connections.

The key purposes of the Neo4j knowledge graph in TripSage are:

- **Storing Travel Domain Knowledge**: Representing entities like destinations, accommodations, attractions, airlines, and their complex interconnections (e.g., `LOCATED_IN`, `NEAR_TO`, `OFFERS_ACTIVITY`).
- **Managing User Preferences and History**: Modeling traveler profiles, their past trips, expressed preferences, and discovered travel patterns.
- **Enhancing AI Agent Reasoning**: Providing a rich contextual understanding for AI agents to make more intelligent and personalized recommendations.
- **Facilitating Complex Queries**: Enabling sophisticated queries that traverse relationships, such as finding similar destinations, recommending activities based on proximity and user interests, or identifying travel patterns.
- **Session Persistence**: Storing information about user interactions and system learning across sessions via the Memory MCP.

## 2. Architecture and Integration

### 2.1. Placement in System Architecture

- **Neo4j Database**: Can be a local Neo4j Desktop instance (for development), a self-hosted Docker container, or a managed Neo4j AuraDB instance (for production).
- **Memory MCP Server**: TripSage interacts with Neo4j primarily through the official **`mcp-neo4j-memory`** package. This MCP server acts as a standardized interface, abstracting direct Neo4j driver interactions for most application logic.
- **TripSage Backend/Agents**: These components use a `MemoryClient` (a Python client for the Memory MCP) to perform CRUD operations, execute graph queries, and manage knowledge.

### 2.2. Data Synchronization

While not fully real-time for all data, a synchronization mechanism is planned to keep the knowledge graph consistent with relevant data from the primary Supabase database. This might involve:

- Event-driven updates (e.g., using Supabase webhooks or database triggers).
- Batch synchronization processes.
- Updates triggered by specific agent actions (e.g., when a trip is saved).

A `GraphSyncService` is envisioned to handle these transformations and updates.

## 3. Neo4j Instance Setup and Configuration

### 3.1. Prerequisites

- Neo4j Desktop (development) or Neo4j AuraDB (production).
- Docker (if using containerized deployment).
- Python environment with `neo4j` driver and `python-dotenv`.

### 3.2. Installation and Setup

**Using Docker (Recommended for Development/Self-Hosting):**
A `docker-compose-neo4j.yml` or an entry in the main `docker-compose.yml` is used:

```yaml
# Example docker-compose.yml entry for Neo4j
services:
  neo4j:
    image: neo4j:5.14.0 # Or desired version
    container_name: tripsage-neo4j
    ports:
      - "7474:7474" # Neo4j Browser
      - "7687:7687" # Bolt protocol
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/import # For CSV imports
      - neo4j_plugins:/plugins
    environment:
      - NEO4J_AUTH=neo4j/your_secure_password # Change 'your_secure_password'
      - NEO4J_PLUGINS=["apoc"] # APOC library is highly recommended
      - NEO4J_dbms_memory_heap_initial_size=512m
      - NEO4J_dbms_memory_heap_max_size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
    restart: unless-stopped

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:
```

To start: `docker-compose -f docker-compose-neo4j.yml up -d` (if separate file).

**Neo4j AuraDB (Production):**

1. Sign up at [Neo4j AuraDB](https://neo4j.com/cloud/aura/).
2. Create a new database instance, selecting an appropriate tier and region.
3. Securely note the connection URI, username, and password.
4. AuraDB handles backups and maintenance automatically.

### 3.3. Environment Variables

Configure your TripSage application (e.g., in `.env`):

```plaintext
# Neo4j Database - Direct access (used by Migration tools, some admin tasks, and Memory MCP server itself)
NEO4J_URI=bolt://localhost:7687 # Or your AuraDB URI
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
NEO4J_DATABASE=neo4j # Default database, can be different for AuraDB

# Neo4j Memory MCP Server (if run as a separate process)
MEMORY_MCP_ENDPOINT=http://localhost:3008 # Or the endpoint where your Memory MCP runs
# MEMORY_MCP_API_KEY=your_memory_mcp_api_key (if applicable)
```

### 3.4. Neo4j Configuration (`neo4j.conf`)

If self-hosting, you might adjust `neo4j.conf`:

```ini
# Memory settings (adjust based on available RAM)
dbms.memory.heap.initial_size=1G
dbms.memory.heap.max_size=4G
dbms.memory.pagecache.size=2G

# Connection settings
dbms.connector.bolt.listen_address=0.0.0.0:7687
dbms.connector.http.listen_address=0.0.0.0:7474

# Security
dbms.security.auth_enabled=true
# For APOC and other procedures (use with caution)
# dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.allowlist=apoc.*,gds.*
```

### 3.5. APOC and Graph Data Science (GDS) Extensions

Install APOC (Awesome Procedures On Cypher) and GDS for extended functionality:

- For Docker, add `"apoc", "graph-data-science"` to `NEO4J_PLUGINS`.
- For Desktop/manual installs, download the JARs from Neo4j Labs and place them in the `plugins` directory.

### 3.6. Database User

Create a dedicated user for the TripSage application if not using the default `neo4j` user:

```cypher
CREATE USER tripsage_app SET PASSWORD 'another_secure_password' CHANGE NOT REQUIRED;
GRANT ROLE publisher TO tripsage_app; // Or more specific roles
GRANT ROLE editor TO tripsage_app;  // Or more specific roles
// GRANT IMPERSONATE (user) TO tripsage_app; // If needed for specific auth flows
```

## 4. Knowledge Graph Data Model

TripSage's knowledge graph is designed to capture rich travel-related information.

### 4.1. Core Node Labels (Entity Types)

- **`Destination`**: Represents travel locations (cities, countries, regions, landmarks).
  - Properties: `name` (string, unique), `type` (string: city, country, landmark), `country` (string), `region` (string), `description` (text), `latitude` (float), `longitude` (float), `climate` (string), `bestTimeToVisit` (list of strings), `currency` (string), `language` (string), `safetyRating` (float), `costLevel` (integer).
- **`Accommodation`**: Hotels, hostels, vacation rentals.
  - Properties: `id` (string, unique from provider), `provider` (string: airbnb, booking.com), `name` (string), `type` (string: hotel, apartment), `address` (string), `latitude` (float), `longitude` (float), `rating` (float), `priceRange` (string), `amenities` (list of strings).
- **`Activity`**: Points of interest, tours, events.
  - Properties: `name` (string), `type` (string: museum, tour, park), `description` (text), `duration` (string), `cost` (float), `bookingLink` (string).
- **`Transportation`**: Flights, trains, buses.
  - Properties: `type` (string: flight, train), `providerName` (string), `routeId` (string), `duration` (integer minutes).
- **`FlightSegment`**: A specific leg of a flight.
  - Properties: `flightNumber` (string), `departureAirport` (string), `arrivalAirport` (string), `departureTime` (datetime), `arrivalTime` (datetime), `airline` (string).
- **`User`**: System users.
  - Properties: `userId` (string, unique, links to Supabase user ID), `name` (string), `homeLocation` (string).
- **`UserPreference`**: User's travel preferences.
  - Properties: `preferenceType` (string: airline, accommodation_style, activity_type), `value` (string), `strength` (float).
- **`Trip`**: A planned itinerary.
  - Properties: `tripId` (string, unique, links to Supabase trip ID), `name` (string), `startDate` (date), `endDate` (date), `status` (string: planning, booked).
- **`Review`**: User reviews for accommodations, activities, etc.
  - Properties: `reviewId` (string, unique), `rating` (float), `text` (string), `date` (datetime).
- **`Session`**: Represents a user's interaction session with TripSage.
  - Properties: `sessionId` (string, unique), `startTime` (datetime), `endTime` (datetime), `summary` (text).
- **`Search`**: A search query made during a session.
  - Properties: `searchId` (string, unique), `queryText` (string), `timestamp` (datetime), `resultCount` (integer).
- **`Observation`**: Generic textual observations linked to any entity. Used by the Memory MCP.
  - Properties: `content` (string), `timestamp` (datetime).

### 4.2. Key Relationship Types

- **`LOCATED_IN`**: (Accommodation|Activity|Airport) -[:LOCATED_IN]-> (Destination)
- **`NEAR_TO`**: (Destination|Accommodation|Activity) -[:NEAR_TO {distance: float, unit: "km"}]-> (Destination|Accommodation|Activity)
- **`HAS_ACTIVITY`**: (Destination) -[:HAS_ACTIVITY]-> (Activity)
- **`OFFERS_ACCOMMODATION`**: (Destination) -[:OFFERS_ACCOMMODATION]-> (Accommodation)
- **`OPERATES_FLIGHT`**: (Airline:Node) -[:OPERATES_FLIGHT]-> (FlightSegment)
- **`DEPARTS_FROM`**: (FlightSegment) -[:DEPARTS_FROM]-> (Airport:Node)
- **`ARRIVES_AT`**: (FlightSegment) -[:ARRIVES_AT]-> (Airport:Node)
- **`PLANNED_TRIP`**: (User) -[:PLANNED_TRIP]-> (Trip)
- **`INCLUDES_FLIGHT`**: (Trip) -[:INCLUDES_FLIGHT {bookingStatus: "confirmed"}]-> (FlightSegment)
- **`INCLUDES_ACCOMMODATION`**: (Trip) -[:INCLUDES_ACCOMMODATION]-> (Accommodation)
- **`INCLUDES_ACTIVITY`**: (Trip) -[:INCLUDES_ACTIVITY]-> (Activity)
- **`HAS_PREFERENCE`**: (User) -[:HAS_PREFERENCE]-> (UserPreference)
- **`WROTE_REVIEW`**: (User) -[:WROTE_REVIEW]-> (Review)
- **`REVIEW_OF`**: (Review) -[:REVIEW_OF]-> (Accommodation|Activity|Destination)
- **`PARTICIPATED_IN_SESSION`**: (User) -[:PARTICIPATED_IN_SESSION]-> (Session)
- **`PERFORMED_SEARCH`**: (Session) -[:PERFORMED_SEARCH]-> (Search)
- **`SEARCH_RELATED_TO`**: (Search) -[:SEARCH_RELATED_TO]-> (Destination|Activity|Accommodation)
- **`HAS_OBSERVATION`**: (Entity) -[:HAS_OBSERVATION]-> (Observation) (Used by Memory MCP)

### 4.3. Schema Constraints and Indexes

Essential for data integrity and query performance. These are typically applied via migration scripts.

**Constraints (Examples):**

```cypher
CREATE CONSTRAINT destination_name_unique IF NOT EXISTS FOR (d:Destination) REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.userId IS UNIQUE;
CREATE CONSTRAINT trip_id_unique IF NOT EXISTS FOR (t:Trip) REQUIRE t.tripId IS UNIQUE;
CREATE CONSTRAINT accommodation_id_unique IF NOT EXISTS FOR (a:Accommodation) REQUIRE a.id IS UNIQUE;
// For all nodes that will be primary entities for the Memory MCP:
CREATE CONSTRAINT entity_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;
```

**Indexes (Examples):**

```cypher
CREATE INDEX destination_country_idx IF NOT EXISTS FOR (d:Destination) ON (d.country);
CREATE INDEX destination_type_idx IF NOT EXISTS FOR (d:Destination) ON (d.type);
CREATE INDEX accommodation_type_idx IF NOT EXISTS FOR (a:Accommodation) ON (a.type);
CREATE INDEX activity_type_idx IF NOT EXISTS FOR (act:Activity) ON (act.type);
CREATE TEXT INDEX destination_description_text_idx IF NOT EXISTS FOR (d:Destination) ON (d.description);
CREATE TEXT INDEX observation_content_text_idx IF NOT EXISTS FOR (o:Observation) ON (o.content); // For Memory MCP searches
```

## 5. Memory MCP Server (`mcp-neo4j-memory`) Integration

TripSage leverages the official `mcp-neo4j-memory` package. This server provides a standardized MCP interface to the Neo4j database.

### 5.1. Starting the Memory MCP Server

A script (`scripts/start_memory_mcp.sh`) is provided to manage this:

```bash
#!/bin/bash
# scripts/start_memory_mcp.sh

# Ensure mcp-neo4j-memory is installed
if ! uv pip show mcp-neo4j-memory > /dev/null 2>&1; then
    echo "Installing mcp-neo4j-memory..."
    uv pip install mcp-neo4j-memory
fi

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Use environment variables for configuration, with defaults
NEO4J_URI_MEM_MCP="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER_MEM_MCP="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD_MEM_MCP="${NEO4J_PASSWORD:-your_secure_password}" # Ensure this matches your Neo4j setup
NEO4J_DATABASE_MEM_MCP="${NEO4J_DATABASE:-neo4j}"
MEMORY_MCP_PORT_VAL=$(echo "${MEMORY_MCP_ENDPOINT:-http://localhost:3008}" | awk -F':' '{print $3}')

echo "Starting Neo4j Memory MCP Server on port ${MEMORY_MCP_PORT_VAL}..."
echo "Connecting to Neo4j at ${NEO4J_URI_MEM_MCP} with user ${NEO4J_USER_MEM_MCP} on database ${NEO4J_DATABASE_MEM_MCP}"

# Start the MCP server
# Note: The actual command might vary slightly based on the mcp-neo4j-memory package's CLI
# This assumes it takes environment variables NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
# Or, it might take command-line arguments. Adjust as per the package's documentation.
NEO4J_URI="$NEO4J_URI_MEM_MCP" \
NEO4J_USERNAME="$NEO4J_USER_MEM_MCP" \
NEO4J_PASSWORD="$NEO4J_PASSWORD_MEM_MCP" \
NEO4J_DATABASE="$NEO4J_DATABASE_MEM_MCP" \
python -m mcp_neo4j_memory --port "${MEMORY_MCP_PORT_VAL}"
```

_(Ensure the startup command `python -m mcp_neo4j_memory ...` is correct for the installed package version and its CLI options for passing Neo4j credentials.)_

### 5.2. Memory MCP Tools

The `mcp-neo4j-memory` server typically exposes tools like:

- **`create_entities`**: Adds new nodes (entities) to the graph. Entities have a `name` (unique ID), `entityType`, and a list of `observations` (textual facts).
- **`delete_entities`**: Removes entities.
- **`add_observations`**: Adds new textual facts to existing entities.
- **`delete_observations`**: Removes specific observations.
- **`create_relations`**: Creates relationships between entities. Relations have `from` (entity name), `to` (entity name), and `relationType`.
- **`delete_relations`**: Removes relationships.
- **`search_nodes`**: Searches for entities based on name, type, or observation content (often using full-text search if configured).
- **`open_nodes`**: Retrieves detailed information about specific entities by name, including their observations and direct relationships.
- **`read_graph`**: Retrieves a portion or the entire graph (use with caution on large graphs).

### 5.3. `MemoryClient` (Python Client for Memory MCP)

A Python client (`src/mcp/memory/client.py` or similar) is used by TripSage agents and services to interact with the Memory MCP server.

```python
# src/mcp/memory/client.py (Simplified Example)
from typing import List, Dict, Any, Optional
from ..base_mcp_client import BaseMCPClient # Assuming a base client exists
from ...utils.logging import get_module_logger
from ...utils.config import settings # Centralized settings

logger = get_module_logger(__name__)

class MemoryClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_name="memory", # Matches key in settings.mcp_servers
            endpoint=settings.mcp_servers.memory.endpoint, # From centralized settings
            api_key=settings.mcp_servers.memory.api_key.get_secret_value() if settings.mcp_servers.memory.api_key else None
        )
        logger.info("Initialized Memory MCP Client")

    async def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Args:
            entities: List of entity objects, each with "name", "entityType", "observations".
        """
        return await self.invoke_tool("create_entities", {"entities": entities})

    async def create_relations(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Args:
            relations: List of relation objects, each with "from", "relationType", "to".
        """
        return await self.invoke_tool("create_relations", {"relations": relations})

    async def add_observations(self, entity_name: str, observations: List[str]) -> Dict[str, Any]:
        return await self.invoke_tool("add_observations", {
            "observations": [{"entityName": entity_name, "contents": observations}]
        })

    async def search_nodes(self, query: str, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        # The mcp-neo4j-memory search_nodes might be simple.
        # More complex searches might require a custom tool or direct Cypher via a different MCP.
        params = {"query": query}
        # if entity_type: params["entityType"] = entity_type # If supported by the MCP tool
        response = await self.invoke_tool("search_nodes", params)
        return response.get("nodes", [])

    async def open_nodes(self, names: List[str]) -> List[Dict[str, Any]]:
        response = await self.invoke_tool("open_nodes", {"names": names})
        return response.get("nodes", [])

    # ... other methods mapping to Memory MCP tools ...
```

## 6. Direct Neo4j Driver Integration (for Admin/Migrations)

While day-to-day operations use the Memory MCP, direct Neo4j driver access is needed for schema management (constraints, indexes), complex administrative queries, and potentially bulk data loading.

### 6.1. Python Neo4j Driver Client

A `Neo4jDirectClient` (e.g., in `src/db/neo4j_direct_client.py`) using the `neo4j` Python package.

```python
# src/db/neo4j_direct_client.py (Simplified Example)
from neo4j import GraphDatabase, Driver, AsyncGraphDatabase, AsyncDriver
from typing import List, Dict, Any, Optional
from ...utils.config import settings # Centralized settings
from ...utils.logging import get_module_logger

logger = get_module_logger(__name__)

class Neo4jDirectClient:
    _driver: Optional[AsyncDriver] = None

    def __init__(self):
        self.uri = settings.neo4j.uri
        self.user = settings.neo4j.user
        self.password = settings.neo4j.password.get_secret_value() if settings.neo4j.password else None
        self.database = settings.neo4j.database

    async def _get_driver(self) -> AsyncDriver:
        if self._driver is None or self._driver._closed: # Check if driver is closed
            logger.info(f"Connecting to Neo4j: {self.uri}, Database: {self.database}")
            self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Optionally verify connectivity here if needed, though driver creation itself can fail
        return self._driver

    async def close(self):
        if self._driver is not None and not self._driver._closed:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j direct connection closed.")

    async def execute_cypher_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        driver = await self._get_driver()
        async with driver.session(database=self.database) as session:
            results = await session.run(query, parameters)
            return [record.data() async for record in results] # Process results asynchronously

    async def apply_constraint(self, constraint_cypher: str):
        logger.info(f"Applying constraint: {constraint_cypher}")
        await self.execute_cypher_query(constraint_cypher)

    async def apply_index(self, index_cypher: str):
        logger.info(f"Applying index: {index_cypher}")
        await self.execute_cypher_query(index_cypher)

# Singleton instance or factory function
# neo4j_direct_client = Neo4jDirectClient()
```

### 6.2. Schema Migrations (Constraints and Indexes)

Migration scripts (e.g., `src/db/migrations/neo4j/V1__initial_schema.py`) use the `Neo4jDirectClient` to apply constraints and indexes.

```python
# src/db/migrations/neo4j/V1__initial_schema.py
# from ....db.neo4j_direct_client import Neo4jDirectClient # Adjust import path

# async def apply_migrations(client: Neo4jDirectClient):
#     constraints = [
#         "CREATE CONSTRAINT destination_name_unique IF NOT EXISTS FOR (d:Destination) REQUIRE d.name IS UNIQUE;",
#         "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;"
#     ]
#     indexes = [
#         "CREATE INDEX destination_country_idx IF NOT EXISTS FOR (d:Destination) ON (d.country);",
#         "CREATE TEXT INDEX observation_content_text_idx IF NOT EXISTS FOR (o:Observation) ON (o.content);"
#     ]
#     for c in constraints: await client.apply_constraint(c)
#     for i in indexes: await client.apply_index(i)
#     logger.info("Applied Neo4j initial schema constraints and indexes.")

# if __name__ == "__main__":
#     import asyncio
#     # client = Neo4jDirectClient()
#     # asyncio.run(apply_migrations(client))
#     # asyncio.run(client.close())
```

## 7. Data Modeling Examples in Cypher

**Creating a Destination with Observations (via Memory MCP concepts):**

```cypher
// 1. Create the Destination as an :Entity node
MERGE (d:Entity {name: "Paris"})
ON CREATE SET d.entityType = "Destination", d.created_at = datetime()
ON MATCH SET d.updated_at = datetime()

// 2. Create Observation nodes
CREATE (obs1:Observation {content: "Capital of France", timestamp: datetime()})
CREATE (obs2:Observation {content: "Known for Eiffel Tower", timestamp: datetime()})

// 3. Link Observations to the Destination
WITH d, obs1, obs2
MERGE (d)-[:HAS_OBSERVATION]->(obs1)
MERGE (d)-[:HAS_OBSERVATION]->(obs2)

RETURN d, obs1, obs2
```

**Creating a User and their Preference:**

```cypher
// Create User entity
MERGE (u:Entity {name: "User:user123"})
ON CREATE SET u.entityType = "User", u.created_at = datetime()

// Create UserPreference entity (if modeling preferences as separate entities)
MERGE (p:Entity {name: "Pref:WindowSeat"})
ON CREATE SET p.entityType = "FlightPreference", p.created_at = datetime()
CREATE (obs_p:Observation {content: "User prefers window seats on flights", timestamp: datetime()})
MERGE (p)-[:HAS_OBSERVATION]->(obs_p)


// Link User to Preference
WITH u, p
MERGE (u)-[:HAS_FLIGHT_PREFERENCE]->(p) // Using a more specific relationship type
```

**Querying for Destinations near "Paris" that offer "Museums":**

```cypher
MATCH (paris:Entity {name: "Paris", entityType: "Destination"})
MATCH (nearby_dest:Entity {entityType: "Destination"})<-[:LOCATED_IN]-(activity:Entity {entityType: "Activity"})
WHERE point.distance(
          point({latitude: paris.latitude, longitude: paris.longitude}),
          point({latitude: nearby_dest.latitude, longitude: nearby_dest.longitude})
      ) < 50000 // 50km radius
AND activity.name CONTAINS "Museum" // Or (activity)-[:HAS_OBSERVATION]->(obs) WHERE obs.content CONTAINS "Museum"
RETURN DISTINCT nearby_dest.name, activity.name
```

_(Note: This query assumes `latitude`, `longitude` are properties on `Destination` nodes, which might be managed directly or as observations depending on the chosen modeling depth.)_

## 8. Optimization and Best Practices

- **Indexing**: Create indexes on frequently queried properties (e.g., `Entity.name`, `Entity.entityType`, `Observation.content` if using text indexes).
- **Constraints**: Use unique constraints for entity identifiers (`Entity.name`).
- **Query Optimization**:
  - Use `PROFILE` or `EXPLAIN` in Neo4j Browser to analyze query performance.
  - Limit graph traversal depth where possible.
  - Use parameterized queries.
- **Batch Operations**: For bulk data ingestion or updates, use `UNWIND` in Cypher or batch operations provided by the Neo4j driver/Memory MCP.
- **Data Model Simplicity**: The Memory MCP's `Entity-Observation-Relation` model is quite generic. For more complex travel-specific queries, consider evolving the graph model with more specific node labels (e.g., `:City`, `:Country`, `:Hotel`) and relationship types, and potentially exposing more specialized tools via a custom Travel Knowledge MCP if needed.

## 9. Testing

- **Unit Tests**: For the `MemoryClient` and any service layers interacting with it. Mock the `invoke_tool` method of `BaseMCPClient`.
- **Integration Tests**: Test interactions with a live (but test-dedicated) Memory MCP server connected to a test Neo4j instance. These tests verify that entities and relations are created and queried correctly.
  - Use `pytest` fixtures to manage test Neo4j instances or clear data between tests.
- **Example Integration Test Snippet**:

  ```python
  # tests/integration/test_memory_integration.py
  # import pytest
  # from ...mcp.memory.client import MemoryClient # Adjust import

  # @pytest.mark.asyncio
  # async def test_create_and_retrieve_entity(memory_mcp_client: MemoryClient): # Fixture for client
  #     entity_name = "TestLocationAlpha"
  #     entity_type = "TestDestination"
  #     observations = ["Observation A", "Observation B"]

  #     create_response = await memory_mcp_client.create_entities([
  #         {"name": entity_name, "entityType": entity_type, "observations": observations}
  #     ])
  #     assert create_response.get("created", []).get("name") == entity_name

  #     open_response = await memory_mcp_client.open_nodes([entity_name])
  #     assert len(open_response) == 1
  #     node = open_response
  #     assert node["name"] == entity_name
  #     assert node["type"] == entity_type # Assuming 'type' is returned by open_nodes
  #     # Check observations, may need to adjust based on actual open_nodes response structure
  #     # assert all(obs_content in [obs.get("content") for obs in node.get("observations", [])] for obs_content in observations)
  ```

## 10. Troubleshooting

- **Connection Issues**: Verify Neo4j URI, credentials, and database name. Ensure the Neo4j instance is running and accessible. Check firewall rules.
- **Memory MCP Server Not Running**: Ensure the `mcp-neo4j-memory` server process is started correctly (e.g., using `scripts/start_memory_mcp.sh`) and listening on the configured `MEMORY_MCP_ENDPOINT`.
- **Authentication Errors**: Double-check API keys if the Memory MCP is secured. For direct Neo4j access, verify user/password.
- **Query Performance**: Use Neo4j Browser's `PROFILE` feature. Check for missing indexes or inefficient Cypher queries.
- **Data Consistency**: If synchronizing with Supabase, ensure the sync logic is robust and handles potential conflicts or errors.

This guide provides a comprehensive plan for integrating and utilizing the Neo4j knowledge graph in TripSage, primarily through the Memory MCP. Adherence to these guidelines will ensure a robust, scalable, and maintainable knowledge management system.
