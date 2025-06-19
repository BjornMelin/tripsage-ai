"""
Base agent node implementation for LangGraph orchestration.

This module provides the abstract base class that all specialized agent nodes
inherit from, ensuring consistent error handling, logging, and tool management.
Refactored to support dependency injection and service-based architecture.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.state import TravelPlanningState, update_state_timestamp
from tripsage_core.exceptions.exceptions import CoreTripSageError as TripSageError
from tripsage_core.utils.error_handling_utils import log_exception
from tripsage_core.utils.logging_utils import get_logger


class BaseAgentNodeError(TripSageError):
    """Error raised when agent node operations fail."""

    pass


class BaseAgentNode(ABC):
    """
    Abstract base class for all LangGraph agent nodes.

    Provides common functionality for error handling, logging, state management,
    and tool initialization that all specialized agent nodes can inherit.
    """

    def __init__(
        self,
        node_name: str,
        service_registry: ServiceRegistry,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize the base agent node with dependency injection.

        Args:
            node_name: Unique name for this node (used in logging and routing)
            service_registry: Service registry for dependency injection
            config: Optional configuration dictionary for node-specific settings
        """
        self.node_name = node_name
        self.service_registry = service_registry
        self.config = config or {}
        self.logger = get_logger(f"orchestration.{node_name}")

        # Initialize node-specific tools
        self._initialize_tools()

        self.logger.info(f"Initialized {node_name} node with service injection")

    @property
    def name(self) -> str:
        """Get the node name for compatibility with tests."""
        return self.node_name

    @abstractmethod
    def _initialize_tools(self) -> None:
        """
        Initialize node-specific tools and resources.

        This method should be implemented by each specialized node to set up
        any tools, MCP clients, or other resources it needs to operate.
        The implementation should use self.service_registry to access services.
        """
        pass

    @abstractmethod
    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """
        Process the current state and return updated state.

        This is the main processing method that each specialized node must
        implement to perform its specific travel planning tasks.

        Args:
            state: Current travel planning state

        Returns:
            Updated state after processing

        Raises:
            BaseAgentNodeError: If processing fails
        """
        pass

    async def __call__(self, state: TravelPlanningState) -> TravelPlanningState:
        """
        Main entry point for node execution.

        This method provides the standard execution flow with error handling,
        logging, and state management that all nodes follow.

        Args:
            state: Current travel planning state

        Returns:
            Updated state after processing
        """
        try:
            self.logger.info(f"Executing {self.node_name} node")

            # Process the state using node-specific logic
            updated_state = await self.process(state)

            # Update agent history and timestamp
            updated_state["agent_history"].append(self.node_name)
            updated_state = update_state_timestamp(updated_state)

            self.logger.info(f"Successfully completed {self.node_name} node execution")
            return updated_state

        except Exception as e:
            self.logger.error(f"Error in {self.node_name} node: {str(e)}")
            log_exception(e, logger_name=f"orchestration.{self.node_name}")
            return self._handle_error(state, e)

    def _handle_error(
        self, state: TravelPlanningState, error: Exception
    ) -> TravelPlanningState:
        """
        Standardized error handling for all nodes.

        Args:
            state: Current state when error occurred
            error: The exception that was raised

        Returns:
            State updated with error information
        """
        # Update error tracking in error_info structure
        error_info = state.get("error_info", {})
        error_info["error_count"] = error_info.get("error_count", 0) + 1
        error_info["last_error"] = str(error)
        retry_attempts = error_info.get("retry_attempts", {})
        retry_attempts[self.node_name] = retry_attempts.get(self.node_name, 0) + 1
        error_info["retry_attempts"] = retry_attempts
        state["error_info"] = error_info

        # Add error message to conversation
        error_message = {
            "role": "assistant",
            "content": (
                "I encountered an issue while processing your request. "
                "Let me try a different approach."
            ),
            "agent": self.node_name,
            "error": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        state["messages"].append(error_message)

        # Update timestamp
        state = update_state_timestamp(state)

        return state

    def _extract_user_intent(self, message: str) -> dict[str, Any]:
        """
        Extract user intent from a message (default implementation).

        Specialized nodes can override this to provide more sophisticated
        intent extraction specific to their domain.

        Args:
            message: User message to analyze

        Returns:
            Dictionary containing extracted intent information
        """
        return {
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": self.node_name,
        }

    def _create_response_message(
        self, content: str, additional_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create a standardized response message.

        Args:
            content: The response content
            additional_data: Optional additional data to include

        Returns:
            Formatted message dictionary
        """
        message = {
            "role": "assistant",
            "content": content,
            "agent": self.node_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if additional_data:
            message.update(additional_data)

        return message

    def get_service(self, service_name: str):
        """
        Get a required service from the registry.

        Args:
            service_name: Name of the service to retrieve

        Returns:
            The service instance

        Raises:
            ValueError: If the service is not available
        """
        return self.service_registry.get_required_service(service_name)

    def get_optional_service(self, service_name: str):
        """
        Get an optional service from the registry.

        Args:
            service_name: Name of the service to retrieve

        Returns:
            The service instance or None if not available
        """
        return self.service_registry.get_optional_service(service_name)
