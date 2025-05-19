# TripSage Dual Storage Implementation Guide

This document details the design, refactoring, and implementation of the dual storage pattern in the TripSage system. This pattern is a cornerstone of TripSage's architecture, enabling the system to leverage both a relational database (Supabase/Neon) for structured data and a graph database (Neo4j via Memory MCP) for unstructured data, relationships, and semantic knowledge.

## 1. Overview of the Dual Storage Pattern

The dual storage strategy in TripSage aims to:

- Store **structured data** (e.g., user profiles, trip details, bookings) in a PostgreSQL relational database (Supabase for production, Neon for development). This provides strong consistency, transactional integrity, and efficient querying for well-defined data.
- Store **unstructured data, complex relationships, and semantic knowledge** (e.g., connections between destinations, user preferences as graph patterns, travel entity relationships) in a Neo4j knowledge graph, accessed via the Memory MCP. This allows for flexible data modeling and powerful graph-based queries.

The challenge is to manage data across these two systems consistently and provide a unified way for the application (especially AI agents) to interact with them.

## 2. Initial Implementation and Its Limitations (Pre-Refactoring)

The initial approach to dual storage involved a collection of functions, often specific to each entity type (e.g., `store_trip_with_dual_storage`), typically located in utility modules like `src/utils/dual_storage.py`.

This function-based approach had several drawbacks:

- **Code Duplication**: Similar logic for creating/updating entities in both Supabase and Neo4j was repeated for different entity types.
- **Lack of Clear Interface**: No standardized contract for dual storage operations.
- **Extensibility Issues**: Adding support for new entity types was cumbersome and error-prone.
- **Limited Testability**: Tight coupling of storage logic made isolated unit testing difficult.
- **Type Safety Concerns**: Data validation was not consistently enforced across both storage systems.

## 3. Refactored Design: Service-Based Architecture

To address the limitations of the initial approach, the dual storage pattern was refactored into a more robust and maintainable service-based architecture.

### 3.1. Key Components of the Refactored Design

1. **`DualStorageService` (Abstract Base Class)**:

    - Located in a module like `src/services/storage/base_dual_storage_service.py` (adjust path as per your final structure).
    - A generic abstract base class (`abc.ABCMeta`) that defines the common interface and shared logic for all dual storage operations.
    - Uses Python generics (`Generic[P, G]`) where `P` represents the Pydantic model for the primary (relational) database entity and `G` represents the Pydantic model for the graph database entity representation or related graph data.
    - Provides standardized CRUD (Create, Retrieve, Update, Delete) method signatures.
    - Contains common orchestration logic, such as ensuring data is written to the primary store before attempting to create related graph entities.
    - Defines abstract methods (e.g., `_store_in_primary`, `_retrieve_from_primary`, `_create_graph_entities`, `_link_to_graph_entities`) that must be implemented by concrete entity-specific services.

    ```python
    # Conceptual structure of DualStorageService
    import abc
    from typing import Generic, TypeVar, Dict, Any, List, Optional
    from pydantic import BaseModel
    # Assuming MCP clients for database and memory graph
    # from src.mcp.database_mcp_client import DatabaseMCPClient # Placeholder
    # from src.mcp.memory_client import MemoryClient # Placeholder

    P = TypeVar('P', bound=BaseModel) # Primary DB Pydantic Model
    G = TypeVar('G', bound=BaseModel) # Graph DB Pydantic Model (or related data model)

    class DualStorageService(Generic[P, G], metaclass=abc.ABCMeta):
        def __init__(self, primary_client: Any, graph_client: Any, entity_name: str):
            self.primary_client = primary_client # e.g., Supabase/Neon MCP client
            self.graph_client = graph_client   # e.g., Memory MCP client
            self.entity_name = entity_name
            # self.logger = get_module_logger(__name__) # Assuming a logger utility

        async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
            # self.logger.info(f"Creating {self.entity_name} with data: {data}")
            primary_id = await self._store_in_primary(data)
            # self.logger.info(f"Stored {self.entity_name} in primary DB with ID: {primary_id}")

            graph_entities_created = await self._create_graph_entities(data, primary_id)
            # self.logger.info(f"Created {len(graph_entities_created)} graph entities for {self.entity_name} ID: {primary_id}")

            # Potentially link primary entity to other existing graph entities
            # graph_relations_created = await self._link_to_graph_entities(data, primary_id)

            return {
                f"{self.entity_name.lower()}_id": primary_id,
                "primary_db_status": "success",
                "graph_db_entities_created": graph_entities_created,
                # "graph_db_relations_created": graph_relations_created
            }

        async def retrieve(self, entity_id: str, include_graph_data: bool = False) -> Optional[Dict[str, Any]]:
            primary_data = await self._retrieve_from_primary(entity_id)
            if not primary_data:
                return None

            response = {"primary_data": primary_data}
            if include_graph_data:
                graph_data = await self._retrieve_from_graph(entity_id)
                response["graph_data"] = graph_data
            return response

        async def update(self, entity_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            updated_primary_data = await self._update_in_primary(entity_id, data)
            if not updated_primary_data:
                return None # Or raise error

            await self._update_in_graph(entity_id, data)

            return {"primary_data": updated_primary_data, "graph_update_status": "success"}


        async def delete(self, entity_id: str) -> bool:
            deleted_from_primary = await self._delete_from_primary(entity_id)
            if not deleted_from_primary:
                return False # Or raise error

            await self._delete_from_graph(entity_id)
            return True

        @abc.abstractmethod
        async def _store_in_primary(self, data: Dict[str, Any]) -> str: # Returns primary_id
            pass

        @abc.abstractmethod
        async def _retrieve_from_primary(self, entity_id: str) -> Optional[Dict[str, Any]]:
            pass

        @abc.abstractmethod
        async def _update_in_primary(self, entity_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            pass

        @abc.abstractmethod
        async def _delete_from_primary(self, entity_id: str) -> bool:
            pass

        @abc.abstractmethod
        async def _create_graph_entities(self, primary_data: Dict[str, Any], primary_id: str) -> List[Dict[str, Any]]:
            pass

        @abc.abstractmethod
        async def _retrieve_from_graph(self, primary_id: str) -> Optional[Dict[str, Any]]: # Or specific graph model
            pass

        @abc.abstractmethod
        async def _update_in_graph(self, primary_id: str, primary_data_update: Dict[str, Any]) -> None:
            pass

        @abc.abstractmethod
        async def _delete_from_graph(self, primary_id: str) -> None:
            pass

        # Optional: Abstract method for linking to existing graph entities
        # @abc.abstractmethod
        # async def _link_to_graph_entities(self, primary_data: Dict[str, Any], primary_id: str) -> List[Dict[str, Any]]:
        #     pass
    ```

2. **Entity-Specific Services** (e.g., `TripStorageService`):

    - Concrete classes that inherit from `DualStorageService`.
    - Each service is responsible for a specific entity type (e.g., Trips, Users, Accommodations).
    - Implements the abstract methods defined in the base class, providing the specific logic for how that entity is stored and represented in both Supabase and Neo4j.
    - Uses Pydantic models for data validation specific to the entity for both primary and graph representations.

    ```python
    # Example: src/services/storage/trip_storage_service.py
    # from .base_dual_storage_service import DualStorageService, P, G # P, G would be Trip specific models
    # from ...models.trip import TripPrimaryModel, TripGraphModel # Example Pydantic models
    # from ...mcp.database_mcp_client import db_client # Placeholder for actual DB MCP client
    # from ...mcp.memory_client import memory_client # Placeholder for actual Memory MCP client

    # class TripStorageService(DualStorageService[TripPrimaryModel, TripGraphModel]):
    #     def __init__(self):
    #         super().__init__(
    #             primary_client=db_client, # Actual initialized client
    #             graph_client=memory_client, # Actual initialized client
    #             entity_name="Trip"
    #         )

    #     async def _store_in_primary(self, data: Dict[str, Any]) -> str:
    #         # Validate with TripPrimaryModel.model_validate(data)
    #         # Logic to insert/update trip data in Supabase using self.primary_client
    #         # Example: trip_record = await self.primary_client.table("trips").insert(validated_data).execute()
    #         # return trip_record.data['id']
    #         pass # Replace with actual implementation

    #     async def _retrieve_from_primary(self, entity_id: str) -> Optional[Dict[str, Any]]:
    #         # Logic to get trip from Supabase
    #         # Example: response = await self.primary_client.table("trips").select("*").eq("id", entity_id).single().execute()
    #         # return response.data
    #         pass

    #     async def _update_in_primary(self, entity_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    #         # Logic to update trip in Supabase
    #         pass

    #     async def _delete_from_primary(self, entity_id: str) -> bool:
    #         # Logic to delete trip from Supabase
    #         pass

    #     async def _create_graph_entities(self, primary_data: Dict[str, Any], primary_id: str) -> List[Dict[str, Any]]:
    #         # Logic to create corresponding trip node and related nodes/relationships in Neo4j
    #         # using self.graph_client (Memory MCP client)
    #         # Example:
    #         # trip_entity = { "name": f"Trip:{primary_id}", "entityType": "Trip", "observations": [f"Destination: {primary_data['destination']}"] }
    #         # destination_entity = { "name": primary_data['destination'], "entityType": "Destination", "observations": [] }
    #         # await self.graph_client.create_entities([trip_entity, destination_entity])
    #         # await self.graph_client.create_relations([{ "from": f"Trip:{primary_id}", "relationType": "HAS_DESTINATION", "to": primary_data['destination']}])
    #         # return [trip_entity, destination_entity]
    #         pass

    #     async def _retrieve_from_graph(self, primary_id: str) -> Optional[Dict[str, Any]]:
    #         # Logic to get trip related data from Neo4j
    #         # Example: nodes = await self.graph_client.open_nodes([f"Trip:{primary_id}"])
    #         # return nodes if nodes else None
    #         pass

    #     async def _update_in_graph(self, primary_id: str, primary_data_update: Dict[str, Any]) -> None:
    #         # Logic to update trip related data in Neo4j
    #         # Example:
    #         # observations_to_add = []
    #         # if 'description' in primary_data_update:
    #         #     observations_to_add.append(f"Updated description: {primary_data_update['description']}")
    #         # if observations_to_add:
    #         #    await self.graph_client.add_observations(f"Trip:{primary_id}", observations_to_add)
    #         pass

    #     async def _delete_from_graph(self, primary_id: str) -> None:
    #         # Logic to delete trip related data from Neo4j
    #         # Example: await self.graph_client.delete_entities([f"Trip:{primary_id}"])
    #         pass

    # # trip_storage_service = TripStorageService() # Singleton instance
    ```

3. **Simplified Access Module** (e.g., `src/utils/dual_storage.py` or `src/services/storage/__init__.py`):

    - This module now primarily instantiates and exports the specific storage service instances (like `trip_service = TripStorageService()`).
    - Client code (e.g., agent tools) imports the service instance directly.

    ```python
    # Example: src/services/storage/__init__.py
    # from .trip_storage_service import TripStorageService
    # # Import other storage services as they are created
    # # from .user_storage_service import UserStorageService

    # trip_service = TripStorageService()
    # # user_service = UserStorageService()

    # __all__ = ["trip_service",
    #            # "user_service"
    #           ]
    ```

### 3.2. Client Code Updates

Agent tools and other parts of the application that interact with dual storage now use the new service instances.

**Old Way (Conceptual):**

```python
# result = await store_trip_with_dual_storage_function(trip_data, user_id)
```

**New Way:**

```python
from src.services.storage import trip_service # Assuming __init__.py exports it

# result = await trip_service.create({**trip_data, "user_id": user_id})
# trip_details = await trip_service.retrieve(trip_id="some_trip_id", include_graph_data=True)
```

## 4. Benefits of the Refactored Pattern

- **DRY (Don't Repeat Yourself)**: Core dual storage logic (e.g., orchestration of writes, error handling patterns) is implemented once in the `DualStorageService` base class.
- **Improved Type Safety**: Pydantic models are used within each service to validate data for both primary (SQL) and graph (Neo4j) representations, catching errors early.
- **Consistent Interface**: All entity types managed by dual storage will share the same CRUD API (create, retrieve, update, delete), making the system more predictable and easier to use.
- **Enhanced Extensibility**: Adding dual storage support for a new entity type (e.g., "User", "Destination") primarily involves:
  1. Defining its Pydantic models for primary and graph data.
  2. Creating a new service class that inherits from `DualStorageService`.
  3. Implementing the entity-specific abstract methods.
- **Increased Testability**: Entity-specific services can be unit-tested in isolation by mocking their `primary_client` and `graph_client` dependencies. The `DualStorageService` base class can also be tested with mock concrete implementations. The isolated testing pattern is particularly useful here.
- **Clearer API**: The service-based approach provides a well-defined and discoverable API for all storage operations related to an entity.

## 5. Status and Future Work (as of Refactoring Completion)

- **Completed**:
  - `DualStorageService` abstract base class created.
  - `TripStorageService` concrete implementation for Trip entities developed.
  - Original `dual_storage.py` module simplified to expose the `TripStorageService` instance.
  - Client code (e.g., Travel Agent's `create_trip` tool) updated to use the new `TripStorageService`.
  - Isolated testing pattern established for dual storage services.
- **Future Work**:
  - Implement additional entity-specific storage services:
    - `UserStorageService`
    - `DestinationStorageService`
    - `AccommodationStorageService`
    - `ActivityStorageService`
  - Enhance test coverage for each new service and the base class.
  - Refine data synchronization strategies between Supabase and Neo4j within the services.
  - Develop comprehensive documentation and usage examples for each service.

## 6. Conclusion

The refactoring of the dual storage pattern from a function-based approach to a service-based architecture marks a significant improvement in the maintainability, testability, and extensibility of TripSage's data persistence layer. This new structure adheres to SOLID principles, promotes code reuse, and provides a clear and consistent interface for managing entities across both Supabase (PostgreSQL) and Neo4j. This robust foundation will support the continued growth and complexity of the TripSage application.
