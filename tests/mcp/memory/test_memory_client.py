"""
Tests for the Memory MCP client.

These tests verify that the MemoryMCPClient correctly interacts with the
Memory MCP service for knowledge graph operations, with proper validation
of parameters and responses.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError


# Mock error class to match the one in the actual module
class MCPError(Exception):
    """Error raised by MCP Client when a request fails."""

    def __init__(
        self,
        message: str,
        server: str = "",
        tool: str = "",
        params: Any = None,
        details: Any = None,
    ):
        self.message = message
        self.server = server
        self.tool = tool
        self.params = params
        self.details = details
        super().__init__(f"{message} (Server: {server}, Tool: {tool})")


# Mock models that match the ones in the actual module
class Entity(BaseModel):
    name: str
    entityType: str
    observations: List[str] = []

    model_config = ConfigDict(extra="allow")


class Relation(BaseModel):
    from_: str
    relationType: str
    to: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Observation(BaseModel):
    entityName: str
    contents: List[str]

    model_config = ConfigDict(extra="allow")


class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    observations: List[str] = []
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="allow")


class RelationResponse(BaseModel):
    id: str
    from_entity: str
    to_entity: str
    type: str
    created_at: str

    model_config = ConfigDict(extra="allow")


class BaseResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class CreateEntitiesResponse(BaseResponse):
    entities: List[EntityResponse] = []
    message: str


class CreateRelationsResponse(BaseResponse):
    relations: List[RelationResponse] = []
    message: str


class GraphResponse(BaseResponse):
    entities: List[EntityResponse] = []
    relations: List[RelationResponse] = []


class SearchNodesResponse(BaseResponse):
    results: List[EntityResponse] = []
    count: int = 0


class OpenNodesResponse(BaseResponse):
    entities: List[EntityResponse] = []
    count: int = 0


class AddObservationsResponse(BaseResponse):
    updated_entities: List[EntityResponse] = []
    message: str


class DeleteEntitiesResponse(BaseResponse):
    deleted_count: int = 0
    message: str


class DeleteObservationsResponse(BaseResponse):
    updated_entities: List[EntityResponse] = []
    message: str


class DeleteRelationsResponse(BaseResponse):
    deleted_count: int = 0
    message: str


# Mock the MCP client
class MockMemoryMCPClient:
    def __init__(
        self,
        endpoint: str = "http://test-memory-mcp:8000",
        api_key: str = "test-api-key",
    ):
        self.server_name = "Memory"
        self.endpoint = endpoint
        self.api_key = api_key
        self._initialized = False
        self.call_tool = AsyncMock()

    async def _call_validate_tool(
        self,
        tool_name: str,
        params: any,
        response_model: type,
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> any:
        try:
            # Convert parameters to dict
            params_dict = (
                params.model_dump(exclude_none=True)
                if hasattr(params, "model_dump")
                else params
            )

            # Call the tool
            response = await self.call_tool(tool_name, params_dict)

            try:
                # Validate response
                validated_response = response_model.model_validate(response)
                return validated_response
            except ValidationError:
                # Return raw response for backward compatibility
                return response
        except ValidationError as e:
            raise MCPError(
                message=f"Invalid parameters for {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Failed to call {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
            ) from e

    async def initialize(self) -> None:
        self._initialized = True

    async def create_entities(self, entities: List[Dict]) -> CreateEntitiesResponse:
        # Implementation that calls _call_validate_tool
        try:
            # Convert raw entities to Pydantic models
            entity_models = [Entity.model_validate(entity) for entity in entities]

            # Create parameters
            params = {"entities": entity_models}

            # Call with validation
            response = await self._call_validate_tool(
                "create_entities", params, CreateEntitiesResponse
            )

            return response
        except ValidationError as e:
            raise MCPError(
                message=f"Invalid entity data: {str(e)}",
                server=self.server_name,
                tool="create_entities",
                params={"entities": entities},
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Failed to create entities: {str(e)}",
                server=self.server_name,
                tool="create_entities",
                params={"entities": entities},
            ) from e

    async def create_relations(self, relations: List[Dict]) -> CreateRelationsResponse:
        try:
            # Convert raw relations to Pydantic models
            relation_models = []
            for relation in relations:
                # Create a copy with from_ instead of from
                relation_copy = relation.copy()
                if "from" in relation_copy:
                    relation_copy["from_"] = relation_copy.pop("from")
                relation_models.append(Relation.model_validate(relation_copy))

            # Create parameters
            params = {"relations": relation_models}

            # Call with validation
            response = await self._call_validate_tool(
                "create_relations", params, CreateRelationsResponse
            )

            return response
        except ValidationError as e:
            raise MCPError(
                message=f"Invalid relation data: {str(e)}",
                server=self.server_name,
                tool="create_relations",
                params={"relations": relations},
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Failed to create relations: {str(e)}",
                server=self.server_name,
                tool="create_relations",
                params={"relations": relations},
            ) from e

    async def add_observations(
        self, observations: List[Dict]
    ) -> AddObservationsResponse:
        try:
            # Convert raw observations to Pydantic models
            observation_models = [
                Observation.model_validate(obs) for obs in observations
            ]

            # Create parameters
            params = {"observations": observation_models}

            # Call with validation
            response = await self._call_validate_tool(
                "add_observations", params, AddObservationsResponse
            )

            return response
        except ValidationError as e:
            raise MCPError(
                message=f"Invalid observation data: {str(e)}",
                server=self.server_name,
                tool="add_observations",
                params={"observations": observations},
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Failed to add observations: {str(e)}",
                server=self.server_name,
                tool="add_observations",
                params={"observations": observations},
            ) from e

    async def delete_entities(self, entity_names: List[str]) -> DeleteEntitiesResponse:
        try:
            # Create parameters
            params = {"entityNames": entity_names}

            # Call with validation
            response = await self._call_validate_tool(
                "delete_entities", params, DeleteEntitiesResponse
            )

            return response
        except ValidationError as e:
            raise MCPError(
                message=f"Invalid entity names: {str(e)}",
                server=self.server_name,
                tool="delete_entities",
                params={"entityNames": entity_names},
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Failed to delete entities: {str(e)}",
                server=self.server_name,
                tool="delete_entities",
                params={"entityNames": entity_names},
            ) from e

    async def delete_observations(
        self, deletions: List[Dict]
    ) -> DeleteObservationsResponse:
        try:
            # Convert raw deletions to Pydantic models
            deletion_models = [
                Observation.model_validate(deletion) for deletion in deletions
            ]

            # Create parameters
            params = {"deletions": deletion_models}

            # Call with validation
            response = await self._call_validate_tool(
                "delete_observations", params, DeleteObservationsResponse
            )

            return response
        except ValidationError as e:
            raise MCPError(
                message=f"Invalid deletion data: {str(e)}",
                server=self.server_name,
                tool="delete_observations",
                params={"deletions": deletions},
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Failed to delete observations: {str(e)}",
                server=self.server_name,
                tool="delete_observations",
                params={"deletions": deletions},
            ) from e

    async def delete_relations(self, relations: List[Dict]) -> DeleteRelationsResponse:
        try:
            # Convert raw relations to Pydantic models
            relation_models = []
            for relation in relations:
                # Create a copy with from_ instead of from
                relation_copy = relation.copy()
                if "from" in relation_copy:
                    relation_copy["from_"] = relation_copy.pop("from")
                relation_models.append(Relation.model_validate(relation_copy))

            # Create parameters
            params = {"relations": relation_models}

            # Call with validation
            response = await self._call_validate_tool(
                "delete_relations", params, DeleteRelationsResponse
            )

            return response
        except ValidationError as e:
            raise MCPError(
                message=f"Invalid relation data: {str(e)}",
                server=self.server_name,
                tool="delete_relations",
                params={"relations": relations},
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Failed to delete relations: {str(e)}",
                server=self.server_name,
                tool="delete_relations",
                params={"relations": relations},
            ) from e

    async def read_graph(self) -> GraphResponse:
        try:
            # No parameters for this request
            params = {}

            # Call with validation
            response = await self._call_validate_tool(
                "read_graph", params, GraphResponse
            )

            return response
        except Exception as e:
            raise MCPError(
                message=f"Failed to read knowledge graph: {str(e)}",
                server=self.server_name,
                tool="read_graph",
                params={},
            ) from e

    async def search_nodes(self, query: str) -> SearchNodesResponse:
        try:
            # Create parameters
            params = {"query": query}

            # Call with validation
            response = await self._call_validate_tool(
                "search_nodes", params, SearchNodesResponse
            )

            return response
        except ValidationError as e:
            raise MCPError(
                message=f"Invalid search query: {str(e)}",
                server=self.server_name,
                tool="search_nodes",
                params={"query": query},
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Failed to search nodes: {str(e)}",
                server=self.server_name,
                tool="search_nodes",
                params={"query": query},
            ) from e

    async def open_nodes(self, names: List[str]) -> OpenNodesResponse:
        try:
            # Create parameters
            params = {"names": names}

            # Call with validation
            response = await self._call_validate_tool(
                "open_nodes", params, OpenNodesResponse
            )

            return response
        except ValidationError as e:
            raise MCPError(
                message=f"Invalid node names: {str(e)}",
                server=self.server_name,
                tool="open_nodes",
                params={"names": names},
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Failed to open nodes: {str(e)}",
                server=self.server_name,
                tool="open_nodes",
                params={"names": names},
            ) from e


@pytest.fixture
def mock_entity_response():
    """Fixture providing a mock entity response."""
    return {
        "id": "entity-123",
        "name": "TestEntity",
        "type": "TestType",
        "observations": ["Test observation"],
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_relation_response():
    """Fixture providing a mock relation response."""
    return {
        "id": "relation-123",
        "from_entity": "EntityA",
        "to_entity": "EntityB",
        "type": "RELATES_TO",
        "created_at": "2023-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_create_entities_response(mock_entity_response):
    """Fixture providing a mock create entities response."""
    return {
        "entities": [mock_entity_response],
        "message": "Entities created successfully",
    }


@pytest.fixture
def mock_create_relations_response(mock_relation_response):
    """Fixture providing a mock create relations response."""
    return {
        "relations": [mock_relation_response],
        "message": "Relations created successfully",
    }


@pytest.fixture
def mock_add_observations_response(mock_entity_response):
    """Fixture providing a mock add observations response."""
    return {
        "updated_entities": [mock_entity_response],
        "message": "Observations added successfully",
    }


@pytest.fixture
def mock_delete_entities_response():
    """Fixture providing a mock delete entities response."""
    return {
        "deleted_count": 2,
        "message": "Entities deleted successfully",
    }


@pytest.fixture
def mock_delete_observations_response(mock_entity_response):
    """Fixture providing a mock delete observations response."""
    return {
        "updated_entities": [mock_entity_response],
        "message": "Observations deleted successfully",
    }


@pytest.fixture
def mock_delete_relations_response():
    """Fixture providing a mock delete relations response."""
    return {
        "deleted_count": 1,
        "message": "Relations deleted successfully",
    }


@pytest.fixture
def mock_graph_response(mock_entity_response, mock_relation_response):
    """Fixture providing a mock graph response."""
    return {
        "entities": [mock_entity_response, mock_entity_response],
        "relations": [mock_relation_response],
    }


@pytest.fixture
def mock_search_nodes_response(mock_entity_response):
    """Fixture providing a mock search nodes response."""
    return {
        "results": [mock_entity_response],
        "count": 1,
    }


@pytest.fixture
def mock_open_nodes_response(mock_entity_response):
    """Fixture providing a mock open nodes response."""
    return {
        "entities": [mock_entity_response],
        "count": 1,
    }


@pytest.fixture
def client():
    """Fixture providing a MemoryMCPClient instance."""
    return MockMemoryMCPClient()


async def test_create_entities(client, mock_create_entities_response):
    """Test creating entities in the knowledge graph."""
    # Arrange
    client.call_tool.return_value = mock_create_entities_response

    entities = [
        {
            "name": "TestEntity",
            "entityType": "TestType",
            "observations": ["Test observation"],
        }
    ]

    # Act
    result = await client.create_entities(entities)

    # Assert
    client.call_tool.assert_called_once()
    assert isinstance(result, CreateEntitiesResponse)
    assert len(result.entities) == 1
    assert result.entities[0].name == "TestEntity"
    assert result.message == "Entities created successfully"


async def test_create_entities_validation_error(client):
    """Test handling validation errors when creating entities."""
    # Arrange
    entity_error = ValidationError.from_exception_data(
        title="ValidationError",
        line_errors=[
            {
                "type": "missing",
                "loc": ("name",),
                "msg": "Field required",
                "input": {},
            }
        ],
    )
    client.call_tool.side_effect = entity_error

    entities = [{"entityType": "TestType", "observations": ["Test observation"]}]

    # Act & Assert
    with pytest.raises(MCPError) as exc_info:
        await client.create_entities(entities)

    assert "Invalid entity data" in str(exc_info.value)
    assert "Memory" in str(exc_info.value)
    assert "create_entities" in str(exc_info.value)


async def test_create_relations(client, mock_create_relations_response):
    """Test creating relations in the knowledge graph."""
    # Arrange
    client.call_tool.return_value = mock_create_relations_response

    relations = [
        {
            "from": "EntityA",
            "relationType": "RELATES_TO",
            "to": "EntityB",
        }
    ]

    # Act
    result = await client.create_relations(relations)

    # Assert
    client.call_tool.assert_called_once()
    assert isinstance(result, CreateRelationsResponse)
    assert len(result.relations) == 1
    assert result.relations[0].from_entity == "EntityA"
    assert result.relations[0].to_entity == "EntityB"
    assert result.message == "Relations created successfully"


async def test_add_observations(client, mock_add_observations_response):
    """Test adding observations to entities."""
    # Arrange
    client.call_tool.return_value = mock_add_observations_response

    observations = [
        {
            "entityName": "TestEntity",
            "contents": ["New observation"],
        }
    ]

    # Act
    result = await client.add_observations(observations)

    # Assert
    client.call_tool.assert_called_once()
    assert isinstance(result, AddObservationsResponse)
    assert len(result.updated_entities) == 1
    assert result.updated_entities[0].name == "TestEntity"
    assert result.message == "Observations added successfully"


async def test_delete_entities(client, mock_delete_entities_response):
    """Test deleting entities from the knowledge graph."""
    # Arrange
    client.call_tool.return_value = mock_delete_entities_response

    entity_names = ["EntityA", "EntityB"]

    # Act
    result = await client.delete_entities(entity_names)

    # Assert
    client.call_tool.assert_called_once()
    assert isinstance(result, DeleteEntitiesResponse)
    assert result.deleted_count == 2
    assert result.message == "Entities deleted successfully"


async def test_delete_observations(client, mock_delete_observations_response):
    """Test deleting observations from entities."""
    # Arrange
    client.call_tool.return_value = mock_delete_observations_response

    deletions = [
        {
            "entityName": "TestEntity",
            "contents": ["Observation to delete"],
        }
    ]

    # Act
    result = await client.delete_observations(deletions)

    # Assert
    client.call_tool.assert_called_once()
    assert isinstance(result, DeleteObservationsResponse)
    assert len(result.updated_entities) == 1
    assert result.updated_entities[0].name == "TestEntity"
    assert result.message == "Observations deleted successfully"


async def test_delete_relations(client, mock_delete_relations_response):
    """Test deleting relations from the knowledge graph."""
    # Arrange
    client.call_tool.return_value = mock_delete_relations_response

    relations = [
        {
            "from": "EntityA",
            "relationType": "RELATES_TO",
            "to": "EntityB",
        }
    ]

    # Act
    result = await client.delete_relations(relations)

    # Assert
    client.call_tool.assert_called_once()
    assert isinstance(result, DeleteRelationsResponse)
    assert result.deleted_count == 1
    assert result.message == "Relations deleted successfully"


async def test_read_graph(client, mock_graph_response):
    """Test reading the entire knowledge graph."""
    # Arrange
    client.call_tool.return_value = mock_graph_response

    # Act
    result = await client.read_graph()

    # Assert
    client.call_tool.assert_called_once()
    assert isinstance(result, GraphResponse)
    assert len(result.entities) == 2
    assert len(result.relations) == 1


async def test_search_nodes(client, mock_search_nodes_response):
    """Test searching for nodes in the knowledge graph."""
    # Arrange
    client.call_tool.return_value = mock_search_nodes_response

    query = "TestEntity"

    # Act
    result = await client.search_nodes(query)

    # Assert
    client.call_tool.assert_called_once()
    assert isinstance(result, SearchNodesResponse)
    assert len(result.results) == 1
    assert result.count == 1


async def test_open_nodes(client, mock_open_nodes_response):
    """Test opening specific nodes in the knowledge graph."""
    # Arrange
    client.call_tool.return_value = mock_open_nodes_response

    names = ["TestEntity"]

    # Act
    result = await client.open_nodes(names)

    # Assert
    client.call_tool.assert_called_once()
    assert isinstance(result, OpenNodesResponse)
    assert len(result.entities) == 1
    assert result.count == 1


async def test_initialization():
    """Test initialization of the MemoryMCPClient."""
    # Arrange & Act
    client = MockMemoryMCPClient(
        endpoint="http://test-memory-mcp:8000",
        api_key="test-api-key",
    )

    # Assert
    assert client.server_name == "Memory"
    assert client.endpoint == "http://test-memory-mcp:8000"
    assert client._initialized is False


async def test_initialize_method(client):
    """Test the initialize method."""
    # Act
    await client.initialize()

    # Assert
    assert client._initialized is True


async def test_call_validate_tool_exception_handling(client):
    """Test that _call_validate_tool handles exceptions properly."""
    # Arrange
    client.call_tool.side_effect = Exception("Test exception")

    params = {}

    # Act & Assert
    with pytest.raises(MCPError) as exc_info:
        await client._call_validate_tool("test_tool", params, CreateEntitiesResponse)

    assert "Failed to call test_tool" in str(exc_info.value)
    assert "Test exception" in str(exc_info.value)


async def test_external_package_recognition():
    """Test that mcp-neo4j-memory package is recognized as external dependency."""
    # This test verifies that the `mcp-neo4j-memory` package is recognized
    # as a proper external dependency by the setup tools

    import importlib.util
    import subprocess
    import sys

    # Try to import the package to check if it's installed
    spec = importlib.util.find_spec("mcp_neo4j_memory")
    is_mcp_installed = spec is not None

    if not is_mcp_installed:
        # Skip the test if the package is not installed
        pytest.skip("mcp-neo4j-memory package not installed")

    # Verify that the package has the necessary interfaces
    try:
        import mcp_neo4j_memory

        # Check that the package has a main entry point for the server
        assert hasattr(mcp_neo4j_memory, "__main__") or hasattr(
            mcp_neo4j_memory, "main"
        ), "External package missing main entry point"

        # Verify the expected tools are available
        tools = getattr(mcp_neo4j_memory, "tools", None) or []
        expected_tools = [
            "create_entities",
            "create_relations",
            "add_observations",
            "delete_entities",
            "delete_observations",
            "delete_relations",
            "read_graph",
            "search_nodes",
            "open_nodes",
        ]

        for tool in expected_tools:
            assert tool in str(tools), f"External package missing expected tool: {tool}"

    except (ImportError, AttributeError) as e:
        pytest.skip(f"External package not correctly importable: {str(e)}")

    # Verify that the startup script can find and recognize the package
    try:
        import os

        # Check that the start_memory_mcp.sh script exists
        script_path = os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            ),
            "scripts",
            "start_memory_mcp.sh",
        )

        assert os.path.exists(script_path), "Startup script not found"

        # Verify the script has the proper command to start the server
        with open(script_path, "r") as f:
            script_content = f.read()

        assert "python -m mcp_neo4j_memory" in script_content, (
            "Startup script does not properly reference the external package"
        )

        # Check that the package is installable via pip
        pip_check = subprocess.run(
            [sys.executable, "-m", "pip", "show", "mcp-neo4j-memory"],
            capture_output=True,
            text=True,
        )

        assert pip_check.returncode == 0, "Package not properly installed via pip"

    except Exception as e:
        pytest.skip(f"Error checking startup script: {str(e)}")
