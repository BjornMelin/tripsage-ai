# Neo4j Knowledge Graph Implementation Plan

This document provides a detailed implementation plan for setting up and integrating Neo4j as the knowledge graph database for TripSage. It outlines the step-by-step process, required components, and integration points.

## 1. Overview

TripSage uses a dual-storage architecture with Supabase for structured relational data and Neo4j for knowledge graph capabilities. This approach ensures optimal storage and retrieval for different types of travel information while maintaining a consistent view of the data.

## 2. Implementation Components

### 2.1 Neo4j Instance Setup

#### Prerequisites

- Neo4j Desktop (for development) or Neo4j AuraDB (for production)
- Docker for containerized deployment
- Authentication credentials and access controls
- Network configuration for secure connections

#### Implementation Steps

1. **Create Neo4j Instance**

   ```bash
   # For development with Docker
   docker run \
     --name neo4j-tripsage \
     -p 7474:7474 -p 7687:7687 \
     -v $PWD/neo4j/data:/data \
     -v $PWD/neo4j/logs:/logs \
     -v $PWD/neo4j/import:/import \
     -v $PWD/neo4j/plugins:/plugins \
     -e NEO4J_AUTH=neo4j/password \
     -e NEO4J_dbms_memory_heap_max__size=4G \
     -e NEO4J_dbms_memory_pagecache_size=2G \
     neo4j:5.13
   ```

   For production, create a Neo4j AuraDB instance:

   1. Sign up for Neo4j AuraDB
   2. Create a new database with appropriate tier (Professional or Enterprise)
   3. Configure region for optimal latency
   4. Note connection credentials for future use

2. **Configure Neo4j Settings**

   Update `neo4j.conf` with optimized settings:

   ```ini
   # Memory settings
   dbms.memory.heap.initial_size=1G
   dbms.memory.heap.max_size=4G
   dbms.memory.pagecache.size=2G

   # Connection settings
   dbms.connector.bolt.listen_address=0.0.0.0:7687
   dbms.connector.http.listen_address=0.0.0.0:7474

   # Security settings
   dbms.security.procedures.unrestricted=apoc.*
   dbms.security.auth_enabled=true

   # APOC extension
   dbms.security.procedures.allowlist=apoc.*
   ```

3. **Install APOC Extension**

   - Download APOC from <https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases>
   - Place in the plugins directory
   - Restart Neo4j instance

4. **Create Database User**

   ```cypher
   CREATE USER tripsage WITH PASSWORD 'password' SET PASSWORD CHANGE NOT REQUIRED;
   GRANT ROLE architect TO tripsage;
   ```

5. **Set up Backup Process**

   ```bash
   # Schedule daily backup
   neo4j-admin dump --database=neo4j --to=/backup/neo4j-$(date +%Y%m%d).dump
   ```

   For AuraDB, use their built-in backup and restore features.

### 2.2 Knowledge Graph Schema Design

The TripSage knowledge graph consists of two primary graph models:

#### Travel Domain Graph

This graph represents travel-specific entities and relationships:

```cypher
// Create constraints and indexes
CREATE CONSTRAINT destination_name_unique IF NOT EXISTS
FOR (d:Destination) REQUIRE d.name IS UNIQUE;

CREATE CONSTRAINT accommodation_id_unique IF NOT EXISTS
FOR (a:Accommodation) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT airline_iata_unique IF NOT EXISTS
FOR (al:Airline) REQUIRE al.iata_code IS UNIQUE;

CREATE CONSTRAINT airport_iata_unique IF NOT EXISTS
FOR (ap:Airport) REQUIRE ap.iata_code IS UNIQUE;

CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT trip_id_unique IF NOT EXISTS
FOR (t:Trip) REQUIRE t.id IS UNIQUE;

// Create indexes
CREATE INDEX destination_country IF NOT EXISTS FOR (d:Destination) ON (d.country);
CREATE INDEX accommodation_type IF NOT EXISTS FOR (a:Accommodation) ON (a.type);
CREATE INDEX trip_date_range IF NOT EXISTS FOR (t:Trip) ON (t.start_date, t.end_date);
```

Define core node types:

```cypher
// Sample node definitions
// These are used for reference/documentation - not executed directly

// Destination node (city, country, landmark)
(:Destination {
    name: "Paris",
    country: "France",
    region: "Île-de-France",
    description: "Capital city of France",
    coordinates: {latitude: 48.8566, longitude: 2.3522},
    population: 2161000,
    time_zone: "Europe/Paris",
    language: "French",
    currency: "EUR"
})

// Accommodation node (hotel, hostel, rental)
(:Accommodation {
    id: "acc12345",
    name: "Grand Hotel Paris",
    type: "hotel",
    rating: 4.5,
    star_rating: 4,
    address: "1 Rue de Rivoli, 75001 Paris, France",
    coordinates: {latitude: 48.8624, longitude: 2.3359},
    price_range: {min: 150, max: 400, currency: "EUR"},
    amenities: ["wifi", "pool", "restaurant", "spa"]
})

// Airline node
(:Airline {
    name: "Air France",
    iata_code: "AF",
    alliance: "SkyTeam",
    country: "France",
    hub_airports: ["CDG", "ORY"],
    rating: 3.8
})

// Airport node
(:Airport {
    name: "Paris Charles de Gaulle Airport",
    iata_code: "CDG",
    city: "Paris",
    country: "France",
    coordinates: {latitude: 49.0097, longitude: 2.5479}
})

// User node
(:User {
    id: "user12345",
    name: "Jane Smith",
    preferences: {
        preferred_airlines: ["AF", "BA"],
        preferred_accommodation_types: ["hotel"],
        budget_range: {min: 2000, max: 5000, currency: "USD"},
        travel_style: "luxury"
    }
})

// Trip node
(:Trip {
    id: "trip12345",
    user_id: "user12345",
    name: "Summer in Europe",
    start_date: "2025-06-15",
    end_date: "2025-06-30",
    budget: 4500,
    budget_currency: "USD",
    status: "planning"
})
```

Define relationship types:

```cypher
// Sample relationship definitions

// Destination relationships
(:Destination)-[:CONTAINS]->(:Destination)  // Paris CONTAINS Montmartre
(:Destination)-[:NEAR_TO {distance: 35.0, unit: "km"}]->(:Destination)  // Paris NEAR_TO Versailles
(:Airport)-[:SERVES]->(:Destination)  // CDG SERVES Paris
(:Accommodation)-[:LOCATED_IN]->(:Destination)  // Grand Hotel Paris LOCATED_IN Paris

// Transport relationships
(:Airline)-[:OPERATES_ROUTE {
    flight_time: 130,
    frequency: "daily",
    distance: 1033.0,
    unit: "km"
}]->(:Route)  // AF OPERATES_ROUTE CDG-LHR
(:Route)-[:CONNECTS {terminal: "2E"}]->(:Airport)  // Route CONNECTS CDG
(:Route)-[:CONNECTS {terminal: "5"}]->(:Airport)  // Route CONNECTS LHR

// User relationships
(:User)-[:PREFERS]->(:Airline)  // User PREFERS AF
(:User)-[:TRAVELED_TO {date: "2024-03-15", rating: 5}]->(:Destination)  // User TRAVELED_TO Paris
(:User)-[:PLANNED]->(:Trip)  // User PLANNED Summer in Europe

// Trip relationships
(:Trip)-[:INCLUDES]->(:Destination)  // Trip INCLUDES Paris
(:Trip)-[:INCLUDES]->(:Accommodation)  // Trip INCLUDES Grand Hotel Paris
(:Trip)-[:INCLUDES {
    flight_number: "AF1234",
    departure: "2025-06-15T10:30:00",
    arrival: "2025-06-15T12:45:00"
}]->(:Route)  // Trip INCLUDES CDG-LHR flight
```

#### Project Meta-Knowledge Graph

This graph tracks user interactions and learning across sessions:

```cypher
// Create constraints
CREATE CONSTRAINT session_id_unique IF NOT EXISTS
FOR (s:Session) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT search_id_unique IF NOT EXISTS
FOR (q:Search) REQUIRE s.id IS UNIQUE;

// Create indexes
CREATE INDEX user_session_index IF NOT EXISTS FOR (s:Session) ON (s.user_id);
CREATE INDEX session_timestamp_index IF NOT EXISTS FOR (s:Session) ON (s.timestamp);
```

Define meta-knowledge nodes:

```cypher
// Sample meta-knowledge nodes

// Session node
(:Session {
    id: "session12345",
    user_id: "user12345",
    start_time: "2025-05-01T14:30:00",
    end_time: "2025-05-01T15:45:00",
    client_info: {
        browser: "Chrome",
        device: "Desktop",
        ip_region: "California"
    }
})

// Search node
(:Search {
    id: "search12345",
    query_type: "flight",
    parameters: {
        origin: "SFO",
        destination: "CDG",
        departure_date: "2025-06-15",
        return_date: "2025-06-30",
        passengers: 2,
        cabin_class: "economy"
    },
    timestamp: "2025-05-01T14:35:00",
    result_count: 24
})

// UserPreference node
(:UserPreference {
    preference_type: "cabin_class",
    value: "business",
    strength: 0.8,
    last_updated: "2025-05-01T14:40:00"
})
```

Define meta-knowledge relationships:

```cypher
// Sample meta-knowledge relationships

(:Session)-[:INCLUDED]->(:Search)  // Session INCLUDED flight search
(:Session)-[:ESTABLISHED]->(:UserPreference)  // Session ESTABLISHED cabin_class preference
(:Search)-[:CONCERNING]->(:Destination)  // Search CONCERNING Paris
(:Search)-[:FOLLOWED_BY]->(:Search)  // Flight search FOLLOWED_BY hotel search
```

### 2.3 Neo4j Python Driver Integration

#### Implementation

1. **Install Neo4j Python Driver**:

   ```bash
   uv pip install neo4j
   ```

2. **Create Connection Manager**:

   ```python
   # src/db/providers/neo4j_provider.py
   import os
   import logging
   from neo4j import GraphDatabase
   from typing import Dict, List, Any, Optional

   logger = logging.getLogger(__name__)

   class Neo4jProvider:
       """Provider for Neo4j graph database operations."""

       def __init__(self, uri: Optional[str] = None, user: Optional[str] = None,
                   password: Optional[str] = None):
           """Initialize Neo4j connection."""
           self._uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
           self._user = user or os.environ.get("NEO4J_USER", "neo4j")
           self._password = password or os.environ.get("NEO4J_PASSWORD", "password")
           self._driver = None
           self._connect()

       def _connect(self) -> None:
           """Establish connection to Neo4j."""
           try:
               self._driver = GraphDatabase.driver(
                   self._uri,
                   auth=(self._user, self._password)
               )
               # Verify connection
               with self._driver.session() as session:
                   result = session.run("RETURN 1 AS test")
                   test_value = result.single()["test"]
                   if test_value != 1:
                       raise Exception("Connection test failed")
               logger.info(f"Connected to Neo4j at {self._uri}")
           except Exception as e:
               logger.error(f"Failed to connect to Neo4j: {str(e)}")
               raise

       def close(self) -> None:
           """Close Neo4j connection."""
           if self._driver:
               self._driver.close()
               logger.info("Neo4j connection closed")

       def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
           """Execute Cypher query and return results."""
           if not self._driver:
               self._connect()

           try:
               with self._driver.session() as session:
                   result = session.run(query, parameters or {})
                   return [dict(record) for record in result]
           except Exception as e:
               logger.error(f"Neo4j query error: {str(e)} - Query: {query}")
               raise

       def create_entity(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
           """Create a new entity node."""
           query = f"""
           CREATE (n:{label} $properties)
           RETURN n
           """
           result = self.execute_query(query, {"properties": properties})
           return result[0]["n"] if result else None

       def create_relationship(self,
                             from_label: str, from_property: str, from_value: Any,
                             to_label: str, to_property: str, to_value: Any,
                             rel_type: str, rel_properties: Dict[str, Any] = None) -> Dict[str, Any]:
           """Create a relationship between two nodes."""
           query = f"""
           MATCH (a:{from_label}), (b:{to_label})
           WHERE a.{from_property} = $from_value AND b.{to_property} = $to_value
           CREATE (a)-[r:{rel_type} $rel_properties]->(b)
           RETURN a, r, b
           """
           result = self.execute_query(query, {
               "from_value": from_value,
               "to_value": to_value,
               "rel_properties": rel_properties or {}
           })
           return result[0] if result else None

       def find_entities(self, label: str, properties: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
           """Find entities matching criteria."""
           where_clause = " AND ".join([f"n.{k} = ${k}" for k in (properties or {}).keys()])
           query = f"""
           MATCH (n:{label})
           {f"WHERE {where_clause}" if where_clause else ""}
           RETURN n
           LIMIT {limit}
           """
           result = self.execute_query(query, properties or {})
           return [record["n"] for record in result]

       def find_relationships(self,
                             from_label: str = None, from_property: str = None, from_value: Any = None,
                             to_label: str = None, to_property: str = None, to_value: Any = None,
                             rel_type: str = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
           """Find relationships matching criteria."""
           # Build match clause
           from_clause = f"(a:{from_label})" if from_label else "(a)"
           to_clause = f"(b:{to_label})" if to_label else "(b)"
           rel_clause = f"[r:{rel_type}]" if rel_type else "[r]"

           # Build where clause
           where_conditions = []
           params = {}

           if from_property and from_value is not None:
               where_conditions.append(f"a.{from_property} = $from_value")
               params["from_value"] = from_value

           if to_property and to_value is not None:
               where_conditions.append(f"b.{to_property} = $to_value")
               params["to_value"] = to_value

           where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

           query = f"""
           MATCH {from_clause}-{rel_clause}->{to_clause}
           {where_clause}
           RETURN a, r, b
           LIMIT {limit}
           """

           return self.execute_query(query, params)
   ```

3. **Create Repository Layer**:

   ```python
   # src/db/repositories/knowledge_graph_repository.py
   from typing import Dict, List, Any, Optional
   from src.db.providers.neo4j_provider import Neo4jProvider

   class KnowledgeGraphRepository:
       """Repository for knowledge graph operations."""

       def __init__(self, provider: Optional[Neo4jProvider] = None):
           """Initialize repository with provider."""
           self.provider = provider or Neo4jProvider()

       def add_destination(self,
                         name: str,
                         country: str,
                         coordinates: Dict[str, float],
                         **kwargs) -> Dict[str, Any]:
           """Add a destination to the knowledge graph."""
           properties = {
               "name": name,
               "country": country,
               "coordinates": coordinates,
               **kwargs
           }
           return self.provider.create_entity("Destination", properties)

       def add_accommodation(self,
                           id: str,
                           name: str,
                           type: str,
                           destination_name: str,
                           **kwargs) -> Dict[str, Any]:
           """Add an accommodation with relationship to destination."""
           # Create accommodation
           properties = {
               "id": id,
               "name": name,
               "type": type,
               **kwargs
           }
           accommodation = self.provider.create_entity("Accommodation", properties)

           # Create relationship to destination
           self.provider.create_relationship(
               from_label="Accommodation", from_property="id", from_value=id,
               to_label="Destination", to_property="name", to_value=destination_name,
               rel_type="LOCATED_IN"
           )

           return accommodation

       def add_user_preference(self,
                             user_id: str,
                             preference_type: str,
                             value: Any,
                             strength: float = 0.5) -> Dict[str, Any]:
           """Add or update a user preference."""
           # Check if preference exists
           query = """
           MATCH (u:User {id: $user_id})-[r:PREFERS]->(p:UserPreference {preference_type: $preference_type})
           RETURN p
           """
           result = self.provider.execute_query(query, {
               "user_id": user_id,
               "preference_type": preference_type
           })

           if result:
               # Update existing preference
               query = """
               MATCH (u:User {id: $user_id})-[r:PREFERS]->(p:UserPreference {preference_type: $preference_type})
               SET p.value = $value, p.strength = $strength, p.last_updated = datetime()
               RETURN p
               """
               result = self.provider.execute_query(query, {
                   "user_id": user_id,
                   "preference_type": preference_type,
                   "value": value,
                   "strength": strength
               })
               return result[0]["p"] if result else None
           else:
               # Create new preference
               # First ensure user exists
               user_nodes = self.provider.find_entities("User", {"id": user_id})
               if not user_nodes:
                   self.provider.create_entity("User", {"id": user_id})

               # Create preference node
               pref = self.provider.create_entity("UserPreference", {
                   "preference_type": preference_type,
                   "value": value,
                   "strength": strength,
                   "last_updated": "datetime()"
               })

               # Create relationship
               self.provider.create_relationship(
                   from_label="User", from_property="id", from_value=user_id,
                   to_label="UserPreference", to_property="preference_type", to_value=preference_type,
                   rel_type="PREFERS"
               )

               return pref

       def get_user_preferences(self, user_id: str) -> List[Dict[str, Any]]:
           """Get all preferences for a user."""
           query = """
           MATCH (u:User {id: $user_id})-[r:PREFERS]->(p:UserPreference)
           RETURN p
           """
           result = self.provider.execute_query(query, {"user_id": user_id})
           return [record["p"] for record in result]

       def record_search(self,
                       user_id: str,
                       session_id: str,
                       query_type: str,
                       parameters: Dict[str, Any]) -> Dict[str, Any]:
           """Record a search in the knowledge graph."""
           # Create search node
           search_id = f"search_{session_id}_{query_type}_{hash(str(parameters))}"
           search = self.provider.create_entity("Search", {
               "id": search_id,
               "query_type": query_type,
               "parameters": parameters,
               "timestamp": "datetime()",
               "result_count": parameters.get("result_count", 0)
           })

           # Ensure session exists
           session_nodes = self.provider.find_entities("Session", {"id": session_id})
           if not session_nodes:
               self.provider.create_entity("Session", {
                   "id": session_id,
                   "user_id": user_id,
                   "start_time": "datetime()"
               })

           # Create relationship
           self.provider.create_relationship(
               from_label="Session", from_property="id", from_value=session_id,
               to_label="Search", to_property="id", to_value=search_id,
               rel_type="INCLUDED"
           )

           return search

       def get_destination_recommendations(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
           """Get destination recommendations based on user preferences and history."""
           query = """
           // Find destinations similar to those the user has shown interest in
           MATCH (u:User {id: $user_id})-[:PLANNED]->(:Trip)-[:INCLUDES]->(d:Destination)
           MATCH (d)-[:NEAR_TO]->(rec:Destination)
           WHERE NOT (u)-[:PLANNED]->(:Trip)-[:INCLUDES]->(rec)

           // Consider user preferences
           OPTIONAL MATCH (u)-[:PREFERS]->(p:UserPreference)
           WHERE p.preference_type IN ['climate', 'region', 'activities']

           // Score recommendations
           WITH rec, count(DISTINCT d) AS similarity_score,
                collect(p.value) AS preferences

           // Calculate preference match
           WITH rec, similarity_score, preferences,
                CASE
                    WHEN rec.climate IN preferences THEN 1 ELSE 0
                END +
                CASE
                    WHEN rec.region IN preferences THEN 1 ELSE 0
                END +
                CASE
                    WHEN ANY(activity IN rec.activities WHERE activity IN preferences)
                    THEN 1 ELSE 0
                END AS preference_score

           RETURN rec,
                  similarity_score * 0.6 + preference_score * 0.4 AS recommendation_score
           ORDER BY recommendation_score DESC
           LIMIT $limit
           """

           result = self.provider.execute_query(query, {
               "user_id": user_id,
               "limit": limit
           })

           return [{
               "destination": record["rec"],
               "score": record["recommendation_score"]
           } for record in result]
   ```

### 2.4 Memory MCP Server Implementation

#### Server Structure

Create the Memory MCP Server using FastMCP 2.0:

```typescript
// src/mcp/memory/server.ts
import { FastMCP } from "fastmcp";
import {
  createEntities,
  createRelations,
  addObservations,
  deleteEntities,
  deleteObservations,
  deleteRelations,
  readGraph,
  searchNodes,
  openNodes,
} from "./tools";

// Create MCP server
const server = new FastMCP({
  name: "TripSage Memory MCP",
  version: "1.0.0",
  description: "Knowledge graph operations for TripSage travel planning",
});

// Register tools
server.registerTool(createEntities);
server.registerTool(createRelations);
server.registerTool(addObservations);
server.registerTool(deleteEntities);
server.registerTool(deleteObservations);
server.registerTool(deleteRelations);
server.registerTool(readGraph);
server.registerTool(searchNodes);
server.registerTool(openNodes);

// Start the server
server.start();
```

Implement the tool definitions:

```typescript
// src/mcp/memory/tools/create_entities.ts
import { createTool } from "fastmcp";
import { z } from "zod";
import { Neo4jService } from "../services/neo4j_service";

export const createEntities = createTool({
  name: "create_entities",
  description: "Create multiple new entities in the knowledge graph",

  input: z.object({
    entities: z.array(
      z.object({
        name: z.string().min(1),
        entityType: z.string().min(1),
        observations: z.array(z.string()),
      })
    ),
  }),

  handler: async ({ input, context }) => {
    const neo4jService = new Neo4jService();

    try {
      const results = await neo4jService.createEntities(input.entities);

      return {
        created: results.length,
        entities: results.map((entity) => ({
          name: entity.name,
          type: entity.entityType,
        })),
      };
    } catch (error) {
      await context.error(`Error creating entities: ${error.message}`);
      throw error;
    }
  },
});
```

```typescript
// src/mcp/memory/tools/create_relations.ts
import { createTool } from "fastmcp";
import { z } from "zod";
import { Neo4jService } from "../services/neo4j_service";

export const createRelations = createTool({
  name: "create_relations",
  description:
    "Create multiple new relations between entities in the knowledge graph",

  input: z.object({
    relations: z.array(
      z.object({
        from: z.string().min(1),
        relationType: z.string().min(1),
        to: z.string().min(1),
      })
    ),
  }),

  handler: async ({ input, context }) => {
    const neo4jService = new Neo4jService();

    try {
      const results = await neo4jService.createRelations(input.relations);

      return {
        created: results.length,
        relations: results.map((relation) => ({
          from: relation.from,
          type: relation.relationType,
          to: relation.to,
        })),
      };
    } catch (error) {
      await context.error(`Error creating relations: ${error.message}`);
      throw error;
    }
  },
});
```

Implement the Neo4j service:

```typescript
// src/mcp/memory/services/neo4j_service.ts
import neo4j from "neo4j-driver";
import { config } from "../config";

export class Neo4jService {
  private driver: neo4j.Driver;

  constructor() {
    this.driver = neo4j.driver(
      config.NEO4J_URI,
      neo4j.auth.basic(config.NEO4J_USER, config.NEO4J_PASSWORD)
    );
  }

  async close() {
    await this.driver.close();
  }

  async createEntities(entities) {
    const session = this.driver.session();
    const results = [];

    try {
      for (const entity of entities) {
        const result = await session.run(
          `
          MERGE (e:${entity.entityType} {name: $name})
          ON CREATE SET e.created = datetime()
          ON MATCH SET e.updated = datetime()
          WITH e
          
          UNWIND $observations as observation
          CREATE (o:Observation {content: observation, timestamp: datetime()})
          CREATE (e)-[:HAS_OBSERVATION]->(o)
          
          RETURN e {.*, type: labels(e)[0]} as entity
          `,
          {
            name: entity.name,
            observations: entity.observations,
          }
        );

        if (result.records.length > 0) {
          results.push(result.records[0].get("entity"));
        }
      }

      return results;
    } finally {
      await session.close();
    }
  }

  async createRelations(relations) {
    const session = this.driver.session();
    const results = [];

    try {
      for (const relation of relations) {
        const result = await session.run(
          `
          MATCH (a {name: $fromName})
          MATCH (b {name: $toName})
          WHERE any(label IN labels(a) WHERE label <> 'Observation')
          AND any(label IN labels(b) WHERE label <> 'Observation')
          CREATE (a)-[r:${relation.relationType} {created: datetime()}]->(b)
          RETURN a.name as from, type(r) as relationType, b.name as to
          `,
          {
            fromName: relation.from,
            toName: relation.to,
          }
        );

        if (result.records.length > 0) {
          const record = result.records[0];
          results.push({
            from: record.get("from"),
            relationType: record.get("relationType"),
            to: record.get("to"),
          });
        }
      }

      return results;
    } finally {
      await session.close();
    }
  }

  // Additional methods for other operations...
}
```

#### Python Client Implementation

```python
# src/mcp/memory/client.py
from typing import List, Dict, Any, Optional
from src.mcp.base_mcp_client import BaseMCPClient
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class MemoryClient(BaseMCPClient):
    """Client for the Memory MCP Server."""

    def __init__(self):
        """Initialize the Memory MCP client."""
        super().__init__(server_name="memory")
        logger.info("Initialized Memory MCP Client")

    async def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple entities in the knowledge graph.

        Args:
            entities: List of entity objects, each with name, entityType, and observations

        Returns:
            Dictionary with creation results
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "create_entities",
                {"entities": entities}
            )
            return result
        except Exception as e:
            logger.error(f"Error creating entities: {str(e)}")
            return {"error": str(e), "created": 0, "entities": []}

    async def create_relations(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple relations between entities.

        Args:
            relations: List of relation objects, each with from, relationType, and to

        Returns:
            Dictionary with creation results
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "create_relations",
                {"relations": relations}
            )
            return result
        except Exception as e:
            logger.error(f"Error creating relations: {str(e)}")
            return {"error": str(e), "created": 0, "relations": []}

    async def add_observations(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add observations to existing entities.

        Args:
            observations: List of observation objects, each with entityName and contents

        Returns:
            Dictionary with addition results
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "add_observations",
                {"observations": observations}
            )
            return result
        except Exception as e:
            logger.error(f"Error adding observations: {str(e)}")
            return {"error": str(e), "added": 0, "observations": []}

    async def search_nodes(self, query: str) -> List[Dict[str, Any]]:
        """Search for nodes in the knowledge graph.

        Args:
            query: Search query string

        Returns:
            List of matching nodes
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "search_nodes",
                {"query": query}
            )
            return result.get("nodes", [])
        except Exception as e:
            logger.error(f"Error searching nodes: {str(e)}")
            return []

    async def read_graph(self) -> Dict[str, Any]:
        """Read the entire knowledge graph.

        Returns:
            Dictionary with entities and relations
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool("read_graph", {})
            return result
        except Exception as e:
            logger.error(f"Error reading graph: {str(e)}")
            return {"entities": [], "relations": []}

    async def open_nodes(self, names: List[str]) -> List[Dict[str, Any]]:
        """Retrieve specific nodes by name.

        Args:
            names: List of entity names to retrieve

        Returns:
            List of node objects
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "open_nodes",
                {"names": names}
            )
            return result.get("nodes", [])
        except Exception as e:
            logger.error(f"Error opening nodes: {str(e)}")
            return []
```

### 2.5 Data Synchronization with Supabase

To maintain consistency between Supabase and Neo4j, implement a synchronization service:

```python
# src/db/services/graph_sync_service.py
import logging
import asyncio
from typing import Dict, List, Any, Optional
from src.db.repositories.trip_repository import TripRepository
from src.db.repositories.knowledge_graph_repository import KnowledgeGraphRepository

logger = logging.getLogger(__name__)

class GraphSyncService:
    """Service for synchronizing data between Supabase and Neo4j."""

    def __init__(self):
        """Initialize repositories."""
        self.trip_repo = TripRepository()
        self.graph_repo = KnowledgeGraphRepository()

    async def sync_trip(self, trip_id: str) -> bool:
        """Synchronize a trip and its related entities to Neo4j.

        Args:
            trip_id: ID of the trip to synchronize

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get trip with related entities
            trip = await self.trip_repo.get_trip_with_details(trip_id)
            if not trip:
                logger.warning(f"Trip {trip_id} not found")
                return False

            # Sync trip
            self.graph_repo.add_trip(
                id=trip.id,
                user_id=trip.user_id,
                name=trip.title,
                start_date=trip.start_date.isoformat(),
                end_date=trip.end_date.isoformat(),
                budget=float(trip.budget),
                status=trip.status
            )

            # Sync destinations
            for destination in trip.destinations:
                self.graph_repo.add_destination(
                    name=destination.name,
                    country=destination.country,
                    coordinates={
                        "latitude": destination.latitude,
                        "longitude": destination.longitude
                    },
                    region=destination.region
                )

                # Connect trip to destination
                self.graph_repo.provider.create_relationship(
                    from_label="Trip", from_property="id", from_value=trip.id,
                    to_label="Destination", to_property="name", to_value=destination.name,
                    rel_type="INCLUDES"
                )

            # Sync accommodations
            for accommodation in trip.accommodations:
                self.graph_repo.add_accommodation(
                    id=accommodation.id,
                    name=accommodation.name,
                    type=accommodation.type,
                    destination_name=accommodation.location,
                    rating=accommodation.rating,
                    price=float(accommodation.price)
                )

                # Connect trip to accommodation
                self.graph_repo.provider.create_relationship(
                    from_label="Trip", from_property="id", from_value=trip.id,
                    to_label="Accommodation", to_property="id", to_value=accommodation.id,
                    rel_type="INCLUDES"
                )

            # Sync flights
            for flight in trip.flights:
                # Ensure airports exist
                for airport_code in [flight.origin, flight.destination]:
                    airport_nodes = self.graph_repo.provider.find_entities(
                        "Airport", {"iata_code": airport_code}
                    )
                    if not airport_nodes:
                        self.graph_repo.provider.create_entity("Airport", {
                            "iata_code": airport_code
                        })

                # Create route if needed
                route_id = f"{flight.origin}-{flight.destination}"
                route_nodes = self.graph_repo.provider.find_entities(
                    "Route", {"id": route_id}
                )
                if not route_nodes:
                    self.graph_repo.provider.create_entity("Route", {
                        "id": route_id,
                        "origin": flight.origin,
                        "destination": flight.destination
                    })

                    # Connect airports to route
                    self.graph_repo.provider.create_relationship(
                        from_label="Route", from_property="id", from_value=route_id,
                        to_label="Airport", to_property="iata_code", to_value=flight.origin,
                        rel_type="CONNECTS",
                        rel_properties={"role": "origin"}
                    )

                    self.graph_repo.provider.create_relationship(
                        from_label="Route", from_property="id", from_value=route_id,
                        to_label="Airport", to_property="iata_code", to_value=flight.destination,
                        rel_type="CONNECTS",
                        rel_properties={"role": "destination"}
                    )

                # Connect trip to route with flight details
                self.graph_repo.provider.create_relationship(
                    from_label="Trip", from_property="id", from_value=trip.id,
                    to_label="Route", to_property="id", to_value=route_id,
                    rel_type="INCLUDES",
                    rel_properties={
                        "flight_number": flight.flight_number,
                        "airline": flight.airline,
                        "departure_time": flight.departure_time.isoformat(),
                        "arrival_time": flight.arrival_time.isoformat(),
                        "price": float(flight.price),
                        "status": flight.status
                    }
                )

            logger.info(f"Successfully synchronized trip {trip_id} to knowledge graph")
            return True

        except Exception as e:
            logger.error(f"Error synchronizing trip {trip_id} to Neo4j: {str(e)}")
            return False

    async def sync_all_trips(self) -> Dict[str, Any]:
        """Synchronize all trips to Neo4j.

        Returns:
            Dictionary with sync results
        """
        try:
            # Get all trip IDs
            trip_ids = await self.trip_repo.get_all_trip_ids()

            # Track results
            results = {
                "total": len(trip_ids),
                "success": 0,
                "failed": 0,
                "failed_ids": []
            }

            # Sync each trip
            for trip_id in trip_ids:
                success = await self.sync_trip(trip_id)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["failed_ids"].append(trip_id)

            logger.info(f"Completed sync of all trips: {results}")
            return results

        except Exception as e:
            logger.error(f"Error in sync_all_trips: {str(e)}")
            return {
                "error": str(e),
                "total": 0,
                "success": 0,
                "failed": 0
            }

    async def setup_sync_webhook(self) -> bool:
        """Set up Supabase webhook for real-time syncing.

        Returns:
            True if successful, False otherwise
        """
        # Implementation depends on Supabase client setup
        # This would typically create a webhook subscription
        # that calls a serverless function when data changes
        pass
```

### 2.6 Integration with Agent Architecture

Integrate the Memory MCP client with the TripSage agent architecture:

```python
# src/agents/travel_agent.py
from src.mcp.memory.client import MemoryClient
from src.mcp.flights.client import FlightsMCPClient
from src.mcp.accommodations.client import AccommodationsMCPClient
from src.mcp.weather.client import WeatherMCPClient
from src.utils.logging import get_module_logger
from src.agents.base_agent import BaseAgent

logger = get_module_logger(__name__)

class TravelAgent(BaseAgent):
    """Agent for travel planning with knowledge graph integration."""

    def __init__(self):
        """Initialize TravelAgent with MCP clients."""
        super().__init__(
            name="TripSage Travel Agent",
            instructions="You are a comprehensive travel planning assistant that helps users find flights, accommodations, and activities. Use your tools to search for travel options, provide recommendations, and create detailed itineraries. Learn from user preferences and leverage the knowledge graph to provide personalized suggestions."
        )

        # Initialize MCP clients
        self.memory_client = MemoryClient()
        self.flights_client = FlightsMCPClient()
        self.accommodations_client = AccommodationsMCPClient()
        self.weather_client = WeatherMCPClient()

        # Register MCP tools
        self._register_mcp_client_tools()

    def _register_mcp_client_tools(self):
        """Register all MCP client tools."""
        # Register Memory MCP tools
        self.register_tool(self.memory_client.create_entities)
        self.register_tool(self.memory_client.create_relations)
        self.register_tool(self.memory_client.add_observations)
        self.register_tool(self.memory_client.search_nodes)
        self.register_tool(self.memory_client.read_graph)
        self.register_tool(self.memory_client.open_nodes)

        # Register other MCP tools
        self.register_tool(self.flights_client.search_flights)
        self.register_tool(self.accommodations_client.search_accommodations)
        self.register_tool(self.weather_client.get_forecast)

    async def start_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Start a new session with context from knowledge graph.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            Session context dictionary
        """
        try:
            # Get user context from knowledge graph
            user_nodes = await self.memory_client.open_nodes([user_id])
            user_preferences = []

            if user_nodes:
                # Get user preferences
                query = f"user:{user_id} preference"
                user_preferences = await self.memory_client.search_nodes(query)

                # Get recent destinations
                query = f"user:{user_id} destination"
                recent_destinations = await self.memory_client.search_nodes(query)

                # Record session start in knowledge graph
                await self.memory_client.create_entities([{
                    "name": session_id,
                    "entityType": "Session",
                    "observations": [
                        f"Started by user {user_id}",
                        f"Start time: {datetime.now().isoformat()}"
                    ]
                }])

                # Create relation between user and session
                await self.memory_client.create_relations([{
                    "from": user_id,
                    "relationType": "STARTED",
                    "to": session_id
                }])
            else:
                # Create new user in knowledge graph
                await self.memory_client.create_entities([{
                    "name": user_id,
                    "entityType": "User",
                    "observations": [
                        "New user",
                        f"Created: {datetime.now().isoformat()}"
                    ]
                }])

                # Create session
                await self.memory_client.create_entities([{
                    "name": session_id,
                    "entityType": "Session",
                    "observations": [
                        f"Started by new user {user_id}",
                        f"Start time: {datetime.now().isoformat()}"
                    ]
                }])

                # Create relation between user and session
                await self.memory_client.create_relations([{
                    "from": user_id,
                    "relationType": "STARTED",
                    "to": session_id
                }])

            return {
                "user_id": user_id,
                "session_id": session_id,
                "preferences": user_preferences,
                "is_new_user": len(user_nodes) == 0
            }

        except Exception as e:
            logger.error(f"Error starting session: {str(e)}")
            return {
                "user_id": user_id,
                "session_id": session_id,
                "error": str(e)
            }

    async def end_session(self, user_id: str, session_id: str) -> bool:
        """End a session and update knowledge graph.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update session node with end time
            await self.memory_client.add_observations([{
                "entityName": session_id,
                "contents": [
                    f"Ended at {datetime.now().isoformat()}"
                ]
            }])

            return True
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            return False

    async def record_search(self,
                         user_id: str,
                         session_id: str,
                         search_type: str,
                         parameters: Dict[str, Any],
                         results: Dict[str, Any]) -> bool:
        """Record a search in the knowledge graph.

        Args:
            user_id: User ID
            session_id: Session ID
            search_type: Type of search (flight, accommodation, etc.)
            parameters: Search parameters
            results: Search results

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create search entity
            search_id = f"search_{session_id}_{search_type}_{hash(str(parameters))}"

            await self.memory_client.create_entities([{
                "name": search_id,
                "entityType": "Search",
                "observations": [
                    f"Search type: {search_type}",
                    f"Parameters: {json.dumps(parameters)}",
                    f"Result count: {results.get('total_count', 0)}",
                    f"Timestamp: {datetime.now().isoformat()}"
                ]
            }])

            # Connect search to session
            await self.memory_client.create_relations([{
                "from": session_id,
                "relationType": "INCLUDED",
                "to": search_id
            }])

            # If destinations were searched, connect them
            if search_type == "accommodation" and "location" in parameters:
                destination = parameters["location"]

                # Check if destination exists
                destination_nodes = await self.memory_client.open_nodes([destination])

                if not destination_nodes:
                    # Create destination
                    await self.memory_client.create_entities([{
                        "name": destination,
                        "entityType": "Destination",
                        "observations": [
                            f"Added from search: {datetime.now().isoformat()}"
                        ]
                    }])

                # Connect search to destination
                await self.memory_client.create_relations([{
                    "from": search_id,
                    "relationType": "CONCERNING",
                    "to": destination
                }])

            return True
        except Exception as e:
            logger.error(f"Error recording search: {str(e)}")
            return False
```

## 3. Testing the Implementation

Create tests to verify the Neo4j integration:

```python
# tests/db/test_neo4j_provider.py
import pytest
from src.db.providers.neo4j_provider import Neo4jProvider

@pytest.fixture
def neo4j_provider():
    """Create a Neo4j provider for testing."""
    provider = Neo4jProvider(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )
    yield provider
    provider.close()

@pytest.mark.asyncio
async def test_create_entity(neo4j_provider):
    """Test creating an entity in Neo4j."""
    # Create test entity
    result = neo4j_provider.create_entity("TestNode", {
        "name": "test_entity",
        "value": "test_value"
    })

    # Verify creation
    assert result is not None
    assert result["name"] == "test_entity"
    assert result["value"] == "test_value"

    # Clean up
    neo4j_provider.execute_query("MATCH (n:TestNode {name: 'test_entity'}) DELETE n")

@pytest.mark.asyncio
async def test_create_relationship(neo4j_provider):
    """Test creating a relationship in Neo4j."""
    # Create test entities
    neo4j_provider.create_entity("TestNode", {
        "name": "source_node",
        "value": "source"
    })

    neo4j_provider.create_entity("TestNode", {
        "name": "target_node",
        "value": "target"
    })

    # Create relationship
    result = neo4j_provider.create_relationship(
        from_label="TestNode", from_property="name", from_value="source_node",
        to_label="TestNode", to_property="name", to_value="target_node",
        rel_type="TEST_REL", rel_properties={"prop": "test"}
    )

    # Verify creation
    assert result is not None
    assert result["a"]["name"] == "source_node"
    assert result["b"]["name"] == "target_node"
    assert result["r"]["prop"] == "test"

    # Clean up
    neo4j_provider.execute_query("""
    MATCH (a:TestNode {name: 'source_node'})-[r]-(b:TestNode {name: 'target_node'})
    DELETE a, r, b
    """)
```

```python
# tests/mcp/test_memory_client.py
import pytest
import uuid
from src.mcp.memory.client import MemoryClient

@pytest.fixture
def memory_client():
    """Create a memory client for testing."""
    return MemoryClient()

@pytest.mark.asyncio
async def test_create_entities(memory_client):
    """Test creating entities through the Memory MCP."""
    # Generate unique test names to avoid conflicts
    test_id = str(uuid.uuid4())
    entity_name = f"test_entity_{test_id}"

    # Create test entity
    result = await memory_client.create_entities([{
        "name": entity_name,
        "entityType": "TestNode",
        "observations": ["Test observation"]
    }])

    # Verify response
    assert "created" in result
    assert result["created"] >= 1
    assert "entities" in result

    # Verify entity was created
    entities = await memory_client.open_nodes([entity_name])
    assert len(entities) > 0
    assert entities[0]["name"] == entity_name

    # Clean up
    await memory_client.delete_entities({"entityNames": [entity_name]})

@pytest.mark.asyncio
async def test_create_relations(memory_client):
    """Test creating relations through the Memory MCP."""
    # Generate unique test names
    test_id = str(uuid.uuid4())
    source_name = f"source_{test_id}"
    target_name = f"target_{test_id}"

    # Create test entities
    await memory_client.create_entities([
        {
            "name": source_name,
            "entityType": "TestNode",
            "observations": ["Source node"]
        },
        {
            "name": target_name,
            "entityType": "TestNode",
            "observations": ["Target node"]
        }
    ])

    # Create relation
    result = await memory_client.create_relations([{
        "from": source_name,
        "relationType": "TEST_RELATION",
        "to": target_name
    }])

    # Verify response
    assert "created" in result
    assert result["created"] >= 1
    assert "relations" in result

    # Verify using graph read
    graph = await memory_client.read_graph()
    relation_found = False

    for relation in graph["relations"]:
        if (relation["from"] == source_name and
            relation["to"] == target_name and
            relation["type"] == "TEST_RELATION"):
            relation_found = True
            break

    assert relation_found

    # Clean up
    await memory_client.delete_entities({
        "entityNames": [source_name, target_name]
    })
```

## 4. Deployment Strategy

### 4.1 Docker Configuration

Create a Docker configuration for the Neo4j deployment:

```dockerfile
# Docker Compose for Neo4j deployment
version: '3.8'

services:
  neo4j:
    image: neo4j:5.13
    container_name: tripsage-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
      - neo4j-import:/import
      - neo4j-plugins:/plugins
      - ./neo4j/conf:/conf
    environment:
      - NEO4J_AUTH=neo4j/your-password
      - NEO4J_dbms_memory_heap_max__size=4G
      - NEO4J_dbms_memory_pagecache_size=2G
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*
    restart: unless-stopped
    networks:
      - tripsage-network

  memory-mcp:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    container_name: tripsage-memory-mcp
    ports:
      - "3005:3000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=your-password
      - PORT=3000
    depends_on:
      - neo4j
    restart: unless-stopped
    networks:
      - tripsage-network

volumes:
  neo4j-data:
  neo4j-logs:
  neo4j-import:
  neo4j-plugins:

networks:
  tripsage-network:
    driver: bridge
```

### 4.2 Environment Configuration

Add Neo4j environment variables to the project:

```bash
# Add to .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
MEMORY_MCP_ENDPOINT=http://localhost:3005
```

### 4.3 Monitoring Setup

Set up monitoring for Neo4j health:

```yaml
# prometheus/neo4j-monitoring.yml
scrape_configs:
  - job_name: "neo4j"
    scrape_interval: 15s
    metrics_path: /metrics
    scheme: http
    static_configs:
      - targets: ["neo4j:2004"] # Neo4j metrics endpoint
```

## 5. Conclusion and Next Steps

This implementation plan provides a detailed guide for setting up the Neo4j knowledge graph for TripSage. After completing these steps, the system will have a fully functional knowledge graph that integrates with the rest of the TripSage architecture.

### Next Steps

1. **Data Modeling**: Further refine the knowledge graph schema for specific travel domains
2. **Performance Optimization**: Implement indexing strategies for large-scale graphs
3. **Advanced Algorithms**: Leverage Neo4j graph algorithms for recommendations and pattern detection
4. **AI Integration**: Connect the knowledge graph to machine learning models for predictions
5. **Visualization**: Develop tools for visualizing the knowledge graph for debugging and analytics

### Potential Enhancements

- Implement graph-based personalization algorithms
- Create hierarchical knowledge structures for complex travel patterns
- Develop temporal analysis for seasonal travel trends
- Implement automated knowledge acquisition from public travel datasets
