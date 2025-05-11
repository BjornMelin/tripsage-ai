# Neo4j Knowledge Graph for TripSage

This document provides a comprehensive guide to TripSage's Neo4j knowledge graph implementation, combining information from the implementation overview, detailed plan, and step-by-step guide.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Components](#implementation-components)
4. [Data Model](#data-model)
5. [Implementation Steps](#implementation-steps)
6. [Integration with TripSage](#integration-with-tripsage)
7. [Optimization Strategies](#optimization-strategies)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

## Overview

TripSage uses a dual-storage architecture with Supabase for structured relational data and Neo4j for knowledge graph capabilities. This ensures optimal storage and retrieval for different types of travel data.

The Neo4j knowledge graph stores entities like destinations, accommodations, attractions, and relationships between them. This graph structure allows for complex queries such as finding connections between destinations, discovering similar travel patterns, and identifying related points of interest.

## Architecture

The Neo4j component fits into the TripSage architecture as follows:

- **Supabase Database**: Primary storage for structured data (users, trips, bookings)
- **Neo4j Knowledge Graph**: Secondary storage for relationship-rich data and travel domain knowledge
- **Memory MCP Server**: Interface between TripSage and the Neo4j database
- **Travel Agent**: Consumes knowledge graph data for intelligent recommendations

## Implementation Components

The implementation consists of several key components:

1. **Neo4j Database**: Either Neo4j Desktop (development) or Neo4j AuraDB (production)
2. **Neo4j Python Driver**: For connecting to the database from the TripSage backend
3. **Memory MCP Server**: MCP wrapper around Neo4j functionality
4. **Knowledge Graph Service**: Python service layer for abstracting graph operations
5. **Data Import Scripts**: For initial population of travel knowledge
6. **Integration Tests**: For verifying knowledge graph functionality

## Data Model

### Core Entities

- **Destination**: Cities, countries, or specific locations travelers can visit
- **PointOfInterest**: Attractions, landmarks, or specific sites within destinations
- **Accommodation**: Hotels, vacation rentals, hostels, etc.
- **Transportation**: Flights, trains, buses, rental cars, etc.
- **Activity**: Tours, experiences, or events available at destinations
- **Traveler**: User profiles with preferences and travel history
- **Trip**: A collection of travel components planned together
- **Review**: Feedback on any travel component

### Key Relationships

- **LOCATED_IN**: Geographic containment (e.g., PointOfInterest LOCATED_IN Destination)
- **NEAR**: Proximity relationship between entities
- **TRAVELED_TO**: Connection between Traveler and Destination
- **STAYED_AT**: Connection between Traveler and Accommodation
- **VISITED**: Connection between Traveler and PointOfInterest
- **INCLUDES**: Composition relationship (e.g., Trip INCLUDES Accommodation)
- **SIMILAR_TO**: Similarity relationship between entities of the same type
- **REVIEWED**: Connection between Traveler and any reviewable entity

## Implementation Steps

### 1. Setup and Installation

1. **Install Neo4j**

   - For local development: Install Neo4j Desktop
   - For production: Set up Neo4j AuraDB instance

2. **Configure Database**

   - Create a new graph database
   - Set appropriate memory allocation
   - Configure security settings

3. **Install Dependencies**

   ```bash
   uv pip install 'neo4j>=5.0.0' 'fastmcp>=2.0.0'
   ```

### 2. Database Schema Setup

1. **Create Constraints**

   ```cypher
   CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE
   ```

2. **Create Indexes**

   ```cypher
   CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name)
   CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.entityType)
   ```

### 3. Entity Service Implementation

Create the core entity service that will handle operations on entities:

```python
# src/mcp/memory/services/entity_service.py
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional

class EntityService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_entity(self, name: str, entity_type: str, observations: List[str]) -> Dict[str, Any]:
        with self.driver.session() as session:
            result = session.run(
                """
                CREATE (e:Entity {
                    id: randomUUID(),
                    name: $name,
                    entityType: $entity_type,
                    observations: $observations
                })
                RETURN e
                """,
                name=name,
                entity_type=entity_type,
                observations=observations
            )
            record = result.single()
            return record["e"] if record else None

    def find_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity)
                WHERE e.entityType = $entity_type
                RETURN e
                """,
                entity_type=entity_type
            )
            return [dict(record["e"].items()) for record in result]

    # Additional methods would be implemented here
```

### 4. Relationship Service Implementation

Create the relationship service for managing connections between entities:

```python
# src/mcp/memory/services/relationship_service.py
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional

class RelationshipService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_relationship(self, from_entity: str, relationship_type: str, to_entity: str) -> bool:
        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH (from:Entity {{name: $from_name}}), (to:Entity {{name: $to_name}})
                CREATE (from)-[r:{relationship_type}]->(to)
                RETURN r
                """,
                from_name=from_entity,
                to_name=to_entity
            )
            return result.single() is not None

    def find_related_entities(self, entity_name: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            query = """
                MATCH (from:Entity {name: $entity_name})-[r]->(to:Entity)
                """

            if relationship_type:
                query += f"WHERE type(r) = '{relationship_type}' "

            query += "RETURN to, type(r) as relationship"

            result = session.run(query, entity_name=entity_name)

            return [
                {
                    "entity": dict(record["to"].items()),
                    "relationship": record["relationship"]
                }
                for record in result
            ]

    # Additional methods would be implemented here
```

### 5. Memory MCP Server Implementation

Create the Memory MCP Server that will expose Neo4j functionality through the MCP protocol:

```python
# src/mcp/memory/server.py
from fastmcp import FastMCP, Context
from typing import Dict, List, Any
import os

from .services.entity_service import EntityService
from .services.relationship_service import RelationshipService

# Initialize services
entity_service = EntityService(
    uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "password")
)

relationship_service = RelationshipService(
    uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "password")
)

# Create MCP server
mcp = FastMCP(name="Memory MCP Server")

@mcp.tool()
async def create_entities(entities: List[Dict[str, Any]], ctx: Context) -> Dict[str, Any]:
    """Create multiple new entities in the knowledge graph.

    Args:
        entities: List of entity objects with name, entityType, and observations
        ctx: MCP context

    Returns:
        Dict with success status and created entities
    """
    try:
        created_entities = []

        for entity in entities:
            created = entity_service.create_entity(
                name=entity["name"],
                entity_type=entity["entityType"],
                observations=entity["observations"]
            )
            if created:
                created_entities.append(created)

        return {
            "success": True,
            "created": len(created_entities),
            "entities": created_entities
        }
    except Exception as e:
        await ctx.error(f"Error creating entities: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
async def create_relations(relations: List[Dict[str, Any]], ctx: Context) -> Dict[str, Any]:
    """Create multiple new relations between entities in the knowledge graph.

    Args:
        relations: List of relation objects with from, to, and relationType
        ctx: MCP context

    Returns:
        Dict with success status and created relations count
    """
    try:
        success_count = 0

        for relation in relations:
            success = relationship_service.create_relationship(
                from_entity=relation["from"],
                relationship_type=relation["relationType"],
                to_entity=relation["to"]
            )
            if success:
                success_count += 1

        return {
            "success": True,
            "created": success_count,
            "total": len(relations)
        }
    except Exception as e:
        await ctx.error(f"Error creating relations: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Additional MCP tools would be defined here

if __name__ == "__main__":
    mcp.run()
```

### 6. Data Import Implementation

Create scripts for importing initial travel data into the knowledge graph:

```python
# scripts/import_destinations.py
import csv
import asyncio
from src.mcp.memory.client import MemoryClient

async def import_destinations():
    client = MemoryClient()

    with open('data/destinations.csv', 'r') as f:
        reader = csv.DictReader(f)

        for batch in chunk_list(list(reader), 10):
            entities = []

            for row in batch:
                entities.append({
                    "name": row["name"],
                    "entityType": "Destination",
                    "observations": [
                        f"Located in {row['country']}",
                        f"Famous for {row['known_for']}",
                        f"Best time to visit: {row['best_time_to_visit']}"
                    ]
                })

            result = await client.create_entities(entities)
            print(f"Created {result['created']} destinations")

def chunk_list(lst, chunk_size):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

if __name__ == "__main__":
    asyncio.run(import_destinations())
```

## Integration with TripSage

### Memory MCP Client

```python
# src/mcp/memory/client.py
from agents import function_tool
from typing import Dict, List, Any

class MemoryClient:
    def __init__(self, endpoint=None):
        self.endpoint = endpoint or "http://localhost:3000"

    @function_tool
    async def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple new entities in the knowledge graph.

        Args:
            entities: List of entity objects with name, entityType, and observations

        Returns:
            Dict with success status and created entities
        """
        # Implementation that calls the Memory MCP Server
        # This would use httpx or another HTTP client to make the request
        pass

    @function_tool
    async def create_relations(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple new relations between entities in the knowledge graph.

        Args:
            relations: List of relation objects with from, to, and relationType

        Returns:
            Dict with success status and created relations count
        """
        # Implementation that calls the Memory MCP Server
        pass

    # Additional client methods would be implemented here
```

### Travel Agent Integration

```python
# src/agents/travel_agent.py
from agents import Agent
from src.mcp.memory.client import MemoryClient

memory_client = MemoryClient()

travel_agent = Agent(
    name="TripSage Travel Agent",
    description="AI-powered travel planning assistant",
    tools=[
        memory_client.create_entities,
        memory_client.create_relations,
        memory_client.search_nodes,
        # Other tools
    ]
)
```

## Optimization Strategies

### 1. Query Optimization

- Use parameterized queries to leverage Neo4j's query cache
- Limit traversal depth for graph queries
- Use PROFILE and EXPLAIN to analyze query performance
- Create appropriate indexes for commonly queried properties

### 2. Caching Strategy

- Cache frequently accessed entities and relationships
- Implement time-to-live (TTL) caching for search results
- Use Redis for distributed caching in production

### 3. Batch Operations

- Group entity and relationship creations into batches
- Use Neo4j's transaction batching for multiple operations
- Implement bulk import for large datasets

## Monitoring and Maintenance

### 1. Performance Monitoring

- Track query execution times
- Monitor memory usage and garbage collection
- Set up alerts for slow queries
- Log API call patterns and frequencies

### 2. Database Maintenance

- Schedule regular backups
- Implement database cleanup routines
- Monitor disk space usage
- Update Neo4j to latest versions for performance improvements

## Testing

### Unit Tests

```python
# tests/mcp/memory/test_entity_service.py
import pytest
from unittest.mock import Mock, patch
from src.mcp.memory.services.entity_service import EntityService

class TestEntityService:
    @pytest.fixture
    def mock_session(self):
        return Mock()

    @pytest.fixture
    def mock_driver(self, mock_session):
        driver = Mock()
        driver.session.return_value = mock_session
        return driver

    @pytest.fixture
    def entity_service(self, mock_driver):
        with patch("neo4j.GraphDatabase.driver", return_value=mock_driver):
            service = EntityService("bolt://localhost:7687", "neo4j", "password")
            yield service
            service.close()

    def test_create_entity(self, entity_service, mock_session):
        # Setup mock
        mock_result = Mock()
        mock_record = Mock()
        mock_record["e"] = {"id": "123", "name": "Paris", "entityType": "Destination"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        # Test
        result = entity_service.create_entity("Paris", "Destination", ["Capital of France"])

        # Verify
        assert result == {"id": "123", "name": "Paris", "entityType": "Destination"}
        mock_session.run.assert_called_once()
```

### Integration Tests

```python
# tests/integration/test_memory_mcp.py
import pytest
import asyncio
from src.mcp.memory.client import MemoryClient

@pytest.mark.asyncio
async def test_create_and_query_entity():
    # This test requires a running Neo4j instance
    client = MemoryClient()

    # Create an entity
    create_result = await client.create_entities([{
        "name": "Test Destination",
        "entityType": "Destination",
        "observations": ["Test observation"]
    }])

    assert create_result["success"] == True
    assert create_result["created"] == 1

    # Search for the entity
    search_result = await client.search_nodes("Test Destination")

    assert len(search_result["nodes"]) > 0
    assert search_result["nodes"][0]["name"] == "Test Destination"
```

## Troubleshooting

### Common Issues and Solutions

1. **Connection Issues**

   - Verify Neo4j service is running
   - Check connection string format
   - Ensure network connectivity between application and database

2. **Performance Problems**

   - Review query execution plans
   - Check for missing indexes
   - Limit result sets and traversal depth
   - Implement proper caching

3. **Data Consistency**

   - Use transactions for related operations
   - Implement retry logic for failed operations
   - Set up constraints for critical properties

4. **Memory Issues**
   - Configure appropriate heap size for Neo4j
   - Implement pagination for large result sets
   - Monitor and adjust JVM settings
