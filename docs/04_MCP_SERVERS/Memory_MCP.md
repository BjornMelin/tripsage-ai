# Memory MCP Server Integration Guide (Neo4j Knowledge Graph Interface)

This document provides a guide to integrating and using the Memory MCP Server, which acts as the primary interface to TripSage's Neo4j knowledge graph.

## 1. Overview

The Memory MCP Server is a crucial component in TripSage's dual-storage architecture. It provides a standardized Model Context Protocol (MCP) interface for all interactions with the Neo4j knowledge graph. This server enables AI agents and other backend services to:

- Create, read, update, and delete travel-related entities (e.g., destinations, accommodations, user profiles).
- Manage semantic relationships between these entities.
- Store and retrieve unstructured "observations" or facts about entities.
- Persist knowledge across user sessions, enabling personalization and learning.
- Perform graph-based queries to uncover insights and patterns in travel data.

TripSage utilizes the **official `mcp-neo4j-memory` package** as its Memory MCP server implementation.

## 2. Role in TripSage Architecture

- **Knowledge Graph Abstraction**: The Memory MCP abstracts the complexities of direct Neo4j interaction (Cypher queries, driver management) from the application logic.
- **Standardized Interface**: Provides a consistent set of tools for graph operations, usable by any MCP-compatible client.
- **Agent Memory**: Serves as the "long-term memory" for AI agents, allowing them to store learned information and retrieve context.
- **Data Enrichment**: Facilitates linking structured data from the relational database (Supabase/Neon) with semantic relationships in the knowledge graph.

## 3. `mcp-neo4j-memory` Server

### 3.1. Features

The `mcp-neo4j-memory` server typically provides tools for:

- **Entity Management**:
  - `create_entities`: Adds new nodes (entities). Each entity has a unique `name`, an `entityType`, and a list of `observations` (textual facts).
  - `delete_entities`: Removes entities and their relationships.
  - `add_observations`: Appends new observations to existing entities.
  - `delete_observations`: Removes specific observations from entities.
- **Relationship Management**:
  - `create_relations`: Establishes typed, directed relationships between two entities (identified by their names).
  - `delete_relations`: Removes specified relationships.
- **Querying and Retrieval**:
  - `search_nodes`: Finds entities based on fuzzy matching against their name, type, or observation content. Often utilizes Neo4j's full-text search capabilities if indexes are configured.
  - `open_nodes`: Retrieves detailed information for a list of entities by their exact names, including their observations and directly connected relationships.
  - `read_graph`: Fetches a representation of the graph, potentially with limits (use with caution on large graphs).

### 3.2. Setup and Configuration

**Docker Setup for Neo4j Backend**:  
Refer to the [Knowledge Graph Guide](../03_DATABASE_AND_STORAGE/KNOWLEDGE_GRAPH_GUIDE.md#3-neo4j-instance-setup-and-configuration) for setting up the Neo4j database.

**Starting the Memory MCP Server**:  
TripSage uses a script (`scripts/start_memory_mcp.sh`) to manage the `mcp-neo4j-memory` server process. Example snippet:

```bash
#!/bin/bash
# scripts/start_memory_mcp.sh (Conceptual)

# Ensure mcp-neo4j-memory is installed
if ! uv pip show mcp-neo4j-memory > /dev/null 2>&1; then
    echo "Installing mcp-neo4j-memory..."
    uv pip install mcp-neo4j-memory
fi

# Load environment variables from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

NEO4J_URI_FOR_MCP="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER_FOR_MCP="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD_FOR_MCP="${NEO4J_PASSWORD:-your_secure_password}"
NEO4J_DATABASE_FOR_MCP="${NEO4J_DATABASE:-neo4j}"

MEMORY_MCP_PORT_NUMBER=$(echo "${MEMORY_MCP_ENDPOINT:-http://localhost:3008}" | awk -F':' '{print $3}')

echo "Starting Neo4j Memory MCP Server on port ${MEMORY_MCP_PORT_NUMBER}..."
echo "MCP Server will connect to Neo4j at ${NEO4J_URI_FOR_MCP} as user ${NEO4J_USER_FOR_MCP} on database ${NEO4J_DATABASE_FOR_MCP}"

NEO4J_URI="$NEO4J_URI_FOR_MCP" \
NEO4J_USERNAME="$NEO4J_USER_FOR_MCP" \
NEO4J_PASSWORD="$NEO4J_PASSWORD_FOR_MCP" \
NEO4J_DATABASE="$NEO4J_DATABASE_FOR_MCP" \
python -m mcp_neo4j_memory --port "${MEMORY_MCP_PORT_NUMBER}"
```

**Environment Variables for TripSage**:

```plaintext
# .env
MEMORY_MCP_ENDPOINT=http://localhost:3008
# MEMORY_MCP_API_KEY=...
```

## 4. TripSage `MemoryClient`

```python
# src/mcp/memory/client.py (Simplified Snippet)
from typing import List, Dict, Any, Optional
from ..base_mcp_client import BaseMCPClient
from ...utils.config import settings
from ...utils.logging import get_module_logger
from agents import function_tool

logger = get_module_logger(__name__)

class MemoryClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_name="memory",
            endpoint=settings.mcp_servers.memory.endpoint,
            api_key=settings.mcp_servers.memory.api_key.get_secret_value() if settings.mcp_servers.memory.api_key else None,
            timeout=120.0
        )
        logger.info("Initialized Memory MCP Client.")

    @function_tool
    async def create_entities_in_graph(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        return await self.invoke_tool("create_entities", {"entities": entities})

    @function_tool
    async def create_relations_in_graph(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        return await self.invoke_tool("create_relations", {"relations": relations})

    @function_tool
    async def add_observations_to_entity(self, entity_name: str, new_observations: List[str]) -> Dict[str, Any]:
        payload = {
            "observations": [{"entityName": entity_name, "contents": new_observations}]
        }
        return await self.invoke_tool("add_observations", payload)

    @function_tool
    async def search_graph_nodes(self, search_query: str) -> List[Dict[str, Any]]:
        response = await self.invoke_tool("search_nodes", {"query": search_query})
        return response.get("nodes", [])

    @function_tool
    async def get_graph_node_details(self, entity_names: List[str]) -> List[Dict[str, Any]]:
        response = await self.invoke_tool("open_nodes", {"names": entity_names})
        return response.get("nodes", [])

    # ... other methods ...
```

### 4.2. Usage in Dual Storage Strategy

The `MemoryClient` is used by dual storage services (e.g., `TripStorageService`) to sync data to Neo4j after creating or updating in Supabase.

## 5. Session Memory and Agent Integration

- **Session Persistence**: Utilities to create a `Session` node, link user interactions, store session summaries.
- **Agent Memory Tools**: Wrappers around `MemoryClient` so agents can directly manipulate the knowledge graph.

## 6. Testing

- **Client Unit Tests**: Mock `invoke_tool` for `MemoryClient`.
- **Integration Tests**: Test against a live `mcp-neo4j-memory` server with a test Neo4j instance.

## 7. Conclusion

The Memory MCP Server provides a vital link between TripSage’s AI-driven features and the underlying Neo4j knowledge graph. Through a standardized MCP interface, agents and services can seamlessly store, retrieve, and analyze rich travel domain data.
