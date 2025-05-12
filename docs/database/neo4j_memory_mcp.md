# Neo4j Memory MCP Integration

This document provides guidance on using the Neo4j Memory MCP integration in TripSage for knowledge graph operations.

## Overview

TripSage uses a dual storage strategy:

1. **Structured Data** - Stored in Supabase (PostgreSQL)
2. **Relationships & Unstructured Data** - Stored in Neo4j via Memory MCP

The Neo4j Memory MCP provides a standardized interface for knowledge graph operations without requiring direct Neo4j database access. This approach simplifies interactions with the knowledge graph and provides consistent error handling and validation.

## Setup & Configuration

### Docker Setup

Neo4j is configured using Docker for local development. The `docker-compose-neo4j.yml` file includes the Neo4j database configuration:

```yaml
version: '3'

services:
  neo4j:
    image: neo4j:5.14.0
    container_name: tripsage-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_max__size=2G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/import
      - neo4j_plugins:/plugins

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:
```

### Environment Variables

Configure the following environment variables in your `.env` file:

```
# Neo4j Database - Direct access (used by Migration tools)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Neo4j Memory MCP
MEMORY_MCP_ENDPOINT=http://localhost:3008
```

### Memory MCP Server - External Dependency

TripSage uses the official `mcp-neo4j-memory` package as an external dependency for the Memory MCP server, rather than implementing a custom server. This approach:

1. Ensures standard compliance with the MCP protocol
2. Reduces maintenance overhead
3. Leverages community-maintained code
4. Provides consistent behavior across implementations

The external package is automatically installed by the startup script if not already present.

### Starting the Memory MCP

A startup script is provided in `scripts/start_memory_mcp.sh` to install the dependency (if needed), configure, and start the Neo4j Memory MCP:

```bash
#!/bin/bash

# Check if mcp-neo4j-memory is installed
if ! pip show mcp-neo4j-memory > /dev/null 2>&1; then
    echo "Installing mcp-neo4j-memory..."
    pip install mcp-neo4j-memory
fi

# Load environment variables
if [ -f .env ]; then
    # Extract Neo4j configuration from .env
    NEO4J_URI=$(grep -o '^NEO4J_URI=.*' .env | cut -d '=' -f2)
    NEO4J_USER=$(grep -o '^NEO4J_USER=.*' .env | cut -d '=' -f2)
    NEO4J_PASSWORD=$(grep -o '^NEO4J_PASSWORD=.*' .env | cut -d '=' -f2)
    NEO4J_DATABASE=$(grep -o '^NEO4J_DATABASE=.*' .env | cut -d '=' -f2)
    MEMORY_MCP_PORT=$(grep -o '^MEMORY_MCP_ENDPOINT=.*' .env | cut -d ':' -f3)
else
    # Default configuration
    NEO4J_URI="bolt://localhost:7687"
    NEO4J_USER="neo4j"
    NEO4J_PASSWORD="tripsage_password"
    NEO4J_DATABASE="neo4j"
    MEMORY_MCP_PORT="3008"
fi

# Start the MCP server with Neo4j configuration
python -m mcp_neo4j_memory --port $MEMORY_MCP_PORT
```

## Using the Memory MCP Client

The `MemoryClient` class provides methods for interacting with the Neo4j Memory MCP:

```python
from src.mcp.memory.client import memory_client

# Initialize the client (required before first use)
await memory_client.initialize()

# Create entities in the knowledge graph
entities = [
    {
        "name": "Paris",
        "entityType": "Destination",
        "observations": ["Capital of France", "Known for cuisine and art"]
    },
    {
        "name": "Eiffel Tower",
        "entityType": "Landmark",
        "observations": ["Famous iron tower", "Built in 1889"]
    }
]
created_entities = await memory_client.create_entities(entities)

# Create relationships between entities
relations = [
    {
        "from": "Paris",
        "relationType": "HAS_LANDMARK",
        "to": "Eiffel Tower"
    }
]
created_relations = await memory_client.create_relations(relations)

# Add observations to existing entities
observations = [
    {
        "entityName": "Paris",
        "contents": ["Popular tourist destination", "Known for romance"]
    }
]
updated_entities = await memory_client.add_observations(observations)

# Search for entities in the knowledge graph
search_results = await memory_client.search_nodes("Paris landmark")

# Get detailed information about specific entities
entities = await memory_client.open_nodes(["Paris", "Eiffel Tower"])

# Read the entire knowledge graph (use sparingly with large graphs)
graph = await memory_client.read_graph()
```

## Dual Storage Strategy

The `dual_storage.py` module provides functions for implementing the dual storage strategy:

```python
from src.utils.dual_storage import (
    store_trip_with_dual_storage,
    retrieve_trip_with_dual_storage,
    update_trip_with_dual_storage,
    delete_trip_with_dual_storage,
)

# Store trip data using dual storage
result = await store_trip_with_dual_storage(trip_data, user_id)

# Retrieve trip data from both storage systems
trip = await retrieve_trip_with_dual_storage(trip_id)

# Include knowledge graph data
trip_with_graph = await retrieve_trip_with_dual_storage(trip_id, include_graph=True)

# Update trip data in both storage systems
update_result = await update_trip_with_dual_storage(trip_id, updates)

# Delete trip data from both storage systems
delete_result = await delete_trip_with_dual_storage(trip_id)
```

## Session Memory Utilities

The `session_memory.py` module provides utilities for session initialization and memory management:

```python
from src.utils.session_memory import (
    initialize_session_memory,
    update_session_memory,
    store_session_summary,
)

# Initialize session memory with user information
session_data = await initialize_session_memory(user_id)

# Update session memory with new preferences or facts
updates = {
    "preferences": {
        "flights": "window seats",
        "accommodation": "luxury"
    },
    "learned_facts": [
        {
            "from": "Paris",
            "relationType": "KNOWN_FOR",
            "to": "Cuisine",
            "fromType": "Destination",
            "toType": "Attribute"
        }
    ]
}
result = await update_session_memory(user_id, updates)

# Store a summary of the session
summary = "User researched vacation options in Europe for summer 2025"
result = await store_session_summary(user_id, summary, session_id)
```

## Agent Memory Tools

The memory tools in `src/agents/memory_tools.py` provide function tools for use with the OpenAI Agents SDK:

```python
from src.agents.memory_tools import (
    get_knowledge_graph,
    search_knowledge_graph,
    get_entity_details,
    create_knowledge_entities,
    create_knowledge_relations,
    add_entity_observations,
    delete_knowledge_entities,
    delete_knowledge_relations,
    delete_entity_observations,
    initialize_agent_memory,
    update_agent_memory,
    save_session_summary,
)
```

These tools can be registered with agents to give them access to memory operations:

```python
def _register_default_tools(self) -> None:
    """Register default tools for the agent."""
    from .memory_tools import (
        initialize_agent_memory,
        search_knowledge_graph,
        get_entity_details,
        create_knowledge_entities,
        create_knowledge_relations,
        add_entity_observations,
    )
    
    # Register memory tools with the agent
    self.register_tool(initialize_agent_memory)
    self.register_tool(search_knowledge_graph)
    self.register_tool(get_entity_details)
    self.register_tool(create_knowledge_entities)
    self.register_tool(create_knowledge_relations)
    self.register_tool(add_entity_observations)
```

## Knowledge Graph Structure

The knowledge graph uses the following entity types:

- **User** - System users and their preferences
- **Trip** - Complete travel itineraries
- **Destination** - Travel locations (cities, countries, landmarks)
- **Accommodation** - Hotels, hostels, rental properties
- **Activity** - Points of interest, tours, events
- **Transportation** - Airlines, trains, buses, car services
- **Session** - Record of user interactions with the system

Common relationship types include:

- **PLANS** - User plans Trip
- **INCLUDES** - Trip includes Destination/Accommodation/Activity
- **LOCATED_IN** - Accommodation is located in Destination
- **TAKES_PLACE_IN** - Activity takes place in Destination
- **HAS_LANDMARK** - Destination has Landmark
- **DEPARTS_FROM** - Transportation departs from Destination
- **ARRIVES_AT** - Transportation arrives at Destination
- **PARTICIPATED_IN** - User participated in Session

## Error Handling

All memory operations include proper error handling to prevent system failures:

1. Errors are caught and logged
2. Meaningful error messages are returned to the caller
3. Changes are atomic (all-or-nothing) when multiple operations are involved
4. Timeouts prevent hanging connections

The `memory_client` handles retries and connection errors automatically.

## Testing

Tests for the Memory MCP integration can be found in:

1. `tests/mcp/memory/test_memory_client.py` - Tests for the Memory client
2. `tests/utils/test_dual_storage.py` - Tests for the dual storage strategy
3. `tests/utils/test_session_memory.py` - Tests for session memory utilities
4. `tests/agents/test_memory_tools.py` - Tests for agent memory tools