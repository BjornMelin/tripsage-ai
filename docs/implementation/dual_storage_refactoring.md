# Dual Storage Pattern Refactoring

## Overview

The dual storage pattern is a key architectural component of TripSage, allowing us to store:
- Structured data in Supabase (relational database)
- Unstructured data and relationships in Neo4j (graph database via Memory MCP)

This document outlines the refactoring of this pattern to improve maintainability, testability, and extensibility.

## Previous Implementation

The previous implementation used a collection of functions in `src/utils/dual_storage.py` with specific implementations for each entity type. This approach had several limitations:

- Code duplication across entity types
- No clear interface for operations
- Difficult to extend to new entity types
- Limited testability due to tight coupling
- Lack of type safety for data validation

## New Design: Service-based Architecture

The refactored dual storage pattern uses a service-based architecture with:

1. **Abstract Base Class**: A generic `DualStorageService` class defines the interface and shared logic
2. **Entity-specific Services**: Concrete implementations for each entity type (e.g., `TripStorageService`)
3. **Standard CRUD Operations**: Create, Retrieve, Update, Delete operations for all entities
4. **Pydantic Models**: Type validation for both primary and graph data models
5. **Backwards Compatibility**: The original API is maintained for existing code

### Key Components

#### 1. `DualStorageService` (Base Class)

```python
class DualStorageService(Generic[P, G], metaclass=abc.ABCMeta):
    """Base class for dual storage services in TripSage."""
    
    # CRUD operations
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def retrieve(self, entity_id: str, include_graph: bool = False) -> Dict[str, Any]: ...
    async def update(self, entity_id: str, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def delete(self, entity_id: str) -> Dict[str, Any]: ...
    
    # Abstract methods to be implemented by subclasses
    @abc.abstractmethod
    async def _store_in_primary(self, data: Dict[str, Any]) -> str: ...
    
    @abc.abstractmethod
    async def _create_graph_entities(
        self, data: Dict[str, Any], entity_id: str
    ) -> List[Dict[str, Any]]: ...
    
    # ... other abstract methods
```

#### 2. `TripStorageService` (Concrete Implementation)

```python
class TripStorageService(DualStorageService[TripPrimaryModel, TripGraphModel]):
    """Service for storing and retrieving Trip data using the dual storage strategy."""
    
    def __init__(self):
        """Initialize the Trip Storage Service."""
        super().__init__(primary_client=db_client, graph_client=memory_client)
    
    async def _store_in_primary(self, data: Dict[str, Any]) -> str:
        """Store structured trip data in Supabase."""
        # Implementation
    
    # ... other method implementations
```

#### 3. Backwards Compatibility Layer

```python
# Create service instance
trip_service = TripStorageService()

async def store_trip_with_dual_storage(
    trip_data: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Store trip data using the dual storage strategy."""
    # Add user_id to trip_data
    trip_data["user_id"] = user_id
    
    # Use service to store trip
    result = await trip_service.create(trip_data)
    
    # Transform result to match existing API
    return {
        "trip_id": result["trip_id"],
        "entities_created": result["entities_created"],
        "relations_created": result["relations_created"],
        "supabase": result["primary_db"],
        "neo4j": result["graph_db"],
    }
```

## Benefits

1. **DRY principle**: Core logic is implemented once in the base class
2. **Type safety**: Pydantic models ensure data validation
3. **Consistent interface**: All entities use the same CRUD operations
4. **Extensibility**: New entity types can be added by implementing a new service
5. **Testability**: Services can be easily mocked and tested in isolation
6. **Clear API**: Well-defined interface for all storage operations

## Usage Example

### Creating a Trip

```python
# Old way
trip_id = await store_trip_with_dual_storage(trip_data, user_id)

# New way
trip_service = TripStorageService()
result = await trip_service.create({**trip_data, "user_id": user_id})
```

### Retrieving a Trip

```python
# Old way (was not previously implemented)
# New way
trip_service = TripStorageService()
trip = await trip_service.retrieve(trip_id)
```

## Todo

1. **Implement other entity services**:
   - UserStorageService
   - DestinationStorageService
   - AccommodationStorageService
   - ActivityStorageService

2. **Update tests**:
   - Create comprehensive test suite for the base class and all services
   - Mock dependencies for proper unit testing

3. **Documentation**:
   - Update API documentation
   - Add examples for all service operations

4. **Migration plan**:
   - Gradually migrate all code to use the new services
   - Eventually deprecate the old functions