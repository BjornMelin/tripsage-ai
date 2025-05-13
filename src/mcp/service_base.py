"""
Base service patterns for MCP implementations.

This module provides common service classes and patterns for
standardizing service layer across all MCP implementations.
"""

import abc
import inspect
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseModel

from src.utils.error_handling import MCPError, log_exception
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

# Define generic type variables
T_Request = TypeVar("T_Request", bound=BaseModel)
T_Response = TypeVar("T_Response", bound=BaseModel)
T_Entity = TypeVar("T_Entity", bound=BaseModel)


class MCPServiceOperation(str, Enum):
    """Enum for MCP service operation types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    LIST = "list"
    CUSTOM = "custom"


class MCPServiceBase(abc.ABC):
    """Base class for all MCP services.

    This abstract class defines the interface and common patterns for
    MCP service implementations, enforcing a standard approach across
    different MCP clients.
    """

    @abc.abstractmethod
    async def initialize(self) -> None:
        """Initialize the service.

        This method should be implemented by subclasses to perform
        any necessary initialization, such as establishing connections
        to external services or loading configuration.
        """
        pass

    def __init__(self, service_name: str):
        """Initialize the service.

        Args:
            service_name: Name of the service for logging
        """
        self.service_name = service_name
        self.logger = get_module_logger(f"{__name__}.{service_name}")
        self.logger.info("Initialized %s service", service_name)

        # Auto-register tool methods
        self._tool_methods = self._discover_tool_methods()

    def _discover_tool_methods(self) -> Dict[str, Callable]:
        """Discover and register all tool methods.

        This method finds all public methods that have a special
        '__is_tool__' attribute or are named with '_tool' suffix.

        Returns:
            Dictionary mapping tool names to method callables
        """
        tool_methods = {}

        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            # Skip private methods
            if name.startswith("_") and not name.endswith("_tool"):
                continue

            # Check if it's explicitly marked as a tool
            is_tool = getattr(method, "__is_tool__", False)

            # Check if it follows the naming convention
            is_tool_name = name.endswith("_tool")

            if is_tool or is_tool_name:
                tool_name = name
                if is_tool_name and not is_tool:
                    # Strip _tool suffix for the actual tool name
                    tool_name = name[:-5]

                tool_methods[tool_name] = method
                self.logger.debug("Registered tool method: %s", tool_name)

        return tool_methods

    def get_tool_methods(self) -> Dict[str, Callable]:
        """Get all registered tool methods.

        Returns:
            Dictionary mapping tool names to method callables
        """
        return self._tool_methods

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if the tool exists, False otherwise
        """
        return tool_name in self._tool_methods

    async def execute_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool

        Returns:
            Tool execution result

        Raises:
            MCPError: If the tool does not exist or fails
        """
        if not self.has_tool(tool_name):
            available_tools = ", ".join(self._tool_methods.keys())
            raise MCPError(
                f"Tool '{tool_name}' not found in service '{self.service_name}'. "
                f"Available tools: {available_tools}",
                error_type="tool_not_found",
            )

        try:
            tool_method = self._tool_methods[tool_name]
            result = await tool_method(**params)
            return result
        except Exception as e:
            self.logger.error("Error executing tool %s: %s", tool_name, str(e))
            log_exception(e)
            if isinstance(e, MCPError):
                raise
            raise MCPError(
                f"Error executing tool '{tool_name}': {str(e)}",
                error_type="tool_execution_error",
                cause=e,
            ) from e


class CRUDServiceBase(MCPServiceBase, Generic[T_Entity, T_Request, T_Response]):
    """Base class for CRUD service implementations.

    This generic class provides a standard pattern for implementing
    Create, Read, Update, Delete operations for entities.
    """

    def __init__(
        self,
        service_name: str,
        entity_type: Type[T_Entity],
        request_type: Type[T_Request],
        response_type: Type[T_Response],
    ):
        """Initialize the CRUD service.

        Args:
            service_name: Name of the service for logging
            entity_type: Pydantic model type for entities
            request_type: Pydantic model type for requests
            response_type: Pydantic model type for responses
        """
        super().__init__(service_name)
        self.entity_type = entity_type
        self.request_type = request_type
        self.response_type = response_type

    async def initialize(self) -> None:
        """Initialize the CRUD service.

        This implementation is a placeholder. Subclasses should override
        this method to perform any necessary initialization.
        """
        self.logger.info("Initializing CRUD service: %s", self.service_name)

    @abc.abstractmethod
    async def create(self, data: Union[T_Request, Dict[str, Any]]) -> T_Response:
        """Create a new entity.

        Args:
            data: Entity data to create

        Returns:
            Created entity response
        """
        pass

    @abc.abstractmethod
    async def read(self, entity_id: str) -> T_Response:
        """Read an entity by ID.

        Args:
            entity_id: ID of the entity to read

        Returns:
            Entity response
        """
        pass

    @abc.abstractmethod
    async def update(
        self, entity_id: str, data: Union[T_Request, Dict[str, Any]]
    ) -> T_Response:
        """Update an entity.

        Args:
            entity_id: ID of the entity to update
            data: Updated entity data

        Returns:
            Updated entity response
        """
        pass

    @abc.abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity.

        Args:
            entity_id: ID of the entity to delete

        Returns:
            True if successful, False otherwise
        """
        pass

    @abc.abstractmethod
    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[T_Response]:
        """List entities with optional filtering and pagination.

        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            filters: Optional filters to apply

        Returns:
            List of entity responses
        """
        pass

    async def validate_request(
        self, data: Union[T_Request, Dict[str, Any]]
    ) -> T_Request:
        """Validate and convert request data to request model.

        Args:
            data: Request data to validate

        Returns:
            Validated request model

        Raises:
            MCPError: If validation fails
        """
        try:
            if isinstance(data, dict):
                return self.request_type(**data)
            elif isinstance(data, BaseModel):
                # If it's already a Pydantic model but not the right type,
                # convert it to a dict first
                if not isinstance(data, self.request_type):
                    return self.request_type(**data.model_dump())
                return cast(T_Request, data)
            else:
                raise TypeError(f"Expected dict or Pydantic model, got {type(data)}")
        except Exception as e:
            self.logger.error("Validation error: %s", str(e))
            log_exception(e)
            raise MCPError(
                f"Invalid request data: {str(e)}",
                error_type="validation_error",
                cause=e,
            ) from e

    async def create_tool(self, **params: Any) -> Dict[str, Any]:
        """Tool wrapper for creating an entity.

        Returns:
            Create operation result
        """
        result = await self.create(params)
        return self._prepare_response(result)

    async def read_tool(self, entity_id: str) -> Dict[str, Any]:
        """Tool wrapper for reading an entity.

        Args:
            entity_id: ID of the entity to read

        Returns:
            Read operation result
        """
        result = await self.read(entity_id)
        return self._prepare_response(result)

    async def update_tool(self, entity_id: str, **params: Any) -> Dict[str, Any]:
        """Tool wrapper for updating an entity.

        Args:
            entity_id: ID of the entity to update

        Returns:
            Update operation result
        """
        result = await self.update(entity_id, params)
        return self._prepare_response(result)

    async def delete_tool(self, entity_id: str) -> Dict[str, bool]:
        """Tool wrapper for deleting an entity.

        Args:
            entity_id: ID of the entity to delete

        Returns:
            Delete operation result
        """
        success = await self.delete(entity_id)
        return {"success": success}

    async def list_tool(
        self, page: int = 1, page_size: int = 20, **filters: Any
    ) -> Dict[str, Any]:
        """Tool wrapper for listing entities.

        Args:
            page: Page number
            page_size: Items per page
            **filters: Optional filters to apply

        Returns:
            List operation result
        """
        results = await self.list(page, page_size, filters)
        return {
            "items": [self._prepare_response(item) for item in results],
            "page": page,
            "page_size": page_size,
            "total": len(results),
        }

    def _prepare_response(self, response: Any) -> Dict[str, Any]:
        """Prepare response for returning to tools.

        Args:
            response: Response object

        Returns:
            Dictionary representation of the response
        """
        if isinstance(response, dict):
            return response
        elif isinstance(response, BaseModel):
            return response.model_dump()
        else:
            return {"data": response}


class SearchServiceBase(MCPServiceBase):
    """Base class for search service implementations.

    This class provides a standard pattern for implementing
    search operations.
    """

    async def initialize(self) -> None:
        """Initialize the search service.

        This implementation is a placeholder. Subclasses should override
        this method to perform any necessary initialization.
        """
        self.logger.info("Initializing search service: %s", self.service_name)

    @abc.abstractmethod
    async def search(
        self, query: str, limit: int = 10, offset: int = 0, **options: Any
    ) -> Dict[str, Any]:
        """Search for entities.

        Args:
            query: Search query
            limit: Maximum number of results
            offset: Result offset for pagination
            **options: Additional search options

        Returns:
            Search results
        """
        pass

    async def search_tool(
        self, query: str, limit: int = 10, offset: int = 0, **options: Any
    ) -> Dict[str, Any]:
        """Tool wrapper for searching.

        Args:
            query: Search query
            limit: Maximum number of results
            offset: Result offset for pagination
            **options: Additional search options

        Returns:
            Search results
        """
        return await self.search(query, limit, offset, **options)


def mcp_tool(method: Callable) -> Callable:
    """Decorator to mark a method as an MCP tool.

    This decorator is used to explicitly mark a method as an MCP tool,
    even if it doesn't follow the naming convention.

    Args:
        method: Method to mark as a tool

    Returns:
        Decorated method
    """
    method.__is_tool__ = True
    return method
