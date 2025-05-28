# Memory MCP Server Integration Guide (Mem0 + pgvector Knowledge System)

This document provides a guide to integrating and using the Memory MCP Server, which acts as the primary interface to TripSage's unified memory system built on Supabase PostgreSQL with pgvector extensions.

## 1. Overview

The Memory MCP Server is a crucial component in TripSage's unified storage architecture. It provides a standardized Model Context Protocol (MCP) interface for all interactions with the Mem0 memory system backed by Supabase PostgreSQL with pgvector for high-performance vector search. This server enables AI agents and other backend services to:

- Create, read, update, and delete travel-related memories with vector embeddings.
- Perform high-performance semantic similarity search using pgvector with HNSW indexing.
- Store and retrieve contextual memories with metadata filtering.
- Persist knowledge across user sessions, enabling personalization and learning.
- Perform vector-based queries to uncover insights and patterns in travel data.
- Leverage Mem0's memory deduplication and optimization capabilities.

TripSage utilizes **Mem0 with Supabase PostgreSQL + pgvector** as its memory system implementation, achieving <100ms latency and 471+ QPS performance.

## 2. Role in TripSage Architecture

- **Vector Memory Abstraction**: The Memory MCP abstracts the complexities of vector database operations (embeddings, similarity search, indexing) from the application logic.
- **Standardized Interface**: Provides a consistent set of tools for memory operations, usable by any MCP-compatible client.
- **Agent Memory**: Serves as the "long-term memory" for AI agents, allowing them to store learned information and retrieve context using semantic similarity.
- **Data Enrichment**: Facilitates linking structured data from the relational database with semantic vector embeddings for enhanced search and recommendations.
- **Performance Optimization**: Leverages pgvector's HNSW indexing for 11x faster vector search compared to traditional approaches.

## 3. Mem0 Memory System with pgvector

### 3.1. Features

The Mem0 memory system with pgvector backend provides tools for:

- **Memory Management**:
  - `add_memory`: Creates new memories with automatic vector embedding generation for semantic search.
  - `get_memory`: Retrieves specific memories by ID with optional filtering.
  - `update_memory`: Modifies existing memories and regenerates embeddings as needed.
  - `delete_memory`: Removes memories and their associated vector embeddings.
- **Vector Search and Similarity**:
  - `search_memories`: Performs semantic similarity search using pgvector's cosine distance with HNSW indexing.
  - `get_similar_memories`: Finds contextually relevant memories based on vector similarity.
  - `hybrid_search`: Combines vector similarity with metadata filtering for precise results.
- **Memory Organization**:
  - `get_user_memories`: Retrieves all memories for a specific user with pagination support.
  - `get_session_memories`: Fetches memories associated with specific chat sessions or interactions.
  - `deduplicate_memories`: Automatically identifies and merges similar memories to prevent redundancy.
- **Performance Optimizations**:
  - **HNSW Indexing**: Hierarchical Navigable Small World indexes for sub-100ms vector search.
  - **Batch Operations**: Efficient bulk memory creation and updates.
  - **Caching Integration**: Redis-backed caching for frequently accessed memories.

### 3.2. Setup and Configuration

**Supabase pgvector Setup**:  
The memory system is now integrated directly with Supabase PostgreSQL. The pgvector extensions are enabled via migrations:

```sql
-- Enable pgvector extension for 1536-dimensional embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create optimized indexes for vector search
CREATE INDEX CONCURRENTLY IF NOT EXISTS memories_embedding_cosine_idx 
ON memories USING hnsw (embedding vector_cosine_ops);
```

**Memory System Configuration**:  
TripSage configures Mem0 to use the Supabase PostgreSQL backend with pgvector:

```python
# Memory system configuration
memory_config = {
    "vector_store": {
        "provider": "postgres",
        "config": {
            "url": settings.database.supabase_url,
            "table_name": "memories",
            "embedding_model_dims": 1536,
            "index_type": "hnsw",
            "distance_metric": "cosine"
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "dimensions": 1536
        }
    }
}
```

**Environment Variables for TripSage**:

```plaintext
# .env - Supabase Configuration
TRIPSAGE_DATABASE_SUPABASE_URL=https://your-project.supabase.co
TRIPSAGE_DATABASE_SUPABASE_ANON_KEY=your-anon-key
TRIPSAGE_DATABASE_SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# pgvector Configuration
TRIPSAGE_DATABASE_PGVECTOR_ENABLED=true
TRIPSAGE_DATABASE_VECTOR_DIMENSIONS=1536

# Memory MCP Endpoint (if using external MCP server)
MEMORY_MCP_ENDPOINT=http://localhost:3008
```

**Migration Setup**:  
Apply the memory system migration:

```bash
# Apply pgvector extensions
psql -f migrations/20250526_01_enable_pgvector_extensions.sql

# Apply Mem0 memory system schema  
psql -f migrations/20250527_01_mem0_memory_system.sql
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
