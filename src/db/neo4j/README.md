# Neo4j Knowledge Graph Integration

This directory contains the Neo4j knowledge graph integration for TripSage, implementing the dual storage architecture that combines Supabase (relational) with Neo4j (graph database).

## Overview

The Neo4j integration provides a robust knowledge graph for storing travel-related information, relationships between destinations, and user travel patterns. This enables powerful graph-based queries like:

- Finding connected destinations (routes between places)
- Providing personalized travel recommendations based on interests
- Analyzing trip patterns and popular destination combinations
- Geographic proximity searches for nearby points of interest

## Architecture

The implementation follows a clean architecture with several components:

- **Client**: High-level interface for Neo4j operations
- **Connection**: Low-level connection management and query execution
- **Repositories**: Data access layer for specific entity types
- **Schemas**: Pydantic models for data validation
- **Migrations**: Database setup, constraints, indexes, and seed data
- **Sync**: Utilities to synchronize data between Supabase and Neo4j
- **Memory MCP**: FastMCP server for knowledge graph operations

## File Structure

```plaintext
src/db/neo4j/
├── __init__.py
├── client.py           # High-level client interface
├── config.py           # Neo4j connection configuration
├── connection.py       # Connection management and query execution
├── exceptions.py       # Custom exceptions for Neo4j operations
├── migrations/         # Database setup and seed data
│   ├── __init__.py
│   ├── constraints.py  # Node and relationship constraints
│   ├── indexes.py      # Performance indexes for queries
│   └── initial_data.py # Seed data for knowledge graph
├── repositories/       # Data access layer
│   ├── __init__.py
│   ├── base.py         # Generic repository with CRUD operations
│   └── destination.py  # Destination-specific repository
├── schemas/            # Pydantic models
│   ├── __init__.py
│   └── destination.py  # Destination entity schema
└── sync.py             # Sync with relational database
```

## Memory MCP Integration

The Memory MCP server provides a standard interface for knowledge graph operations:

```plaintext
src/mcp/memory/
├── __init__.py
├── client.py           # Memory MCP client
└── server.py           # FastMCP server implementation
```

## Usage Examples

### Basic Usage

```python
from src.db.neo4j.client import neo4j_client

# Initialize Neo4j database
await neo4j_client.initialize()

# Add a new destination
destination = await neo4j_client.add_destination({
    "name": "Bali",
    "country": "Indonesia",
    "type": "island",
    "description": "Tropical paradise with beaches and temples",
    "safety_rating": 4.2,
    "cost_level": 2
})

# Create a relationship between destinations
await neo4j_client.create_destination_relationship(
    from_destination="Tokyo",
    relationship_type="CONNECTED_TO",
    to_destination="Kyoto",
    properties={
        "distance_km": 372,
        "transport": ["train", "flight", "bus"]
    }
)

# Find nearby destinations
nearby = await neo4j_client.find_nearby_destinations(
    latitude=35.6762,
    longitude=139.6503,
    distance_km=100
)

# Get travel recommendations based on interests
recommendations = await neo4j_client.find_travel_recommendations(
    interests=["beaches", "cuisine", "nature"],
    preferred_countries=["Thailand", "Indonesia", "Vietnam"],
    budget_level=3
)
```

### Memory MCP Usage

```python
from src.mcp.memory.client import memory_client

# Initialize Memory MCP client
await memory_client.initialize()

# Create entities
entities = await memory_client.create_entities([
    {
        "name": "Paris",
        "entityType": "Destination",
        "observations": [
            "Known for the Eiffel Tower and Louvre Museum",
            "France's capital and major cultural center"
        ]
    }
])

# Create relationships
relations = await memory_client.create_relations([
    {
        "from": "Paris",
        "relationType": "LOCATED_IN",
        "to": "France"
    }
])

# Search knowledge graph
results = await memory_client.search_nodes("museums art culture")

# Read entire knowledge graph
graph = await memory_client.read_graph()
```

## Synchronization with Relational Database

The sync module ensures consistency between the Supabase relational database and the Neo4j knowledge graph:

```python
from src.db.neo4j.sync import sync_destinations_to_knowledge_graph, sync_trips_to_knowledge_graph

# Sync destinations
dest_stats = await sync_destinations_to_knowledge_graph()
print(f"Created: {dest_stats['created']}, Updated: {dest_stats['updated']}")

# Sync trips
trip_stats = await sync_trips_to_knowledge_graph()
print(f"Trips created: {trip_stats['trips_created']}, Relationships: {trip_stats['relationships_created']}")
```

## Testing

The system includes a command-line test script for verifying the Neo4j integration:

```bash
# Test connection to Neo4j
python scripts/test_neo4j_integration.py test

# List destinations in knowledge graph
python scripts/test_neo4j_integration.py list

# Search knowledge graph
python scripts/test_neo4j_integration.py search "temples japan"

# Find travel routes
python scripts/test_neo4j_integration.py route "Tokyo" "Kyoto"

# Get travel recommendations
python scripts/test_neo4j_integration.py recommend beaches nature --countries Thailand Indonesia --budget 3

# Synchronize with relational database
python scripts/test_neo4j_integration.py sync

# Test Memory MCP
python scripts/test_neo4j_integration.py memory
```

## Environment Setup

Make sure to set the following environment variables for Neo4j connection:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

## Knowledge Graph Schema

The knowledge graph uses the following primary node types:

- **Destination**: Travel locations (cities, countries, landmarks)
- **User**: System users and their preferences
- **Trip**: Complete travel itineraries

And relationship types:

- **CONNECTED_TO**: Connections between destinations
- **TRAVEL_ROUTE**: Specific travel routes with metadata
- **INCLUDES**: Trips including destinations
- **PLANNED**: Users who planned trips
- **VISITED**: Users who visited destinations
