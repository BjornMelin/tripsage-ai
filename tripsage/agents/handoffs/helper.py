"""
Handoff helper functions for TripSage agents.

This module provides helper functions to facilitate handoffs between
different agent types in TripSage, leveraging OpenAI Agents SDK patterns.
Refactored to support dependency injection and service-based architecture.
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union

try:
    from agents import function_tool
except ImportError:
    from unittest.mock import MagicMock

    function_tool = MagicMock

from typing import TYPE_CHECKING

from tripsage.agents.service_registry import ServiceRegistry
from tripsage_core.exceptions import CoreTripSageError as TripSageError
from tripsage_core.utils.logging_utils import get_logger

if TYPE_CHECKING:
    from tripsage.agents.base import BaseAgent

logger = get_logger(__name__)


class HandoffError(TripSageError):
    """Error raised when a handoff fails."""

    pass


def create_handoff_tool(
    target_agent_class: Type["BaseAgent"],
    tool_name: str,
    description: str,
    context_filter: Optional[List[str]] = None,
    service_registry: Optional[ServiceRegistry] = None,
) -> Callable:
    """Create a handoff tool that transfers control to another agent.

    Args:
        target_agent_class: The agent class to hand off to
        tool_name: Name for the handoff tool
        description: Description of what this handoff does
        context_filter: Optional list of context keys to pass along
        service_registry: Service registry for dependency injection

    Returns:
        A handoff tool function
    """

    @function_tool
    async def handoff_tool(
        query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute handoff to target agent."""
        try:
            # Create target agent instance with service registry
            target_agent = target_agent_class(service_registry=service_registry)

            # Prepare handoff context
            handoff_context = {
                "is_handoff": True,
                "handoff_source": tool_name,
                "handoff_query": query,
            }

            # Apply context filter if specified
            if context and context_filter:
                filtered_context = {
                    k: v for k, v in context.items() if k in context_filter
                }
                handoff_context.update(filtered_context)
            elif context:
                handoff_context.update(context)

            # Run the target agent
            result = await target_agent.run(query, context=handoff_context)

            return {
                "handoff": "completed",
                "target_agent": target_agent_class.__name__,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Handoff to {target_agent_class.__name__} failed: {str(e)}")
            raise HandoffError(f"Handoff failed: {str(e)}") from e

    # Set attributes for tracking
    handoff_tool.__is_handoff_tool__ = True
    handoff_tool.__target_agent__ = target_agent_class.__name__
    handoff_tool.__name__ = tool_name
    handoff_tool.__doc__ = description

    return handoff_tool


def create_delegation_tool(
    target_agent_class: Type["BaseAgent"],
    tool_name: str,
    description: str,
    return_key: str = "content",
    context_filter: Optional[List[str]] = None,
    service_registry: Optional[ServiceRegistry] = None,
) -> Callable:
    """Create a delegation tool that uses another agent as a tool.

    Args:
        target_agent_class: The agent class to delegate to
        tool_name: Name for the delegation tool
        description: Description of what this delegation does
        return_key: Key in the response to return (defaults to "content")
        context_filter: Optional list of context keys to pass along
        service_registry: Service registry for dependency injection

    Returns:
        A delegation tool function
    """

    @function_tool
    async def delegation_tool(
        query: str, context: Optional[Dict[str, Any]] = None
    ) -> Union[str, Dict[str, Any]]:
        """Execute delegation to target agent."""
        try:
            # Create target agent instance with service registry
            target_agent = target_agent_class(service_registry=service_registry)

            # Prepare delegation context
            delegation_context = {
                "is_delegation": True,
                "delegation_source": tool_name,
                "delegation_query": query,
            }

            # Apply context filter if specified
            if context and context_filter:
                filtered_context = {
                    k: v for k, v in context.items() if k in context_filter
                }
                delegation_context.update(filtered_context)
            elif context:
                delegation_context.update(context)

            # Run the target agent
            result = await target_agent.run(query, context=delegation_context)

            # Return the specified key from the result
            if isinstance(result, dict) and return_key in result:
                return result[return_key]
            else:
                return result

        except Exception as e:
            logger.error(
                f"Delegation to {target_agent_class.__name__} failed: {str(e)}"
            )
            raise HandoffError(f"Delegation failed: {str(e)}") from e

    # Set attributes for tracking
    delegation_tool.__is_delegation_tool__ = True
    delegation_tool.__target_agent__ = target_agent_class.__name__
    delegation_tool.__name__ = tool_name
    delegation_tool.__doc__ = description

    return delegation_tool


def register_handoff_tools(
    agent: "BaseAgent",
    target_agents: Dict[str, Dict[str, Union[Type["BaseAgent"], str, List[str]]]],
    service_registry: Optional[ServiceRegistry] = None,
) -> int:
    """Register multiple handoff tools at once.

    Args:
        agent: The agent to register handoffs with
        target_agents: Dictionary mapping tool names to dictionaries with keys:
            - "agent_class": Target agent class
            - "description": Handoff description
            - "context_filter": Optional list of context keys to pass along
        service_registry: Service registry for dependency injection

    Returns:
        Number of tools registered
    """
    count = 0
    registry = service_registry or getattr(agent, "service_registry", None)

    for tool_name, config in target_agents.items():
        target_class = config["agent_class"]
        description = config["description"]
        context_filter = config.get("context_filter")

        handoff_tool = create_handoff_tool(
            target_class,
            tool_name,
            description,
            context_filter=context_filter,
            service_registry=registry,
        )

        agent._register_tool(handoff_tool)
        count += 1

    logger.info(f"Registered {count} handoff tools")
    return count


def register_delegation_tools(
    agent: "BaseAgent",
    target_agents: Dict[str, Dict[str, Union[Type["BaseAgent"], str, List[str], str]]],
    service_registry: Optional[ServiceRegistry] = None,
) -> int:
    """Register multiple delegation tools at once.

    Args:
        agent: The agent to register delegations with
        target_agents: Dictionary mapping tool names to dictionaries with keys:
            - "agent_class": Target agent class
            - "description": Delegation description
            - "return_key": Key in the response to return (defaults to "content")
            - "context_filter": Optional list of context keys to pass along
        service_registry: Service registry for dependency injection

    Returns:
        Number of tools registered
    """
    count = 0
    registry = service_registry or getattr(agent, "service_registry", None)

    for tool_name, config in target_agents.items():
        target_class = config["agent_class"]
        description = config["description"]
        return_key = config.get("return_key", "content")
        context_filter = config.get("context_filter")

        delegation_tool = create_delegation_tool(
            target_class,
            tool_name,
            description,
            return_key=return_key,
            context_filter=context_filter,
            service_registry=registry,
        )

        agent._register_tool(delegation_tool)
        count += 1

    logger.info(f"Registered {count} delegation tools")
    return count


def create_user_announcement(
    source_agent_name: str,
    target_agent_name: str,
    reason: Optional[str] = None,
) -> str:
    """Create a user-friendly handoff announcement.

    Args:
        source_agent_name: Name of the source agent
        target_agent_name: Name of the target agent
        reason: Optional reason for the handoff

    Returns:
        Formatted announcement message
    """
    # Format names for display
    target_name = target_agent_name.replace("Agent", "").strip()

    # Base announcement
    announcement = (
        f"👋 I'm connecting you with our {target_name} Specialist to "
        f"better assist with your request."
    )

    # Add reason if provided
    if reason:
        announcement += f"\n\n{reason}"

    return announcement
