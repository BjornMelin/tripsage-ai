"""Base Agent implementation for TripSage.

This module provides the base agent class using the OpenAI Agents SDK
for the TripSage application. Refactored to use dependency injection
and proper async patterns.
"""

import importlib
import inspect
import time
import uuid
from collections.abc import Callable
from typing import Any


try:
    from agents import Agent, Runner, function_tool
except ImportError:
    # Mock for testing environments where agents package may not be available
    from unittest.mock import MagicMock

    Agent = MagicMock
    Runner = MagicMock
    function_tool = MagicMock

from tripsage.agents.service_registry import ServiceRegistry
from tripsage_core.config import get_settings
from tripsage_core.exceptions.exceptions import CoreTripSageError
from tripsage_core.utils.error_handling_utils import log_exception
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)
settings = get_settings()


class BaseAgent:
    """Base class for all TripSage agents using the OpenAI Agents SDK."""

    def __init__(
        self,
        name: str,
        instructions: str,
        service_registry: ServiceRegistry,
        model: str = None,
        temperature: float = None,
        tools: list[Callable] | None = None,
        metadata: dict[str, str] | None = None,
    ):
        """Initialize the agent with dependency injection.

        Args:
            name: Agent name
            instructions: Agent instructions
            service_registry: Service registry for dependency injection
            model: Model name to use (defaults to settings if None)
            temperature: Temperature for model sampling (defaults to settings if None)
            tools: List of tools to register
            metadata: Additional metadata
        """
        self.name = name
        self.instructions = instructions
        self.service_registry = service_registry
        self.model = model or settings.openai_model
        self.temperature = temperature or settings.model_temperature
        self.metadata = metadata or {"agent_type": "tripsage"}

        # Initialize tools
        self._tools = tools or []
        self._registered_tools: set[str] = set()
        self._handoff_tools: dict[str, dict[str, Any]] = {}
        self._delegation_tools: dict[str, dict[str, Any]] = {}

        # Register default tools
        self._register_default_tools()

        # Create OpenAI Agent
        self.agent = Agent(
            name=name,
            instructions=instructions,
            model=self.model,
            temperature=self.temperature,
            tools=self._tools,
        )

        # Store conversation history
        self.messages_history = []
        self.session_id = str(uuid.uuid4())
        self.session_data = {}
        self.handoff_data = {}

        logger.info("Initialized agent: %s", name)

    def _register_default_tools(self) -> None:
        """Register default tools for the agent."""
        # Register memory tools with service injection
        self.register_tool_group("memory_tools", service_registry=self.service_registry)

        # Register echo tool
        self._register_tool(self.echo)

    def _register_tool(self, tool: Callable) -> None:
        """Register a tool with the agent if it hasn't been registered already.

        Args:
            tool: Tool function to register
        """
        tool_name = tool.__name__

        # Skip if already registered
        if tool_name in self._registered_tools:
            logger.debug("Tool already registered: %s", tool_name)
            return

        self._tools.append(tool)
        self._registered_tools.add(tool_name)

        # Track handoff and delegation tools separately
        if hasattr(tool, "__is_handoff_tool__"):
            self._handoff_tools[tool_name] = {
                "target_agent": getattr(tool, "__target_agent__", "Unknown"),
                "tool": tool,
            }
            logger.debug(
                "Registered handoff tool: %s → %s",
                tool_name,
                self._handoff_tools[tool_name]["target_agent"],
            )
        elif hasattr(tool, "__is_delegation_tool__"):
            self._delegation_tools[tool_name] = {
                "target_agent": getattr(tool, "__target_agent__", "Unknown"),
                "tool": tool,
            }
            logger.debug(
                "Registered delegation tool: %s → %s",
                tool_name,
                self._delegation_tools[tool_name]["target_agent"],
            )
        else:
            logger.debug("Registered tool: %s", tool_name)

    def register_tool_group(
        self,
        module_name: str,
        package: str | None = None,
        service_registry: ServiceRegistry | None = None,
    ) -> int:
        """Register all tools from a module with service injection.

        This method automatically discovers and registers all functions
        decorated with @function_tool in the specified module, passing
        the service registry to tools that need it.

        Args:
            module_name: Name of the module containing tools
            package: Optional package name for relative imports
            service_registry: Service registry to pass to tools

        Returns:
            Number of tools registered
        """
        try:
            # Import the module
            if not module_name.startswith("tripsage.") and not package:
                # Try relative import from tripsage.tools package
                module = importlib.import_module(f".{module_name}", "tripsage.tools")
            else:
                module = importlib.import_module(module_name, package)

            # Use the provided service registry or the agent's
            registry = service_registry or self.service_registry

            # Find all function tools in the module
            tool_count = 0
            for name, obj in inspect.getmembers(module):
                # Skip private members and non-callables
                if name.startswith("_") or not callable(obj):
                    continue

                # Check if it's a function_tool
                if hasattr(obj, "__is_function_tool__"):
                    # Create a wrapper that injects the service registry
                    if "service_registry" in inspect.signature(obj).parameters:
                        # Tool accepts service registry - create wrapper
                        wrapped_tool = self._create_service_injected_tool(obj, registry)
                        self._register_tool(wrapped_tool)
                    else:
                        # Tool doesn't need service registry
                        self._register_tool(obj)
                    tool_count += 1

            logger.info("Registered %d tools from module: %s", tool_count, module_name)
            return tool_count

        except (ImportError, AttributeError) as e:
            logger.warning("Could not register tools from %s: %s", module_name, str(e))
            return 0

    def _create_service_injected_tool(
        self, tool: Callable, service_registry: ServiceRegistry
    ) -> Callable:
        """Create a wrapper that injects the service registry into a tool.

        Args:
            tool: The original tool function
            service_registry: The service registry to inject

        Returns:
            Wrapped tool function with service registry injected
        """
        from functools import wraps

        @wraps(tool)
        async def wrapped_tool(*args, **kwargs):
            # Inject service registry if not already provided
            if "service_registry" not in kwargs:
                kwargs["service_registry"] = service_registry
            return await tool(*args, **kwargs)

        # Preserve attributes from original tool
        for attr in ["__is_function_tool__", "__name__", "__doc__"]:
            if hasattr(tool, attr):
                setattr(wrapped_tool, attr, getattr(tool, attr))

        return wrapped_tool

    def register_handoff(
        self,
        target_agent_class: type["BaseAgent"],
        tool_name: str,
        description: str,
        context_filter: list[str] | None = None,
    ) -> None:
        """Register a handoff tool for transferring control to another agent.

        Args:
            target_agent_class: The agent class to hand off to
            tool_name: Name for the handoff tool
            description: Description of what this handoff does
            context_filter: Optional list of context keys to pass along
        """
        from tripsage.agents.handoffs.helper import create_handoff_tool

        handoff_tool = create_handoff_tool(
            target_agent_class,
            tool_name,
            description,
            context_filter=context_filter,
            service_registry=self.service_registry,
        )

        self._register_tool(handoff_tool)

    def register_delegation(
        self,
        target_agent_class: type["BaseAgent"],
        tool_name: str,
        description: str,
        return_key: str = "content",
        context_filter: list[str] | None = None,
    ) -> None:
        """Register a delegation tool for using another agent as a tool.

        Args:
            target_agent_class: The agent class to delegate to
            tool_name: Name for the delegation tool
            description: Description of what this delegation does
            return_key: Key in the response to return (defaults to "content")
            context_filter: Optional list of context keys to pass along
        """
        from tripsage.agents.handoffs.helper import create_delegation_tool

        delegation_tool = create_delegation_tool(
            target_agent_class,
            tool_name,
            description,
            return_key=return_key,
            context_filter=context_filter,
            service_registry=self.service_registry,
        )

        self._register_tool(delegation_tool)

    def register_multiple_handoffs(
        self,
        target_agents: dict[str, dict[str, type["BaseAgent"] | str | list[str]]],
    ) -> int:
        """Register multiple handoff tools at once.

        Args:
            target_agents: Dictionary mapping tool names to dictionaries with keys:
                - "agent_class": Target agent class
                - "description": Handoff description
                - "context_filter": Optional list of context keys to pass along

        Returns:
            Number of tools registered
        """
        from tripsage.agents.handoffs.helper import register_handoff_tools

        return register_handoff_tools(
            self, target_agents, service_registry=self.service_registry
        )

    def register_multiple_delegations(
        self,
        target_agents: dict[str, dict[str, type["BaseAgent"] | str | list[str] | str]],
    ) -> int:
        """Register multiple delegation tools at once.

        Args:
            target_agents: Dictionary mapping tool names to dictionaries with keys:
                - "agent_class": Target agent class
                - "description": Delegation description
                - "return_key": Key in the response to return (defaults to "content")
                - "context_filter": Optional list of context keys to pass along

        Returns:
            Number of tools registered
        """
        from tripsage.agents.handoffs.helper import register_delegation_tools

        return register_delegation_tools(
            self, target_agents, service_registry=self.service_registry
        )

    async def _initialize_session(self, user_id: str | None = None) -> dict[str, Any]:
        """Initialize a new session with memory data.

        Args:
            user_id: Optional user ID

        Returns:
            Session data
        """
        try:
            # Initialize session memory using memory service
            session_data = {}
            if user_id and self.service_registry.memory_service:
                # Get user context from memory service
                context = await self.service_registry.memory_service.get_user_context(
                    user_id
                )
                session_data = {
                    "user_id": user_id,
                    "preferences": context.get("preferences", {}),
                    "past_trips": context.get("past_trips", []),
                }
            elif user_id:
                session_data = {"user_id": user_id}

            self.session_data = session_data
            logger.info("Session initialized with memory data")
            return self.session_data
        except Exception as e:
            logger.exception("Error initializing session: %s", str(e))
            log_exception(e)
            return {}

    async def _save_session_summary(self, user_id: str, summary: str) -> None:
        """Save a summary of the current session.

        Args:
            user_id: User ID
            summary: Session summary
        """
        try:
            if self.service_registry.memory_service:
                # Save conversation history to memory
                messages = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in self.messages_history
                    if "role" in msg and "content" in msg
                ]

                await self.service_registry.memory_service.add_conversation_memory(
                    messages=messages,
                    user_id=user_id,
                    session_id=self.session_id,
                    metadata={
                        "agent": self.name,
                        "summary": summary,
                    },
                )
            logger.info("Session summary saved")
        except Exception as e:
            logger.exception("Error saving session summary: %s", str(e))
            log_exception(e)

    async def run(
        self, user_input: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Run the agent with user input.

        Args:
            user_input: User input text
            context: Optional context data

        Returns:
            Dictionary with the agent's response and other information
        """
        # Add to message history
        self.messages_history.append(
            {"role": "user", "content": user_input, "timestamp": time.time()}
        )

        # Set up context
        run_context = context or {}

        # Check if this is a handoff from another agent
        is_handoff = run_context.get("is_handoff", False)
        handoff_source = run_context.get("handoff_source", None)

        if is_handoff and handoff_source:
            logger.info("Receiving handoff from %s to %s", handoff_source, self.name)

            # Extract handoff data if available
            handoff_data = run_context.get("handoff_data", {})
            self.handoff_data = handoff_data

            # Add handoff information to context
            run_context["handoff_received"] = True

            # Store handoff in session data
            if "handoffs" not in self.session_data:
                self.session_data["handoffs"] = []

            self.session_data["handoffs"].append(
                {
                    "from": handoff_source,
                    "to": self.name,
                    "timestamp": time.time(),
                    "query": (
                        user_input[:100] + "..."
                        if len(user_input) > 100
                        else user_input
                    ),
                }
            )

        # Initialize session data if this is the first message
        if not self.session_data and "user_id" in run_context:
            await self._initialize_session(run_context.get("user_id"))
            run_context["session_data"] = self.session_data
            run_context["session_id"] = self.session_id

        try:
            # Run the agent
            logger.info("Running agent: %s", self.name)
            result = await Runner.run(self.agent, user_input, context=run_context)

            # Check if any tool calls were handoffs
            tool_calls = result.tool_calls if hasattr(result, "tool_calls") else []

            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")

                # Check if the tool call was a handoff
                if tool_name in self._handoff_tools:
                    logger.info(
                        "Detected handoff to %s via %s",
                        self._handoff_tools[tool_name]["target_agent"],
                        tool_name,
                    )

                    # Add handoff information to response
                    result.handoff_detected = True
                    result.handoff_target = self._handoff_tools[tool_name][
                        "target_agent"
                    ]
                    result.handoff_tool = tool_name

                    # Create handoff response with both content and handoff metadata
                    return {
                        "content": result.final_output,
                        "tool_calls": tool_calls,
                        "status": "handoff",
                        "handoff_target": result.handoff_target,
                        "handoff_tool": result.handoff_tool,
                    }

                # Check if the tool call was a delegation
                elif tool_name in self._delegation_tools:
                    logger.info(
                        "Detected delegation to %s via %s",
                        self._delegation_tools[tool_name]["target_agent"],
                        tool_name,
                    )

                    # For delegations, we continue as normal since control comes back

            # Extract response for normal processing (no handoff)
            response = {
                "content": result.final_output,
                "tool_calls": tool_calls,
                "status": "success",
            }

            # Add to message history
            self.messages_history.append(
                {
                    "role": "assistant",
                    "content": response["content"],
                    "timestamp": time.time(),
                }
            )

            # Save session summary if needed and we have enough messages
            if len(self.messages_history) >= 10 and "user_id" in run_context:
                # Generate session summary
                summary = (
                    f"Conversation with {self.messages_history[0]['content'][:50]}..."
                )
                await self._save_session_summary(run_context["user_id"], summary)

            return response

        except Exception as e:
            logger.exception("Error running agent: %s", str(e))
            log_exception(e)

            error_message = "An error occurred while processing your request."
            if isinstance(e, CoreTripSageError):
                error_message = e.message

            # Add error to message history
            self.messages_history.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "timestamp": time.time(),
                    "error": True,
                }
            )

            return {
                "content": error_message,
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Get the conversation history.

        Returns:
            List of message dictionaries
        """
        return self.messages_history

    @function_tool
    async def echo(self, text: str) -> dict[str, str]:
        """Echo the input back to the user.

        Args:
            text: Text to echo

        Returns:
            Dictionary with the echoed text
        """
        return {"text": text}
