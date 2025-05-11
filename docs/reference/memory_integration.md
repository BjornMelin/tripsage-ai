# Memory Knowledge Graph Integration

This document provides detailed guidance on integrating with the Memory MCP for knowledge graph operations in the TripSage project.

## Knowledge Graph Structure

TripSage uses two distinct knowledge graphs:

1. **Travel Domain Knowledge Graph**

   - Stores travel-specific information (destinations, accommodations, etc.)
   - Used by the application to make travel recommendations

2. **Project Meta-Knowledge Graph** (Memory MCP)
   - Stores information about the TripSage system itself
   - Used by Claude to maintain project context across conversations

## Entity Types

Common entity types in the travel knowledge graph:

- `Destination` - Travel locations (cities, countries, landmarks)
- `Accommodation` - Hotels, hostels, rental properties
- `Transportation` - Airlines, trains, buses, car services
- `Activity` - Points of interest, tours, events
- `User` - System users and their preferences
- `Trip` - Complete travel itineraries

## Relation Types

Common relations in the travel knowledge graph:

- `is_located_in` - Geographic containment (city in country)
- `offers` - Service availability (hotel offers breakfast)
- `connects` - Transportation links (flight connects cities)
- `has_reviewed` - User feedback (user has reviewed hotel)
- `prefers` - User preferences (user prefers non-stop flights)
- `includes` - Composite relationships (trip includes activity)
- `requires` - Dependencies (activity requires booking)

## Memory Operations

### Entity Operations

```python
from mcp.memory.client import MemoryClient

memory_client = MemoryClient()

# Create new entities
async def add_destination(name, country, description):
    await memory_client.create_entities([{
        "name": name,
        "entityType": "Destination",
        "observations": [
            f"Located in {country}",
            description
        ]
    }])

# Create multiple entities
async def add_accommodations(accommodations_list):
    entities = []
    for acc in accommodations_list:
        entities.append({
            "name": acc["name"],
            "entityType": "Accommodation",
            "observations": [
                f"Located in {acc['location']}",
                f"Rating: {acc['rating']}/5",
                acc["description"]
            ]
        })
    await memory_client.create_entities(entities)
```

### Relation Operations

```python
# Create relations
async def connect_entities(from_entity, relation_type, to_entity):
    await memory_client.create_relations([{
        "from": from_entity,
        "relationType": relation_type,
        "to": to_entity
    }])

# Create multiple relations
async def build_trip_connections(trip_name, destinations, accommodations, activities):
    relations = []

    # Connect trip to destinations
    for dest in destinations:
        relations.append({
            "from": trip_name,
            "relationType": "includes",
            "to": dest
        })

    # Connect accommodations to destinations
    for acc, dest in zip(accommodations, destinations):
        relations.append({
            "from": acc,
            "relationType": "is_located_in",
            "to": dest
        })
        relations.append({
            "from": trip_name,
            "relationType": "includes",
            "to": acc
        })

    # Connect activities to destinations
    for act, dest in zip(activities, destinations):
        relations.append({
            "from": act,
            "relationType": "takes_place_in",
            "to": dest
        })
        relations.append({
            "from": trip_name,
            "relationType": "includes",
            "to": act
        })

    await memory_client.create_relations(relations)
```

### Observation Operations

```python
# Add observations to an existing entity
async def update_destination_info(destination_name, new_observations):
    await memory_client.add_observations([{
        "entityName": destination_name,
        "contents": new_observations
    }])

# Add user preference observations
async def record_user_preferences(user_name, preferences):
    observation_contents = []
    for category, preference in preferences.items():
        observation_contents.append(f"Prefers {preference} for {category}")

    await memory_client.add_observations([{
        "entityName": user_name,
        "contents": observation_contents
    }])
```

### Query Operations

```python
# Search for entities
async def find_destinations(search_term):
    results = await memory_client.search_nodes(search_term)
    return [node for node in results if node["type"] == "Destination"]

# Get detailed information about specific entities
async def get_trip_details(trip_name):
    nodes = await memory_client.open_nodes([trip_name])
    trip_node = nodes[0] if nodes else None
    return trip_node

# Retrieve the entire knowledge graph
async def analyze_knowledge_graph():
    graph = await memory_client.read_graph()
    return {
        "entity_count": len(graph["entities"]),
        "relation_count": len(graph["relations"]),
        "entity_types": set(e["type"] for e in graph["entities"]),
        "relation_types": set(r["type"] for r in graph["relations"])
    }
```

## Session Workflow Pattern

This pattern ensures consistent knowledge graph integration in each session:

```python
async def travel_planning_session(user_query):
    # 1. Start with knowledge retrieval
    user_preferences = await memory_client.open_nodes([user_name])
    relevant_destinations = await memory_client.search_nodes(
        query=extract_destinations(user_query)
    )

    # 2. Process user query using retrieved knowledge
    plan = await process_travel_plan(
        query=user_query,
        user_data=user_preferences,
        context=relevant_destinations
    )

    # 3. Store new knowledge discovered in this session
    new_entities = extract_new_entities(plan)
    await memory_client.create_entities(new_entities)

    new_relations = identify_relations(plan, new_entities)
    await memory_client.create_relations(new_relations)

    # 4. Update existing knowledge with new observations
    new_observations = extract_observations(plan)
    for entity_name, observations in new_observations.items():
        await memory_client.add_observations({
            "entityName": entity_name,
            "contents": observations
        })

    return plan
```

## Common Knowledge Patterns

1. **User Preference Tracking**

   ```python
   await memory_client.create_entities([{
       "name": "User:123",
       "entityType": "User",
       "observations": ["Prefers window seats", "Budget traveler"]
   }])
   ```

2. **Trip History Storage**

   ```python
   await memory_client.create_entities([{
       "name": "Trip:Barcelona-2023",
       "entityType": "Trip",
       "observations": ["7-day trip to Barcelona in July 2023", "Budget: $2000"]
   }])
   ```

3. **Destination Knowledge Base**

   ```python
   await memory_client.create_entities([{
       "name": "Barcelona",
       "entityType": "Destination",
       "observations": [
           "Located in Spain",
           "Known for architecture, beaches, and cuisine",
           "High season: June to August"
       ]
   }])
   ```

4. **Travel Patterns**
   ```python
   await memory_client.create_relations([
       {
           "from": "User:123",
           "relationType": "frequently_visits",
           "to": "Europe"
       },
       {
           "from": "User:123",
           "relationType": "prefers",
           "to": "Budget_Hotels"
       }
   ])
   ```
