# Memory MCP Server Implementation Guide

This document provides a comprehensive implementation guide for the Memory MCP Server in the TripSage system, which serves as the interface to the Neo4j knowledge graph database.

## Table of Contents

- [Memory MCP Server Implementation Guide](#memory-mcp-server-implementation-guide)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Prerequisites](#prerequisites)
  - [Implementation Steps](#implementation-steps)
    - [1. Server Structure](#1-server-structure)
    - [2. Neo4j Client Implementation](#2-neo4j-client-implementation)
    - [3. Entity Management Tools](#3-entity-management-tools)
    - [4. Relationship Management Tools](#4-relationship-management-tools)
    - [5. Query and Search Tools](#5-query-and-search-tools)
    - [6. Session Persistence Implementation](#6-session-persistence-implementation)
  - [Integration with TripSage](#integration-with-tripsage)
    - [Client Usage Examples](#client-usage-examples)
      - [1. Travel Planning Agent Integration](#1-travel-planning-agent-integration)
      - [2. Capturing Travel History for Personalization](#2-capturing-travel-history-for-personalization)
      - [3. Using Knowledge Graph for Recommendations](#3-using-knowledge-graph-for-recommendations)
  - [Testing Strategy](#testing-strategy)
    - [Unit Testing for Neo4j Client](#unit-testing-for-neo4j-client)
    - [Integration Testing for Memory MCP Server](#integration-testing-for-memory-mcp-server)
  - [Deployment](#deployment)
    - [Docker Configuration](#docker-configuration)
    - [Environment Variables](#environment-variables)
    - [Startup Script](#startup-script)
    - [Docker Compose Integration](#docker-compose-integration)

## Overview

The Memory MCP Server is a critical component of the TripSage dual-storage architecture, responsible for managing the Neo4j knowledge graph. This graph stores travel-related information with rich semantic relationships as well as session-persistent data that enhances personalization across user interactions.

Key capabilities include:

- Creating and managing travel entities (destinations, accommodations, etc.)
- Establishing and querying semantic relationships between entities
- Persisting knowledge across sessions for personalized recommendations
- Supporting complex traversal queries for advanced travel insights

## Prerequisites

- Neo4j database instance (either Neo4j Desktop for development or Neo4j AuraDB for production)
- Python 3.9+ environment with `uv` for package management
- FastMCP 2.0 for MCP server implementation
- Proper configuration in environment variables or config files

## Implementation Steps

### 1. Server Structure

Create the basic Memory MCP Server structure following the TripSage FastMCP 2.0 pattern.

```python
# /src/mcp/memory/server.py
"""
Memory MCP Server for managing knowledge graph operations in TripSage.
"""

from typing import Dict, List, Any, Optional
from fastmcp import FastMCP, Context

from ..base_mcp_server import BaseMCPServer
from .client import Neo4jClient

class MemoryMCPServer(BaseMCPServer):
    """MCP Server for Neo4j knowledge graph operations."""

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        host: str = "0.0.0.0",
        port: int = 3004,
    ):
        """Initialize the Memory MCP Server.

        Args:
            neo4j_uri: Neo4j database URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            host: Host to bind the server to
            port: Port to listen on
        """
        super().__init__(
            name="Memory",
            description="Knowledge graph operations for travel information",
            version="1.0.0",
            host=host,
            port=port,
        )

        # Initialize Neo4j client
        self.neo4j_client = Neo4jClient(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password
        )

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all Memory MCP tools."""
        # Entity management tools
        self.tool(name="create_entities", description="Create multiple new entities in the knowledge graph")(self.create_entities)
        self.tool(name="delete_entities", description="Delete multiple entities and their associated relations")(self.delete_entities)
        self.tool(name="add_observations", description="Add new observations to existing entities")(self.add_observations)
        self.tool(name="delete_observations", description="Delete specific observations from entities")(self.delete_observations)

        # Relationship management tools
        self.tool(name="create_relations", description="Create multiple new relations between entities")(self.create_relations)
        self.tool(name="delete_relations", description="Delete multiple relations from the knowledge graph")(self.delete_relations)

        # Query and search tools
        self.tool(name="read_graph", description="Read the entire knowledge graph")(self.read_graph)
        self.tool(name="search_nodes", description="Search for nodes in the knowledge graph based on a query")(self.search_nodes)
        self.tool(name="open_nodes", description="Open specific nodes in the knowledge graph by their names")(self.open_nodes)
```

### 2. Neo4j Client Implementation

Create a dedicated Neo4j client to handle database interactions.

```python
# /src/mcp/memory/client.py
"""
Neo4j client for Memory MCP Server.
"""

from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase
import logging

from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger

logger = get_module_logger(__name__)

class Neo4jClient:
    """Client for interacting with Neo4j database."""

    def __init__(self, uri: str, user: str, password: str):
        """Initialize the Neo4j client.

        Args:
            uri: Neo4j database URI
            user: Neo4j username
            password: Neo4j password
        """
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = GraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password)
        )

        logger.info("Initialized Neo4j client for %s", uri)

    def close(self):
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            logger.debug("Closed Neo4j driver connection")

    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query against the Neo4j database.

        Args:
            query: Cypher query to execute
            parameters: Query parameters

        Returns:
            List of records from the query result

        Raises:
            MCPError: If the query fails
        """
        try:
            with self._driver.session() as session:
                result = session.run(query, parameters or {})
                # Convert Neo4j records to dictionaries
                return [dict(record) for record in result]
        except Exception as e:
            logger.error("Neo4j query failed: %s", str(e))
            raise MCPError(
                message=f"Neo4j query failed: {str(e)}",
                server="neo4j",
                tool="execute_query",
                params={"query": query}
            ) from e

class MemoryClient:
    """Client for the Memory MCP Server."""

    def __init__(self, endpoint: str, api_key: Optional[str] = None):
        """Initialize the Memory MCP client.

        Args:
            endpoint: MCP server endpoint
            api_key: API key for authentication (if required)
        """
        from ..base_mcp_client import BaseMCPClient

        self.client = BaseMCPClient(
            endpoint=endpoint,
            api_key=api_key,
            timeout=120.0,  # Neo4j operations might take longer
            use_cache=True,
            cache_ttl=300,  # 5 minutes cache for most operations
        )

    async def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple entities in the knowledge graph.

        Args:
            entities: List of entity dictionaries, each with name, entityType, and observations

        Returns:
            Result from the operation
        """
        return await self.client.call_tool("create_entities", {"entities": entities})

    async def create_relations(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple relations in the knowledge graph.

        Args:
            relations: List of relation dictionaries, each with from, relationType, and to

        Returns:
            Result from the operation
        """
        return await self.client.call_tool("create_relations", {"relations": relations})

    async def add_observations(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add observations to existing entities.

        Args:
            observations: List of observation dictionaries, each with entityName and contents

        Returns:
            Result from the operation
        """
        return await self.client.call_tool("add_observations", {"observations": observations})

    async def search_nodes(self, query: str) -> List[Dict[str, Any]]:
        """Search for nodes in the knowledge graph.

        Args:
            query: Search query string

        Returns:
            List of matching nodes
        """
        result = await self.client.call_tool("search_nodes", {"query": query})
        return result.get("nodes", [])

    async def open_nodes(self, names: List[str]) -> List[Dict[str, Any]]:
        """Get detailed information about specific nodes.

        Args:
            names: List of node names to retrieve

        Returns:
            List of node details
        """
        result = await self.client.call_tool("open_nodes", {"names": names})
        return result.get("nodes", [])

    async def read_graph(self) -> Dict[str, Any]:
        """Read the entire knowledge graph.

        Returns:
            Knowledge graph data with entities and relations
        """
        return await self.client.call_tool("read_graph", {})
```

### 3. Entity Management Tools

Implement tools for creating, updating, and deleting entities.

```python
# Add these methods to the MemoryMCPServer class

from pydantic import BaseModel, Field
from typing import List, Optional

class Entity(BaseModel):
    name: str = Field(..., description="The name of the entity")
    entityType: str = Field(..., description="The type of the entity")
    observations: List[str] = Field(default_factory=list, description="An array of observation contents associated with the entity")

class EntityCreationParams(BaseModel):
    entities: List[Entity] = Field(..., description="An array of entities to create")

class EntityDeletionParams(BaseModel):
    entityNames: List[str] = Field(..., description="An array of entity names to delete")

class Observation(BaseModel):
    entityName: str = Field(..., description="The name of the entity to add observations to")
    contents: List[str] = Field(..., description="An array of observation contents to add")

class ObservationAddParams(BaseModel):
    observations: List[Observation] = Field(..., description="An array of observations to add")

class ObservationDeletion(BaseModel):
    entityName: str = Field(..., description="The name of the entity containing the observations")
    observations: List[str] = Field(..., description="An array of observations to delete")

class ObservationDeletionParams(BaseModel):
    deletions: List[ObservationDeletion] = Field(..., description="An array of observation deletions")

async def create_entities(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Create multiple new entities in the knowledge graph.

    Args:
        params: Entity creation parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing created entity IDs
    """
    await ctx.info(f"Creating {len(params['entities'])} entities")

    # Validate params
    validated_params = EntityCreationParams(**params)

    # Process each entity
    created_entities = []

    for idx, entity in enumerate(validated_params.entities):
        # Report progress
        await ctx.report_progress(idx / len(validated_params.entities), f"Creating entity: {entity.name}")

        # Create Cypher query for entity creation
        query = """
        MERGE (e:`Entity` {name: $name})
        SET e.type = $entityType,
            e.created_at = datetime(),
            e.updated_at = datetime()
        RETURN e
        """

        # Execute query
        result = await self.neo4j_client.execute_query(
            query=query,
            parameters={
                "name": entity.name,
                "entityType": entity.entityType,
            }
        )

        # Process observations if any
        if entity.observations:
            # Add observations to the entity
            await self._add_observations_to_entity(entity.name, entity.observations)

        created_entities.append(entity.name)

    await ctx.report_progress(1.0, "Entity creation completed")

    return {
        "created": created_entities,
        "count": len(created_entities)
    }

async def _add_observations_to_entity(self, entity_name: str, observations: List[str]) -> None:
    """Add observations to an entity.

    Args:
        entity_name: Name of the entity
        observations: List of observation strings
    """
    # Create Cypher query for adding observations
    query = """
    MATCH (e:`Entity` {name: $entityName})
    WITH e
    UNWIND $observations as obs
    MERGE (o:`Observation` {content: obs})
    MERGE (e)-[:HAS_OBSERVATION]->(o)
    SET o.created_at = datetime()
    """

    await self.neo4j_client.execute_query(
        query=query,
        parameters={
            "entityName": entity_name,
            "observations": observations
        }
    )

async def delete_entities(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Delete multiple entities and their associated relations.

    Args:
        params: Entity deletion parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing deleted entity names
    """
    await ctx.info(f"Deleting {len(params['entityNames'])} entities")

    # Validate params
    validated_params = EntityDeletionParams(**params)

    # Process each entity
    for idx, entity_name in enumerate(validated_params.entityNames):
        # Report progress
        await ctx.report_progress(idx / len(validated_params.entityNames), f"Deleting entity: {entity_name}")

        # Create Cypher query for entity deletion
        query = """
        MATCH (e:`Entity` {name: $name})
        OPTIONAL MATCH (e)-[r]-()
        DELETE r, e
        """

        # Execute query
        await self.neo4j_client.execute_query(
            query=query,
            parameters={"name": entity_name}
        )

    await ctx.report_progress(1.0, "Entity deletion completed")

    return {
        "deleted": validated_params.entityNames,
        "count": len(validated_params.entityNames)
    }

async def add_observations(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Add new observations to existing entities.

    Args:
        params: Observation addition parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing updated entity names
    """
    await ctx.info(f"Adding observations to {len(params['observations'])} entities")

    # Validate params
    validated_params = ObservationAddParams(**params)

    # Process each observation set
    updated_entities = []

    for idx, obs in enumerate(validated_params.observations):
        # Report progress
        await ctx.report_progress(idx / len(validated_params.observations), f"Adding observations to: {obs.entityName}")

        # Add observations
        await self._add_observations_to_entity(obs.entityName, obs.contents)

        updated_entities.append(obs.entityName)

    await ctx.report_progress(1.0, "Observation addition completed")

    return {
        "updated": updated_entities,
        "count": len(updated_entities)
    }

async def delete_observations(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Delete specific observations from entities.

    Args:
        params: Observation deletion parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing affected entity names
    """
    await ctx.info(f"Deleting observations from {len(params['deletions'])} entities")

    # Validate params
    validated_params = ObservationDeletionParams(**params)

    # Process each deletion
    affected_entities = []

    for idx, deletion in enumerate(validated_params.deletions):
        # Report progress
        await ctx.report_progress(idx / len(validated_params.deletions), f"Deleting observations from: {deletion.entityName}")

        # Create Cypher query for deleting observations
        query = """
        MATCH (e:`Entity` {name: $entityName})-[r:HAS_OBSERVATION]->(o:`Observation`)
        WHERE o.content IN $observations
        DELETE r, o
        """

        # Execute query
        await self.neo4j_client.execute_query(
            query=query,
            parameters={
                "entityName": deletion.entityName,
                "observations": deletion.observations
            }
        )

        affected_entities.append(deletion.entityName)

    await ctx.report_progress(1.0, "Observation deletion completed")

    return {
        "affected": affected_entities,
        "count": len(affected_entities)
    }
```

### 4. Relationship Management Tools

Implement tools for creating and managing relationships between entities.

```python
# Add these methods to the MemoryMCPServer class

class Relation(BaseModel):
    from_: str = Field(..., alias="from", description="The name of the entity where the relation starts")
    relationType: str = Field(..., description="The type of the relation")
    to: str = Field(..., description="The name of the entity where the relation ends")

class RelationCreationParams(BaseModel):
    relations: List[Relation] = Field(..., description="An array of relations to create")

class RelationDeletionParams(BaseModel):
    relations: List[Relation] = Field(..., description="An array of relations to delete")

async def create_relations(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Create multiple new relations between entities.

    Args:
        params: Relation creation parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing created relation details
    """
    await ctx.info(f"Creating {len(params['relations'])} relations")

    # Validate params
    validated_params = RelationCreationParams(**params)

    # Process each relation
    created_relations = []

    for idx, relation in enumerate(validated_params.relations):
        # Report progress
        await ctx.report_progress(
            idx / len(validated_params.relations),
            f"Creating relation: {relation.from_} -{relation.relationType}-> {relation.to}"
        )

        # Create Cypher query for relation creation
        query = """
        MATCH (from:`Entity` {name: $from})
        MATCH (to:`Entity` {name: $to})
        MERGE (from)-[r:`$relationType`]->(to)
        SET r.created_at = datetime()
        RETURN from.name as from, type(r) as relationType, to.name as to
        """

        # Execute query with parameter substitution for relation type
        query = query.replace('`$relationType`', f"`{relation.relationType}`")

        result = await self.neo4j_client.execute_query(
            query=query,
            parameters={
                "from": relation.from_,
                "to": relation.to
            }
        )

        if result:
            created_relations.append({
                "from": relation.from_,
                "relationType": relation.relationType,
                "to": relation.to
            })

    await ctx.report_progress(1.0, "Relation creation completed")

    return {
        "created": created_relations,
        "count": len(created_relations)
    }

async def delete_relations(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Delete multiple relations from the knowledge graph.

    Args:
        params: Relation deletion parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing deleted relation details
    """
    await ctx.info(f"Deleting {len(params['relations'])} relations")

    # Validate params
    validated_params = RelationDeletionParams(**params)

    # Process each relation
    deleted_relations = []

    for idx, relation in enumerate(validated_params.relations):
        # Report progress
        await ctx.report_progress(
            idx / len(validated_params.relations),
            f"Deleting relation: {relation.from_} -{relation.relationType}-> {relation.to}"
        )

        # Create Cypher query for relation deletion
        query = """
        MATCH (from:`Entity` {name: $from})-[r:`$relationType`]->(to:`Entity` {name: $to})
        DELETE r
        RETURN from.name as from, type(r) as relationType, to.name as to
        """

        # Execute query with parameter substitution for relation type
        query = query.replace('`$relationType`', f"`{relation.relationType}`")

        result = await self.neo4j_client.execute_query(
            query=query,
            parameters={
                "from": relation.from_,
                "to": relation.to
            }
        )

        if result:
            deleted_relations.append({
                "from": relation.from_,
                "relationType": relation.relationType,
                "to": relation.to
            })

    await ctx.report_progress(1.0, "Relation deletion completed")

    return {
        "deleted": deleted_relations,
        "count": len(deleted_relations)
    }
```

### 5. Query and Search Tools

Implement powerful query and search capabilities for the knowledge graph.

```python
# Add these methods to the MemoryMCPServer class

class SearchNodesParams(BaseModel):
    query: str = Field(..., description="The search query to match against entity names, types, and observation content")

class OpenNodesParams(BaseModel):
    names: List[str] = Field(..., description="An array of entity names to retrieve")

async def read_graph(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Read the entire knowledge graph.

    Args:
        params: Empty parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing entities and relations
    """
    await ctx.info("Reading entire knowledge graph")

    # Get entities with their observations
    entities_query = """
    MATCH (e:`Entity`)
    OPTIONAL MATCH (e)-[:HAS_OBSERVATION]->(o:`Observation`)
    RETURN e.name as name, e.type as type,
           collect(o.content) as observations,
           e.created_at as created_at, e.updated_at as updated_at
    """

    entities_result = await self.neo4j_client.execute_query(entities_query)

    # Get relations
    relations_query = """
    MATCH (from:`Entity`)-[r]->(to:`Entity`)
    WHERE type(r) <> 'HAS_OBSERVATION'
    RETURN from.name as from, type(r) as relationType, to.name as to,
           r.created_at as created_at
    """

    relations_result = await self.neo4j_client.execute_query(relations_query)

    # Format entities
    entities = []
    for entity in entities_result:
        entities.append({
            "name": entity["name"],
            "type": entity["type"],
            "observations": entity["observations"] or [],
            "created_at": entity.get("created_at"),
            "updated_at": entity.get("updated_at")
        })

    # Format relations
    relations = []
    for relation in relations_result:
        relations.append({
            "from": relation["from"],
            "relationType": relation["relationType"],
            "to": relation["to"],
            "created_at": relation.get("created_at")
        })

    await ctx.report_progress(1.0, "Knowledge graph retrieval completed")

    return {
        "entities": entities,
        "relations": relations,
        "entity_count": len(entities),
        "relation_count": len(relations)
    }

async def search_nodes(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Search for nodes in the knowledge graph based on a query.

    Args:
        params: Search parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing matching nodes
    """
    await ctx.info(f"Searching nodes with query: {params['query']}")

    # Validate params
    validated_params = SearchNodesParams(**params)

    # Fuzzy search query that matches entity names, types, and observation content
    search_query = """
    MATCH (e:`Entity`)
    WHERE e.name =~ $search_pattern OR e.type =~ $search_pattern
    RETURN e.name as name, e.type as type, [] as observations, 'name_or_type' as match_type

    UNION

    MATCH (e:`Entity`)-[:HAS_OBSERVATION]->(o:`Observation`)
    WHERE o.content =~ $search_pattern
    WITH e, collect(o.content) as matchedObs
    RETURN e.name as name, e.type as type, matchedObs as observations, 'observation' as match_type
    """

    # Execute search query
    search_results = await self.neo4j_client.execute_query(
        query=search_query,
        parameters={
            "search_pattern": f"(?i).*{validated_params.query}.*"  # Case-insensitive pattern matching
        }
    )

    # Format search results
    nodes = []
    for result in search_results:
        nodes.append({
            "name": result["name"],
            "type": result["type"],
            "matchedObservations": result["observations"],
            "matchType": result["match_type"]
        })

    await ctx.report_progress(1.0, "Node search completed")

    return {
        "query": validated_params.query,
        "nodes": nodes,
        "count": len(nodes)
    }

async def open_nodes(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Open specific nodes in the knowledge graph by their names.

    Args:
        params: Open node parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing detailed node information
    """
    await ctx.info(f"Opening {len(params['names'])} nodes")

    # Validate params
    validated_params = OpenNodesParams(**params)

    # Detailed node query
    node_query = """
    MATCH (e:`Entity`)
    WHERE e.name IN $names
    OPTIONAL MATCH (e)-[:HAS_OBSERVATION]->(o:`Observation`)
    WITH e, collect(o.content) as obs
    OPTIONAL MATCH (e)-[r]->(related:`Entity`)
    WHERE type(r) <> 'HAS_OBSERVATION'
    WITH e, obs, collect({relationType: type(r), entity: related.name, entityType: related.type}) as outgoing
    OPTIONAL MATCH (other:`Entity`)-[r2]->(e)
    WHERE type(r2) <> 'HAS_OBSERVATION'
    WITH e, obs, outgoing, collect({relationType: type(r2), entity: other.name, entityType: other.type}) as incoming
    RETURN e.name as name, e.type as type, obs as observations,
           outgoing, incoming, e.created_at as created_at, e.updated_at as updated_at
    """

    # Execute node query
    node_results = await self.neo4j_client.execute_query(
        query=node_query,
        parameters={"names": validated_params.names}
    )

    # Format node results
    nodes = []
    for result in node_results:
        nodes.append({
            "name": result["name"],
            "type": result["type"],
            "observations": result["observations"] or [],
            "outgoingRelations": result["outgoing"] or [],
            "incomingRelations": result["incoming"] or [],
            "created_at": result.get("created_at"),
            "updated_at": result.get("updated_at")
        })

    await ctx.report_progress(1.0, "Node retrieval completed")

    return {
        "nodes": nodes,
        "count": len(nodes)
    }
```

### 6. Session Persistence Implementation

Implement tools for persisting knowledge across sessions.

```python
# Additional methods to add to the MemoryMCPServer class

class SessionStartParams(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the session")
    user_id: Optional[str] = Field(None, description="User ID associated with the session")

class SessionEndParams(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the session")
    summary: Optional[str] = Field(None, description="Summary of the session")

async def start_session(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Start a new knowledge session.

    Args:
        params: Session start parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing session details
    """
    await ctx.info(f"Starting session: {params['session_id']}")

    # Validate params
    validated_params = SessionStartParams(**params)

    # Create session node
    query = """
    CREATE (s:`Session` {
        session_id: $session_id,
        start_time: datetime(),
        user_id: $user_id
    })
    RETURN s.session_id as session_id, s.start_time as start_time
    """

    result = await self.neo4j_client.execute_query(
        query=query,
        parameters={
            "session_id": validated_params.session_id,
            "user_id": validated_params.user_id
        }
    )

    session_data = result[0] if result else {}

    await ctx.report_progress(1.0, "Session started")

    return {
        "session_id": validated_params.session_id,
        "start_time": session_data.get("start_time"),
        "user_id": validated_params.user_id
    }

async def end_session(self, params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """End a knowledge session.

    Args:
        params: Session end parameters
        ctx: Context for progress reporting

    Returns:
        Dictionary containing session details
    """
    await ctx.info(f"Ending session: {params['session_id']}")

    # Validate params
    validated_params = SessionEndParams(**params)

    # Update session node
    query = """
    MATCH (s:`Session` {session_id: $session_id})
    SET s.end_time = datetime(),
        s.summary = $summary
    RETURN s.session_id as session_id, s.start_time as start_time,
           s.end_time as end_time, s.summary as summary
    """

    result = await self.neo4j_client.execute_query(
        query=query,
        parameters={
            "session_id": validated_params.session_id,
            "summary": validated_params.summary
        }
    )

    session_data = result[0] if result else {}

    await ctx.report_progress(1.0, "Session ended")

    return {
        "session_id": validated_params.session_id,
        "start_time": session_data.get("start_time"),
        "end_time": session_data.get("end_time"),
        "summary": session_data.get("summary")
    }

async def record_search(
    self, session_id: str, query: str, destination: Optional[str] = None
) -> Dict[str, Any]:
    """Record a search in the current session.

    Args:
        session_id: The session ID
        query: The search query
        destination: Optional destination name being searched

    Returns:
        Dictionary containing search details
    """
    # Create search node
    query = """
    MATCH (s:`Session` {session_id: $session_id})
    CREATE (search:`Search` {
        query: $query,
        timestamp: datetime()
    })
    CREATE (s)-[:INCLUDED]->(search)
    """

    params = {
        "session_id": session_id,
        "query": query
    }

    await self.neo4j_client.execute_query(query=query, parameters=params)

    # If destination is provided, link the search to it
    if destination:
        dest_query = """
        MATCH (search:`Search`)-[:INCLUDED]-(`Session` {session_id: $session_id})
        WHERE search.query = $query
        MATCH (dest:`Entity` {name: $destination, type: 'Destination'})
        CREATE (search)-[:CONCERNING]->(dest)
        """

        await self.neo4j_client.execute_query(
            query=dest_query,
            parameters={
                "session_id": session_id,
                "query": query,
                "destination": destination
            }
        )

    return {
        "session_id": session_id,
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "destination": destination
    }

async def record_preference(
    self, session_id: str, user_id: str, preference_type: str, value: str
) -> Dict[str, Any]:
    """Record a user preference.

    Args:
        session_id: The session ID
        user_id: The user ID
        preference_type: Type of preference (e.g., "transportation", "accommodation")
        value: Preference value (e.g., "train", "hostel")

    Returns:
        Dictionary containing preference details
    """
    # Create preference node
    query = """
    MATCH (s:`Session` {session_id: $session_id})
    MERGE (p:`UserPreference` {
        user_id: $user_id,
        preference_type: $preference_type,
        value: $value
    })
    MERGE (s)-[:ESTABLISHED]->(p)
    SET p.updated_at = datetime()
    RETURN p.preference_type as preference_type, p.value as value
    """

    result = await self.neo4j_client.execute_query(
        query=query,
        parameters={
            "session_id": session_id,
            "user_id": user_id,
            "preference_type": preference_type,
            "value": value
        }
    )

    pref_data = result[0] if result else {}

    return {
        "user_id": user_id,
        "preference_type": pref_data.get("preference_type", preference_type),
        "value": pref_data.get("value", value),
        "session_id": session_id
    }

async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
    """Get all preferences for a user.

    Args:
        user_id: The user ID

    Returns:
        Dictionary containing all user preferences
    """
    # Query user preferences
    query = """
    MATCH (p:`UserPreference` {user_id: $user_id})
    RETURN p.preference_type as preference_type, p.value as value
    """

    results = await self.neo4j_client.execute_query(
        query=query,
        parameters={"user_id": user_id}
    )

    # Format preferences
    preferences = {}
    for pref in results:
        preferences[pref["preference_type"]] = pref["value"]

    return {
        "user_id": user_id,
        "preferences": preferences
    }
```

## Integration with TripSage

### Client Usage Examples

#### 1. Travel Planning Agent Integration

```python
# Example code for Travel Planning Agent integration

from src.mcp.memory.client import MemoryClient

class TravelPlanningAgent:
    def __init__(self):
        # Initialize Memory MCP client
        self.memory_client = MemoryClient(endpoint="http://localhost:3004")

    async def plan_trip(self, user_id: str, query: str):
        # 1. Start a new session
        session_id = str(uuid.uuid4())
        await self.memory_client.call_tool("start_session", {
            "session_id": session_id,
            "user_id": user_id
        })

        # 2. Retrieve user preferences from knowledge graph
        user_nodes = await self.memory_client.open_nodes([f"User:{user_id}"])
        user_prefs = {}
        if user_nodes:
            user_node = user_nodes[0]
            for obs in user_node["observations"]:
                if obs.startswith("Prefers "):
                    parts = obs.replace("Prefers ", "").split(" for ")
                    if len(parts) == 2:
                        user_prefs[parts[1]] = parts[0]

        # 3. Extract destination from query
        destinations = extract_destinations(query)
        destination_nodes = []

        for dest in destinations:
            # Search for existing destination knowledge
            results = await self.memory_client.search_nodes(dest)
            matching_dests = [node for node in results if node["type"] == "Destination"]

            if matching_dests:
                # Use existing destination knowledge
                destination_nodes.extend(matching_dests)
            else:
                # Create new destination entity with basic info
                await self.memory_client.create_entities([{
                    "name": dest,
                    "entityType": "Destination",
                    "observations": [f"Mentioned in query: {query}"]
                }])

                # Record for later enrichment
                destination_nodes.append({"name": dest, "type": "Destination"})

        # 4. Process the travel plan using knowledge
        plan = await self._generate_plan(query, user_prefs, destination_nodes)

        # 5. Update knowledge graph with new information
        await self._update_knowledge_graph(plan, session_id, user_id)

        # 6. End session
        await self.memory_client.call_tool("end_session", {
            "session_id": session_id,
            "summary": f"Travel planning session for {', '.join(destinations)}"
        })

        return plan

    async def _update_knowledge_graph(self, plan, session_id, user_id):
        # Extract entities from the plan
        new_entities = []

        # Example: Add accommodations
        for accommodation in plan.get("accommodations", []):
            new_entities.append({
                "name": accommodation["name"],
                "entityType": "Accommodation",
                "observations": [
                    f"Located in {accommodation['location']}",
                    f"Price range: {accommodation['price_range']}",
                    accommodation.get("description", "")
                ]
            })

        # Create entities
        if new_entities:
            await self.memory_client.create_entities(new_entities)

        # Extract relationships
        new_relations = []

        # Example: Connect accommodations to destinations
        for accommodation in plan.get("accommodations", []):
            new_relations.append({
                "from": accommodation["name"],
                "relationType": "is_located_in",
                "to": accommodation["location"]
            })

        # Create relations
        if new_relations:
            await self.memory_client.create_relations(new_relations)

        # Record user preferences if found in the plan
        if "preferences" in plan:
            for pref_type, value in plan["preferences"].items():
                await self.memory_client.record_preference(
                    session_id=session_id,
                    user_id=user_id,
                    preference_type=pref_type,
                    value=value
                )
```

#### 2. Capturing Travel History for Personalization

```python
# Example code for recording a completed trip
async def record_completed_trip(user_id: str, trip_details: Dict[str, Any]):
    memory_client = MemoryClient(endpoint="http://localhost:3004")

    # Create trip entity
    trip_name = f"Trip:{trip_details['id']}"

    # Format trip observations
    trip_observations = [
        f"{trip_details['duration']} trip to {trip_details['destination']} in {trip_details['month']} {trip_details['year']}",
        f"Budget: ${trip_details['budget']}",
        f"Rating: {trip_details['rating']}/5"
    ]

    # Add custom notes if available
    if trip_details.get('notes'):
        trip_observations.append(trip_details['notes'])

    # Create trip entity
    await memory_client.create_entities([{
        "name": trip_name,
        "entityType": "Trip",
        "observations": trip_observations
    }])

    # Link trip to user
    await memory_client.create_relations([{
        "from": f"User:{user_id}",
        "relationType": "experienced",
        "to": trip_name
    }])

    # Link trip to destination
    await memory_client.create_relations([{
        "from": trip_name,
        "relationType": "visited",
        "to": trip_details['destination']
    }])

    # Add accommodations if available
    if trip_details.get('accommodation'):
        await memory_client.create_relations([{
            "from": trip_name,
            "relationType": "stayed_at",
            "to": trip_details['accommodation']
        }])

    # Extract preferences from trip feedback
    if trip_details.get('feedback'):
        for category, rating in trip_details['feedback'].items():
            if rating >= 4:  # Only record high ratings as preferences
                await memory_client.add_observations([{
                    "entityName": f"User:{user_id}",
                    "contents": [f"Prefers {trip_details['destination']} for {category}"]
                }])
```

#### 3. Using Knowledge Graph for Recommendations

```python
# Example code for generating personalized recommendations
async def generate_destination_recommendations(user_id: str):
    memory_client = MemoryClient(endpoint="http://localhost:3004")

    # Get user node with preferences
    user_nodes = await memory_client.open_nodes([f"User:{user_id}"])

    if not user_nodes:
        return {"error": "User not found in knowledge graph"}

    user_node = user_nodes[0]

    # Extract preferred destinations from past trips
    outgoing_relations = user_node.get("outgoingRelations", [])
    past_trips = [rel for rel in outgoing_relations if rel["relationType"] == "experienced"]

    # Get list of previously visited destinations
    visited_destinations = set()

    for trip_rel in past_trips:
        # Follow the trip to destination relation
        trip_nodes = await memory_client.open_nodes([trip_rel["entity"]])

        if trip_nodes:
            trip_node = trip_nodes[0]
            trip_destinations = [rel for rel in trip_node.get("outgoingRelations", [])
                                if rel["relationType"] == "visited"]

            for dest_rel in trip_destinations:
                visited_destinations.add(dest_rel["entity"])

    # Extract user preferences
    preferences = {}
    for observation in user_node.get("observations", []):
        if observation.startswith("Prefers "):
            parts = observation.replace("Prefers ", "").split(" for ")
            if len(parts) == 2:
                category = parts[1]
                if category not in preferences:
                    preferences[category] = []
                preferences[category].append(parts[0])

    # Generate recommendations based on preferences
    recommendations = []

    # For each preference category, find matching destinations
    for category, values in preferences.items():
        for value in values:
            # Search for destinations with similar attributes
            similar_destinations = await memory_client.search_nodes(value)

            for dest in similar_destinations:
                if dest["type"] == "Destination" and dest["name"] not in visited_destinations:
                    # Add to recommendations if not already visited
                    recommendations.append({
                        "destination": dest["name"],
                        "reason": f"You might like this because you prefer {value} for {category}",
                        "confidence": 0.8  # Example confidence score
                    })

    # Deduplicate recommendations
    unique_recommendations = {}
    for rec in recommendations:
        if rec["destination"] not in unique_recommendations:
            unique_recommendations[rec["destination"]] = rec
        else:
            # If duplicate, take the one with higher confidence
            if rec["confidence"] > unique_recommendations[rec["destination"]]["confidence"]:
                unique_recommendations[rec["destination"]] = rec

    return {"recommendations": list(unique_recommendations.values())}
```

## Testing Strategy

### Unit Testing for Neo4j Client

```python
# /tests/mcp/memory/test_neo4j_client.py
import pytest
from unittest.mock import AsyncMock, patch
from src.mcp.memory.client import Neo4jClient, MemoryClient

@pytest.fixture
def mock_neo4j_driver():
    with patch("src.mcp.memory.client.GraphDatabase") as mock:
        mock.driver.return_value.session.return_value.__enter__.return_value.run.return_value = [
            {"key1": "value1", "key2": "value2"}
        ]
        yield mock

@pytest.fixture
def neo4j_client(mock_neo4j_driver):
    return Neo4jClient(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )

@pytest.mark.asyncio
async def test_execute_query(neo4j_client):
    # Test basic query execution
    result = await neo4j_client.execute_query("MATCH (n) RETURN n LIMIT 1")

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["key1"] == "value1"
    assert result[0]["key2"] == "value2"

@pytest.mark.asyncio
async def test_execute_query_with_parameters(neo4j_client):
    # Test query with parameters
    result = await neo4j_client.execute_query(
        "MATCH (n {name: $name}) RETURN n",
        {"name": "TestNode"}
    )

    assert isinstance(result, list)
    assert len(result) == 1

@pytest.mark.asyncio
async def test_execute_query_error(neo4j_client, mock_neo4j_driver):
    # Test error handling
    mock_neo4j_driver.driver.return_value.session.return_value.__enter__.return_value.run.side_effect = Exception("Test error")

    with pytest.raises(Exception) as exc_info:
        await neo4j_client.execute_query("INVALID QUERY")

    assert "Neo4j query failed" in str(exc_info.value)
```

### Integration Testing for Memory MCP Server

```python
# /tests/mcp/memory/test_memory_mcp_server.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from src.mcp.memory.server import MemoryMCPServer

@pytest.fixture
def memory_mcp_server():
    # Create server with mock Neo4j client
    server = MemoryMCPServer(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        host="localhost",
        port=3004
    )

    # Mock the Neo4j client
    server.neo4j_client.execute_query = AsyncMock(return_value=[])

    # Create test client
    client = TestClient(server.app)

    return client, server

def test_root_endpoint(memory_mcp_server):
    client, _ = memory_mcp_server
    response = client.get("/")

    assert response.status_code == 200
    assert "Memory" in response.json()["name"]
    assert "tools" in response.json()

def test_list_tools_endpoint(memory_mcp_server):
    client, _ = memory_mcp_server
    response = client.get("/tools")

    assert response.status_code == 200
    assert "tools" in response.json()
    assert isinstance(response.json()["tools"], list)

@pytest.mark.asyncio
async def test_create_entities(memory_mcp_server):
    _, server = memory_mcp_server

    # Mock Context
    mock_context = MagicMock()
    mock_context.info = AsyncMock()
    mock_context.report_progress = AsyncMock()

    # Mock Neo4j responses
    server.neo4j_client.execute_query.return_value = [{"name": "TestEntity"}]

    # Call the tool
    result = await server.create_entities(
        {
            "entities": [
                {
                    "name": "TestEntity",
                    "entityType": "Destination",
                    "observations": ["Test observation"]
                }
            ]
        },
        mock_context
    )

    # Check results
    assert "created" in result
    assert "count" in result
    assert result["count"] == 1
    assert result["created"][0] == "TestEntity"

    # Verify progress reporting
    mock_context.report_progress.assert_called()
    mock_context.info.assert_called()
```

## Deployment

### Docker Configuration

```dockerfile
# /Dockerfile.memory
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 3004

# Run server
CMD ["python", "-m", "src.mcp.memory.main"]
```

### Environment Variables

```plaintext
# Required environment variables for Memory MCP Server
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password
NEO4J_DATABASE=tripsage
MEMORY_MCP_HOST=0.0.0.0
MEMORY_MCP_PORT=3004
```

### Startup Script

```python
# /src/mcp/memory/main.py
"""
Main script to start the Memory MCP Server.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.mcp.memory.server import MemoryMCPServer
from src.utils.logging import setup_logging

if __name__ == "__main__":
    # Setup logging
    setup_logging()

    # Get environment variables
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    host = os.getenv("MEMORY_MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MEMORY_MCP_PORT", "3004"))

    # Validate required environment variables
    if not neo4j_password:
        logging.error("NEO4J_PASSWORD environment variable is required")
        sys.exit(1)

    # Create and run server
    server = MemoryMCPServer(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        host=host,
        port=port
    )

    # Run the server
    server.run()
```

### Docker Compose Integration

Add the Memory MCP Server to the TripSage docker-compose.yml:

```yaml
# Memory MCP Server
memory-mcp:
  build:
    context: .
    dockerfile: Dockerfile.memory
  ports:
    - "3004:3004"
  environment:
    - NEO4J_URI=bolt://neo4j:7687
    - NEO4J_USER=neo4j
    - NEO4J_PASSWORD=${NEO4J_PASSWORD}
    - MEMORY_MCP_HOST=0.0.0.0
    - MEMORY_MCP_PORT=3004
  depends_on:
    - neo4j
  restart: unless-stopped

# Neo4j Database
neo4j:
  image: neo4j:4.4
  ports:
    - "7474:7474" # HTTP
    - "7687:7687" # Bolt
  environment:
    - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
    - NEO4J_dbms_memory_heap_max__size=4G
    - NEO4J_dbms_memory_pagecache_size=1G
  volumes:
    - neo4j_data:/data
    - neo4j_logs:/logs
  restart: unless-stopped
```
