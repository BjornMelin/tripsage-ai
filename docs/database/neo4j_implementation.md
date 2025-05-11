# Neo4j Knowledge Graph Implementation Plan

This document outlines the implementation plan for setting up Neo4j as the knowledge graph database for TripSage.

## Overview

TripSage uses a dual-storage architecture with Supabase for structured relational data and Neo4j for knowledge graph capabilities. This ensures optimal storage and retrieval for different types of travel data.

## Implementation Tasks

### 1. Neo4j Instance Setup

#### Requirements

- Neo4j Desktop or Neo4j AuraDB cloud instance
- Configuration for optimal performance with travel knowledge graph
- Security setup with proper authentication

#### Implementation Steps

1. Install Neo4j Desktop for development or set up Neo4j AuraDB for production
2. Configure Neo4j with appropriate memory settings
3. Set up authentication with secure credentials
4. Configure backup and recovery processes
5. Set up monitoring and logging

### 2. Knowledge Graph Schema Design

TripSage requires two distinct knowledge graphs:

#### Travel Domain Knowledge Graph

- **Nodes**: Destinations, Attractions, Accommodations, Airlines, Travel Seasons
- **Relationships**: LOCATED_IN, OFFERS, OPERATES_BETWEEN, BEST_DURING
- **Properties**: Various attributes like ratings, prices, seasonal information

Example schema:

```cypher
// Node labels
:Destination {name, country, region, description, climate, language, currency}
:Attraction {name, type, description, rating, price_range, duration}
:Accommodation {name, type, description, rating, price_range, amenities}
:Airline {name, alliance, hub_airports, rating}
:Season {name, months, weather_description, crowd_level}

// Relationships
(:Attraction)-[:LOCATED_IN]->(:Destination)
(:Accommodation)-[:LOCATED_IN]->(:Destination)
(:Airline)-[:OPERATES_BETWEEN]->(:Destination)
(:Destination)-[:BEST_DURING]->(:Season)
(:Attraction)-[:BEST_DURING]->(:Season)
```

#### Project Meta-Knowledge Graph

- **Nodes**: Sessions, Searches, UserPreferences
- **Relationships**: SEARCHED_FOR, PREFERRED
- **Properties**: Search parameters, preferences, timestamps

Example schema:

```cypher
// Node labels
:Session {session_id, start_time, end_time, user_id}
:Search {query, timestamp, result_count}
:UserPreference {preference_type, value, strength}

// Relationships
(:Session)-[:INCLUDED]->(:Search)
(:Session)-[:ESTABLISHED]->(:UserPreference)
(:Search)-[:CONCERNING]->(:Destination)
```

### 3. Neo4j Python Driver Integration

#### Implementation

1. Install Neo4j Python driver:

   ```bash
   uv pip install neo4j
   ```

2. Create connection pool manager:

   ```python
   from neo4j import GraphDatabase
   from src.utils.config import get_config

   class Neo4jConnection:
       def __init__(self):
           config = get_config()
           self._uri = config.get("NEO4J_URI")
           self._user = config.get("NEO4J_USER")
           self._password = config.get("NEO4J_PASSWORD")
           self._driver = GraphDatabase.driver(
               self._uri,
               auth=(self._user, self._password)
           )

       def close(self):
           if self._driver is not None:
               self._driver.close()

       def execute_query(self, query, parameters=None):
           with self._driver.session() as session:
               result = session.run(query, parameters or {})
               return [record for record in result]
   ```

### 4. Memory MCP Server Implementation

The Memory MCP Server will provide the interface between agents and the knowledge graph:

1. Create server using FastMCP 2.0
2. Implement standard knowledge graph operations:
   - Entity creation and retrieval
   - Relationship management
   - Graph traversal and pattern matching
   - Knowledge persistence across sessions

Example tool implementations:

```python
@app.tool
async def create_entity(params: EntityCreationParams) -> Dict[str, Any]:
    """Create a new entity in the knowledge graph.

    Args:
        params: Entity creation parameters

    Returns:
        Created entity details
    """
    # Implementation

@app.tool
async def find_relationships(params: RelationshipQueryParams) -> Dict[str, Any]:
    """Find relationships between entities in the knowledge graph.

    Args:
        params: Relationship query parameters

    Returns:
        Matching relationships
    """
    # Implementation
```

### 5. Data Synchronization with Supabase

To maintain consistency between Supabase and Neo4j:

1. Implement event-based synchronization (using Supabase webhooks)
2. Create data transformation layer between relational and graph models
3. Set up periodic reconciliation processes

Example synchronization workflow:

```python
async def sync_destination_to_graph(destination_id: str):
    """Synchronize a destination from Supabase to Neo4j.

    Args:
        destination_id: The ID of the destination to synchronize
    """
    # Get destination from Supabase
    destination = await supabase_client.from_("destinations").select("*").eq("id", destination_id).single()

    # Create or update Neo4j node
    query = """
    MERGE (d:Destination {id: $id})
    SET d.name = $name,
        d.country = $country,
        d.description = $description,
        d.updated_at = $updated_at
    RETURN d
    """

    result = neo4j_connection.execute_query(
        query,
        {
            "id": destination["id"],
            "name": destination["name"],
            "country": destination["country"],
            "description": destination["description"],
            "updated_at": destination["updated_at"]
        }
    )

    return result
```

## Timeline and Milestones

1. **Week 1**: Neo4j instance setup and configuration
2. **Week 2**: Knowledge graph schema design and implementation
3. **Week 3**: Neo4j Python driver integration and Memory MCP Server
4. **Week 4**: Data synchronization and testing

## Success Criteria

1. Neo4j instance is properly configured and secured
2. Knowledge graph schema supports all required travel entities and relationships
3. Memory MCP Server provides all necessary graph operations
4. Data remains consistent between Supabase and Neo4j
5. Performance meets requirements for agent interactions

## Next Steps (after completion)

1. Implement advanced graph algorithms for travel recommendations
2. Create visualization tools for knowledge graph exploration
3. Develop machine learning models using graph data for personalization
