"""Base service class for TripSage business services.

This module provides a standardized base class for all business services in TripSage,
implementing common patterns for dependency injection, logging, error handling,
and external service initialization.
"""

import logging
from typing import Any, TypeVar

from tripsage_core.exceptions import CoreServiceError, CoreTripSageError
from tripsage_core.utils.decorator_utils import with_error_handling


ServiceType = TypeVar("ServiceType")


class BaseService:
    """Base class for all TripSage business services.

    This class provides a standardized foundation for business services with:
    - Dependency injection for database and external services
    - Standardized logging setup
    - Common error handling patterns
    - Service initialization lifecycle management

    All business services should inherit from this class to ensure consistency
    and reduce code duplication across the service layer.

    Example:
        ```python
        from tripsage_core.services.base_service import BaseService
        from tripsage_core.services.infrastructure.database_service import (
            DatabaseService,
        )

        class UserService(BaseService):
            def __init__(
                self,
                database_service: Optional[DatabaseService] = None,
                external_service_module: str = "external_apis.user_api",
                external_service_class: str = "UserAPIClient"
            ):
                super().__init__(
                    database_service=database_service,
                    external_service_module=external_service_module,
                    external_service_class=external_service_class
                )

            @with_error_handling(operation_name="create_user")
            async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
                # Service implementation
                return await self.db.create_user(user_data)
        ```
    """

    def __init__(
        self,
        database_service: Any | None = None,
        *,
        external_service_module: str | None = None,
        external_service_class: str | None = None,
        cache_service: Any | None = None,
        service_name: str | None = None,
    ):
        """Initialize the base service with dependency injection.

        Args:
            database_service: Database service instance (auto-injected if None)
            external_service_module: Module path for external service
            external_service_class: Class name for external service
            cache_service: Cache service instance (auto-injected if None)
            service_name: Custom service name for logging (defaults to class name)
        """
        # Set up service identification
        self.service_name = service_name or self.__class__.__name__

        # Initialize logger with service-specific configuration
        self.logger = self._setup_logger()

        # Initialize dependencies
        self.db = self._initialize_database_service(database_service)
        self.cache = self._initialize_cache_service(cache_service)
        self.external_service = self._initialize_external_service(
            external_service_module, external_service_class
        )

        # Log successful initialization
        self.logger.info(
            "Service initialized: %s",
            self.service_name,
            extra={
                "service": self.service_name,
                "has_database": self.db is not None,
                "has_cache": self.cache is not None,
                "has_external_service": self.external_service is not None,
            },
        )

    def _setup_logger(self) -> logging.Logger:
        """Set up service-specific logger with proper configuration.

        Returns:
            Configured logger instance for this service
        """
        logger = logging.getLogger(f"{self.__module__}.{self.service_name}")

        # Ensure logger has proper level if not already configured
        if not logger.handlers and not logger.level:
            logger.setLevel(logging.INFO)

        return logger

    def _initialize_database_service(self, service: Any | None) -> Any | None:
        """Initialize database service with dependency injection pattern.

        Args:
            service: Optional pre-configured database service

        Returns:
            Database service instance or None if initialization fails
        """
        if service is not None:
            return service

        try:
            # Use lazy import to avoid circular dependencies
            from tripsage_core.services.infrastructure.database_service import (
                DatabaseService,
            )

            database_service = DatabaseService()
            self.logger.debug("Database service initialized")
            return database_service

        except ImportError as e:
            self.logger.warning(
                "Database service not available: %s",
                e,
                extra={"service": self.service_name, "error": str(e)},
            )
            return None
        except CoreTripSageError as error:
            self.logger.exception(
                "Failed to initialize database service",
                extra={"service": self.service_name, "error": str(error)},
            )
            return None
        except (RuntimeError, ValueError, OSError) as error:
            self.logger.exception(
                "Failed to initialize database service",
                extra={"service": self.service_name, "error": str(error)},
            )
            return None

    def _initialize_cache_service(self, service: Any | None) -> Any | None:
        """Initialize cache service with dependency injection pattern.

        Args:
            service: Optional pre-configured cache service

        Returns:
            Cache service instance or None if initialization fails
        """
        if service is not None:
            return service

        try:
            # Use lazy import to avoid circular dependencies
            from tripsage_core.services.infrastructure.cache_service import CacheService

            cache_service = CacheService()
            self.logger.debug("Cache service initialized")
            return cache_service

        except ImportError as e:
            self.logger.warning(
                "Cache service not available: %s",
                e,
                extra={"service": self.service_name, "error": str(e)},
            )
            return None
        except CoreTripSageError as error:
            self.logger.exception(
                "Failed to initialize cache service",
                extra={"service": self.service_name, "error": str(error)},
            )
            return None
        except (RuntimeError, ValueError, OSError) as error:
            self.logger.exception(
                "Failed to initialize cache service",
                extra={"service": self.service_name, "error": str(error)},
            )
            return None

    def _initialize_external_service(
        self, module_name: str | None, class_name: str | None
    ) -> Any | None:
        """Initialize external service with dynamic import pattern.

        Args:
            module_name: Python module path for the external service
            class_name: Class name within the module

        Returns:
            External service instance or None if initialization fails
        """
        if not module_name or not class_name:
            return None

        try:
            # Dynamic import of external service
            if "." in module_name:
                # Handle module paths like "tripsage_core.services.external_apis"
                module = __import__(module_name, fromlist=[class_name])
            else:
                # Handle simple module names
                module = __import__(module_name)

            service_class = getattr(module, class_name)
            external_service = service_class()

            self.logger.debug(
                "External service initialized: %s",
                class_name,
                extra={"service": self.service_name, "external_service": class_name},
            )
            return external_service

        except ImportError as e:
            self.logger.warning(
                "External service %s not available: %s",
                class_name,
                e,
                extra={
                    "service": self.service_name,
                    "external_service": class_name,
                    "error": str(e),
                },
            )
            return None
        except AttributeError as e:
            self.logger.warning(
                "External service class %s not found in %s: %s",
                class_name,
                module_name,
                e,
                extra={
                    "service": self.service_name,
                    "external_service": class_name,
                    "module": module_name,
                    "error": str(e),
                },
            )
            return None
        except CoreTripSageError as error:
            self.logger.exception(
                "Failed to initialize external service %s",
                class_name,
                extra={
                    "service": self.service_name,
                    "external_service": class_name,
                    "error": str(error),
                },
            )
            return None
        except (RuntimeError, ValueError, OSError) as error:
            self.logger.exception(
                "Failed to initialize external service %s",
                class_name,
                extra={
                    "service": self.service_name,
                    "external_service": class_name,
                    "error": str(error),
                },
            )
            return None

    @with_error_handling(operation_name="health_check")
    async def health_check(self) -> dict[str, Any]:
        """Perform health check for the service and its dependencies.

        Returns:
            Health status information for the service and its dependencies
        """
        health_status: dict[str, Any] = {
            "service": self.service_name,
            "status": "healthy",
            "dependencies": {},
        }

        # Check database service health
        if self.db is not None:
            try:
                # Attempt a simple database operation if available
                if hasattr(self.db, "health_check"):
                    await self.db.health_check()
                health_status["dependencies"]["database"] = "healthy"
            except (
                TimeoutError,
                CoreTripSageError,
                ConnectionError,
                RuntimeError,
            ) as error:
                health_status["dependencies"]["database"] = f"unhealthy: {error!s}"
                health_status["status"] = "degraded"
        else:
            health_status["dependencies"]["database"] = "unavailable"

        # Check cache service health
        if self.cache is not None:
            try:
                # Attempt a simple cache operation if available
                if hasattr(self.cache, "health_check"):
                    await self.cache.health_check()
                health_status["dependencies"]["cache"] = "healthy"
            except (
                TimeoutError,
                CoreTripSageError,
                ConnectionError,
                RuntimeError,
            ) as error:
                health_status["dependencies"]["cache"] = f"unhealthy: {error!s}"
                health_status["status"] = "degraded"
        else:
            health_status["dependencies"]["cache"] = "unavailable"

        # Check external service health
        if self.external_service is not None:
            try:
                # Attempt a simple external service operation if available
                if hasattr(self.external_service, "health_check"):
                    await self.external_service.health_check()
                health_status["dependencies"]["external_service"] = "healthy"
            except (
                TimeoutError,
                CoreTripSageError,
                ConnectionError,
                RuntimeError,
            ) as error:
                health_status["dependencies"]["external_service"] = (
                    f"unhealthy: {error!s}"
                )
                health_status["status"] = "degraded"
        else:
            health_status["dependencies"]["external_service"] = "unavailable"

        return health_status

    def get_service_info(self) -> dict[str, Any]:
        """Get service information and configuration.

        Returns:
            Service information including name, dependencies, and configuration
        """
        return {
            "service_name": self.service_name,
            "service_class": self.__class__.__name__,
            "module": self.__module__,
            "dependencies": {
                "database_service": self.db is not None,
                "cache_service": self.cache is not None,
                "external_service": self.external_service is not None,
            },
            "external_service_type": (
                type(self.external_service).__name__ if self.external_service else None
            ),
        }

    def __repr__(self) -> str:
        """String representation of the service."""
        return f"{self.__class__.__name__}(name='{self.service_name}')"


class BaseCRUDService(BaseService):
    """Base service class with common CRUD operations.

    Extends BaseService with standardized CRUD (Create, Read, Update, Delete)
    operations that can be customized by inheriting services.
    """

    @with_error_handling(operation_name="create_entity")
    async def create_entity(
        self, entity_data: dict[str, Any], entity_type: str
    ) -> dict[str, Any]:
        """Create a new entity with standardized error handling.

        Args:
            entity_data: Data for the new entity
            entity_type: Type of entity being created

        Returns:
            Created entity data with ID

        Raises:
            CoreServiceError: If creation fails
        """
        if self.db is None:
            raise CoreServiceError(
                message="Database service not available",
                code="DATABASE_UNAVAILABLE",
                details={"service": self.service_name, "operation": "create_entity"},
            )

        # Delegate to database service
        return await self.db.create_entity(entity_data, entity_type)

    @with_error_handling(operation_name="get_entity")
    async def get_entity(
        self, entity_id: str, entity_type: str
    ) -> dict[str, Any] | None:
        """Retrieve an entity by ID with standardized error handling.

        Args:
            entity_id: Unique identifier for the entity
            entity_type: Type of entity being retrieved

        Returns:
            Entity data or None if not found
        """
        if self.db is None:
            raise CoreServiceError(
                message="Database service not available",
                code="DATABASE_UNAVAILABLE",
                details={"service": self.service_name, "operation": "get_entity"},
            )

        return await self.db.get_entity(entity_id, entity_type)

    @with_error_handling(operation_name="update_entity")
    async def update_entity(
        self, entity_id: str, entity_data: dict[str, Any], entity_type: str
    ) -> dict[str, Any]:
        """Update an existing entity with standardized error handling.

        Args:
            entity_id: Unique identifier for the entity
            entity_data: Updated data for the entity
            entity_type: Type of entity being updated

        Returns:
            Updated entity data

        Raises:
            CoreServiceError: If update fails
        """
        if self.db is None:
            raise CoreServiceError(
                message="Database service not available",
                code="DATABASE_UNAVAILABLE",
                details={"service": self.service_name, "operation": "update_entity"},
            )

        return await self.db.update_entity(entity_id, entity_data, entity_type)

    @with_error_handling(operation_name="delete_entity")
    async def delete_entity(self, entity_id: str, entity_type: str) -> bool:
        """Delete an entity with standardized error handling.

        Args:
            entity_id: Unique identifier for the entity
            entity_type: Type of entity being deleted

        Returns:
            True if deletion was successful

        Raises:
            CoreServiceError: If deletion fails
        """
        if self.db is None:
            raise CoreServiceError(
                message="Database service not available",
                code="DATABASE_UNAVAILABLE",
                details={"service": self.service_name, "operation": "delete_entity"},
            )

        return await self.db.delete_entity(entity_id, entity_type)


__all__ = ["BaseCRUDService", "BaseService"]
