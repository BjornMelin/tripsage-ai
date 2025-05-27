"""
Base agent node implementation for LangGraph orchestration.

This module provides the abstract base class that all specialized agent nodes
inherit from, ensuring consistent error handling, logging, and tool management.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from tripsage.orchestration.state import TravelPlanningState, update_state_timestamp
from tripsage.utils.error_handling import TripSageError, log_exception
from tripsage.utils.logging import get_logger


class BaseAgentNodeError(TripSageError):
    """Error raised when agent node operations fail."""

    pass


class BaseAgentNode(ABC):
    """
    Abstract base class for all LangGraph agent nodes.

    Provides common functionality for error handling, logging, state management,
    and tool initialization that all specialized agent nodes can inherit.
    """

    def __init__(self, node_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base agent node.

        Args:
            node_name: Unique name for this node (used in logging and routing)
            config: Optional configuration dictionary for node-specific settings
        """
        self.node_name = node_name
        self.config = config or {}
        self.logger = get_logger(f"orchestration.{node_name}")

        # Initialize node-specific tools
        self._initialize_tools()

        self.logger.info(f"Initialized {node_name} node")

    @abstractmethod
    def _initialize_tools(self) -> None:
        """
        Initialize node-specific tools and resources.

        This method should be implemented by each specialized node to set up
        any tools, MCP clients, or other resources it needs to operate.
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
            log_exception(
                e,
                context={"node": self.node_name, "session_id": state.get("session_id")},
            )
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
        # Update error tracking
        state["error_count"] += 1
        state["last_error"] = str(error)
        state["retry_attempts"][self.node_name] = (
            state["retry_attempts"].get(self.node_name, 0) + 1
        )

        # Add error message to conversation
        error_message = {
            "role": "assistant",
            "content": (
                "I encountered an issue while processing your request. "
                "Let me try a different approach."
            ),
            "agent": self.node_name,
            "error": True,
            "timestamp": datetime.utcnow().isoformat(),
        }
        state["messages"].append(error_message)

        # Update timestamp
        state = update_state_timestamp(state)

        return state

    def _extract_user_intent(self, message: str) -> Dict[str, Any]:
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
            "timestamp": datetime.utcnow().isoformat(),
            "node": self.node_name,
        }

    def _create_response_message(
        self, content: str, additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
            "timestamp": datetime.utcnow().isoformat(),
        }

        if additional_data:
            message.update(additional_data)

        return message
