"""
MCP Manager for Airbnb accommodation operations.

This module provides a simplified manager that handles the single remaining
MCP integration for Airbnb accommodations. All other services have been
migrated to direct SDK integration.
"""

import logging
import threading
import time
import traceback
from typing import Any, Dict, Optional

import httpx

# Optional OpenTelemetry support
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    HAS_OPENTELEMETRY = True
except ImportError:
    # Create dummy classes for when OpenTelemetry is not available
    class DummySpan:
        def set_status(self, status, description=None):
            pass

        def set_attribute(self, key, value):
            pass

        def record_exception(self, exception):
            pass

    class DummyTracer:
        def start_span(self, name, **kwargs):
            return DummySpan()

    class DummyTrace:
        def get_tracer(self, name):
            return DummyTracer()

    class DummyStatus:
        ERROR = "ERROR"
        OK = "OK"

    class DummyStatusCode:
        ERROR = "ERROR"
        OK = "OK"

    trace = DummyTrace()
    Status = DummyStatus()
    StatusCode = DummyStatusCode()
    HAS_OPENTELEMETRY = False

from .base_wrapper import BaseMCPWrapper
from .exceptions import (
    MCPAuthenticationError,
    MCPClientError,
    MCPInvocationError,
    MCPManagerError,
    MCPMethodNotFoundError,
    MCPNotFoundError,
    MCPNotRegisteredError,
    MCPRateLimitError,
    MCPTimeoutError,
)
from .registry import registry

# Get logger for this module
logger = logging.getLogger(__name__)

# Get tracer for OpenTelemetry
tracer = trace.get_tracer(__name__)


class MCPManager:
    """Singleton manager for all MCP operations."""

    _instance: Optional["MCPManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MCPManager":
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the manager."""
        # Ensure initialization only happens once
        if not self._initialized:
            self._wrappers: Dict[str, BaseMCPWrapper] = {}
            self._configs: Dict[str, Dict[str, Any]] = {}
            self._initialized = True

    def load_configurations(self, configs: Dict[str, Dict[str, Any]]) -> None:
        """
        Load MCP configurations.

        Args:
            configs: Dictionary of MCP configurations
        """
        self._configs = configs

    async def initialize_mcp(self, mcp_name: str) -> BaseMCPWrapper:
        """
        Initialize an MCP wrapper instance.

        Args:
            mcp_name: The name of the MCP to initialize

        Returns:
            The initialized MCP wrapper

        Raises:
            MCPNotFoundError: If the MCP is not registered
            MCPManagerError: If initialization fails
        """
        # Check if already initialized
        if mcp_name in self._wrappers:
            return self._wrappers[mcp_name]

        try:
            # Get the wrapper class from registry
            wrapper_class = registry.get_wrapper_class(mcp_name)

            # Create client and wrapper
            # Note: The actual client initialization will depend on
            # the specific MCP implementation
            wrapper = wrapper_class(client=None, mcp_name=mcp_name)

            # Store the wrapper
            self._wrappers[mcp_name] = wrapper

            return wrapper

        except KeyError as e:
            raise MCPNotRegisteredError(
                f"MCP '{mcp_name}' not found in registry", mcp_name=mcp_name
            ) from e
        except Exception as e:
            raise MCPManagerError(
                f"Failed to initialize MCP '{mcp_name}': {str(e)}"
            ) from e

    async def initialize_all_enabled(self) -> None:
        """
        Initialize all enabled MCPs based on configuration.

        This method will initialize all MCPs that have configurations loaded.
        """
        for mcp_name in self._configs:
            try:
                await self.initialize_mcp(mcp_name)
            except Exception as e:
                # Log the error but continue with other MCPs
                print(f"Failed to initialize MCP '{mcp_name}': {e}")

    async def invoke(
        self,
        mcp_name: str,
        method_name: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """
        Invoke a method on an MCP.

        Args:
            mcp_name: The name of the MCP to use
            method_name: The method to invoke
            params: Method parameters as a dictionary
            **kwargs: Additional keyword arguments

        Returns:
            The result from the MCP method call

        Raises:
            MCPNotRegisteredError: If the MCP is not found
            MCPManagerError: If the invocation fails
        """
        # Create OpenTelemetry span
        with tracer.start_as_current_span(
            f"mcp.call.{mcp_name}.{method_name}",
            attributes={
                "mcp.name": mcp_name,
                "mcp.method": method_name,
            },
        ) as span:
            # Start timing
            start_time = time.time()

            # Log the start of the MCP call (don't log sensitive params)
            logger.info(
                "MCP call started",
                extra={
                    "mcp_name": mcp_name,
                    "method": method_name,
                    "has_params": bool(params or kwargs),
                },
            )

            try:
                # Initialize the MCP if not already done
                wrapper = await self.initialize_mcp(mcp_name)

                # Prepare parameters
                call_params = params or {}
                call_params.update(kwargs)

                # Invoke the method
                result = await wrapper.invoke_method(method_name, **call_params)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Log successful completion
                logger.info(
                    "MCP call completed successfully",
                    extra={
                        "mcp_name": mcp_name,
                        "method": method_name,
                        "duration_ms": duration_ms,
                        "success": True,
                    },
                )

                # Set span status to OK
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("mcp.success", True)
                span.set_attribute("mcp.duration_ms", duration_ms)

                return result

            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Map common exceptions to specific MCP errors
                mapped_exception = self._map_exception(e, mcp_name, method_name)

                # Log the error
                logger.error(
                    f"MCP call failed: {str(mapped_exception)}",
                    extra={
                        "mcp_name": mcp_name,
                        "method": method_name,
                        "duration_ms": duration_ms,
                        "success": False,
                        "error_type": mapped_exception.__class__.__name__,
                        "error_message": str(mapped_exception),
                        "traceback": traceback.format_exc(),
                    },
                )

                # Record exception on span
                span.record_exception(mapped_exception)
                error_name = mapped_exception.__class__.__name__
                span.set_status(
                    Status(StatusCode.ERROR, f"{error_name}: {str(mapped_exception)}")
                )
                span.set_attribute("mcp.success", False)
                span.set_attribute("mcp.error_type", error_name)
                span.set_attribute("mcp.duration_ms", duration_ms)

                raise mapped_exception from e

    def _map_exception(
        self, original_error: Exception, mcp_name: str, method_name: str
    ) -> MCPClientError:
        """
        Map common exceptions to specific MCP error types.

        Args:
            original_error: The original exception
            mcp_name: Name of the MCP
            method_name: Name of the method

        Returns:
            A specific MCPClientError subtype
        """
        error_message = str(original_error)

        # Check for timeout errors
        if isinstance(original_error, (httpx.TimeoutException, TimeoutError)):
            timeout_seconds = getattr(original_error, "timeout", 30)
            return MCPTimeoutError(
                f"MCP operation timed out after {timeout_seconds}s: {error_message}",
                mcp_name=mcp_name,
                timeout_seconds=timeout_seconds,
                original_error=original_error,
            )

        # Check for authentication errors
        if isinstance(original_error, httpx.HTTPStatusError):
            if original_error.response.status_code == 401:
                return MCPAuthenticationError(
                    f"Authentication failed for MCP {mcp_name}: {error_message}",
                    mcp_name=mcp_name,
                    original_error=original_error,
                )
            elif original_error.response.status_code == 429:
                retry_after = original_error.response.headers.get("Retry-After")
                return MCPRateLimitError(
                    f"Rate limit exceeded for MCP {mcp_name}: {error_message}",
                    mcp_name=mcp_name,
                    retry_after=float(retry_after) if retry_after else None,
                    original_error=original_error,
                )
            elif original_error.response.status_code == 404:
                return MCPNotFoundError(
                    f"Resource not found in MCP {mcp_name}: {error_message}",
                    mcp_name=mcp_name,
                    original_error=original_error,
                )

        # Check for method not found errors
        if (
            "method not found" in error_message.lower()
            or "unknown method" in error_message.lower()
        ):
            return MCPMethodNotFoundError(
                f"Method '{method_name}' not found in MCP {mcp_name}: {error_message}",
                mcp_name=mcp_name,
                method_name=method_name,
            )

        # Default to generic invocation error
        return MCPInvocationError(
            f"Failed to invoke {mcp_name}.{method_name}: {error_message}",
            mcp_name=mcp_name,
            method_name=method_name,
            original_error=original_error,
        )

    def get_available_mcps(self) -> list[str]:
        """
        Get a list of available (registered) MCPs.

        Returns:
            List of available MCP names
        """
        return registry.get_registered_mcps()

    def get_initialized_mcps(self) -> list[str]:
        """
        Get a list of initialized MCPs.

        Returns:
            List of initialized MCP names
        """
        return list(self._wrappers.keys())


# Global manager instance
mcp_manager = MCPManager()
