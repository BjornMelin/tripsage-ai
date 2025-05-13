"""
Base Agent implementation for TripSage.

This module provides the base agent class using the OpenAI Agents SDK
with integration for MCP tools and dual storage architecture.
"""

import importlib
import inspect
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

from agents import Agent, function_tool
from tripsage.clients.base_client import BaseMCPClient
from tripsage.utils.error_handling import MCPError, TripSageError, log_exception
from tripsage.utils.logging import get_module_logger
from tripsage.utils.settings import get_settings

logger = get_module_logger(__name__)
settings = get_settings()


class BaseAgent:
    """Base class for all TripSage agents using the OpenAI Agents SDK."""

    def __init__(
        self,
        name: str,
        instructions: str,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        tools: Optional[List[Callable]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ):
        """Initialize the agent.

        Args:
            name: Agent name
            instructions: Agent instructions
            model: Model name to use
            temperature: Temperature for model sampling
            tools: List of tools to register
            metadata: Additional metadata
        """
        self.name = name
        self.instructions = instructions
        self.model = model
        self.temperature = temperature
        self.metadata = metadata or {"agent_type": "tripsage"}

        # Initialize tools
        self._tools = tools or []
        self._registered_tools: Set[str] = set()

        # Register default tools
        self._register_default_tools()

        # Create OpenAI Agent
        self.agent = Agent(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            tools=self._tools,
        )

        # Store conversation history
        self.messages_history = []
        self.session_id = str(uuid.uuid4())
        self.session_data = {}

        logger.info("Initialized agent: %s", name)

    def _register_default_tools(self) -> None:
        """Register default tools for the agent."""
        # Register memory tools
        self.register_tool_group("memory_tools")

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
        logger.debug("Registered tool: %s", tool_name)

    def register_tool_group(
        self, module_name: str, package: Optional[str] = None
    ) -> int:
        """Register all tools from a module.

        This method automatically discovers and registers all functions
        decorated with @function_tool in the specified module.

        Args:
            module_name: Name of the module containing tools
            package: Optional package name for relative imports

        Returns:
            Number of tools registered
        """
        try:
            # Import the module
            if not module_name.startswith("tripsage.") and not package:
                # Try relative import from tools package
                module = importlib.import_module(f".{module_name}", "tripsage.tools")
            else:
                module = importlib.import_module(module_name, package)

            # Find all function tools in the module
            tool_count = 0
            for name, obj in inspect.getmembers(module):
                # Skip private members and non-callables
                if name.startswith("_") or not callable(obj):
                    continue

                # Check if it's a function_tool
                if hasattr(obj, "__is_function_tool__"):
                    self._register_tool(obj)
                    tool_count += 1

            logger.info("Registered %d tools from module: %s", tool_count, module_name)
            return tool_count

        except (ImportError, AttributeError) as e:
            logger.warning("Could not register tools from %s: %s", module_name, str(e))
            return 0

    def register_mcp_client_tools(
        self, mcp_client: BaseMCPClient, prefix: str = ""
    ) -> None:
        """Register tools from an MCP client.

        This method is a public interface for registering MCP client tools
        with the agent.

        Args:
            mcp_client: MCP client to register tools from
            prefix: Prefix to add to tool names
        """
        try:
            # Get available tools from client
            client_tools = mcp_client.list_tools_sync()

            if not client_tools:
                logger.warning(
                    "No tools found in MCP client: %s", mcp_client.server_name
                )
                return

            # Register each tool
            registered_count = 0
            for tool_name in client_tools:
                if self._register_mcp_tool(mcp_client, tool_name, prefix):
                    registered_count += 1

            logger.info(
                "Registered %d tools from MCP client: %s",
                registered_count,
                mcp_client.server_name,
            )

        except Exception as e:
            logger.error("Error registering MCP client tools: %s", str(e))
            log_exception(e)

    def _register_mcp_tool(
        self, mcp_client: BaseMCPClient, tool_name: str, prefix: str = ""
    ) -> bool:
        """Register a single MCP tool.

        Args:
            mcp_client: MCP client to register tool from
            tool_name: Name of the tool to register
            prefix: Prefix to add to tool name

        Returns:
            Boolean indicating if the tool was registered
        """
        # Set proper name with prefix
        wrapper_name = f"{prefix}{tool_name}"

        # Skip if already registered
        if wrapper_name in self._registered_tools:
            logger.debug("MCP tool already registered: %s", wrapper_name)
            return False

        # Create a wrapper function for this tool
        @function_tool
        async def mcp_tool_wrapper(params: Dict[str, Any]):
            """Wrapper for MCP client tool."""
            try:
                result = await mcp_client.call_tool(tool_name, params)
                return result
            except Exception as e:
                logger.error("Error calling MCP tool %s: %s", tool_name, str(e))
                if isinstance(e, MCPError):
                    return {"error": e.message}
                return {"error": f"MCP tool error: {str(e)}"}

        # Set proper name and docstring for the wrapper
        tool_metadata = mcp_client.get_tool_metadata_sync(tool_name)
        mcp_tool_wrapper.__name__ = wrapper_name

        if tool_metadata and "description" in tool_metadata:
            mcp_tool_wrapper.__doc__ = tool_metadata["description"]
        else:
            mcp_tool_wrapper.__doc__ = (
                f"Call the {tool_name} tool from {mcp_client.server_name} MCP."
            )

        # Register the wrapper
        self._register_tool(mcp_tool_wrapper)
        logger.debug(
            "Registered MCP tool %s as %s from %s",
            tool_name,
            wrapper_name,
            mcp_client.server_name,
        )
        return True

    async def _initialize_session(
        self, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize a new session with knowledge graph data.

        Args:
            user_id: Optional user ID

        Returns:
            Session data
        """
        try:
            # Initialize session memory
            from tripsage.utils.session_memory import initialize_session_memory

            self.session_data = await initialize_session_memory(user_id)
            logger.info("Session initialized with memory data")
            return self.session_data
        except Exception as e:
            logger.error("Error initializing session: %s", str(e))
            log_exception(e)
            return {}

    async def _save_session_summary(self, user_id: str, summary: str) -> None:
        """Save a summary of the current session.

        Args:
            user_id: User ID
            summary: Session summary
        """
        try:
            from tripsage.utils.session_memory import store_session_summary

            await store_session_summary(user_id, summary, self.session_id)
            logger.info("Session summary saved")
        except Exception as e:
            logger.error("Error saving session summary: %s", str(e))
            log_exception(e)

    async def run(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the agent with user input.

        Args:
            user_input: User input text
            context: Optional context data

        Returns:
            Dictionary with the agent's response and other information
        """
        from agents import Runner

        # Add to message history
        self.messages_history.append(
            {"role": "user", "content": user_input, "timestamp": time.time()}
        )

        # Set up context
        run_context = context or {}

        # Initialize session data if this is the first message
        if not self.session_data and "user_id" in run_context:
            await self._initialize_session(run_context.get("user_id"))
            run_context["session_data"] = self.session_data
            run_context["session_id"] = self.session_id

        try:
            # Run the agent
            logger.info("Running agent: %s", self.name)
            result = await Runner.run(self.agent, user_input, context=run_context)

            # Extract response
            response = {
                "content": result.final_output,
                "tool_calls": (
                    result.tool_calls if hasattr(result, "tool_calls") else []
                ),
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
            logger.error("Error running agent: %s", str(e))
            log_exception(e)

            error_message = "An error occurred while processing your request."
            if isinstance(e, TripSageError):
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

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history.

        Returns:
            List of message dictionaries
        """
        return self.messages_history

    @function_tool
    async def echo(self, text: str) -> Dict[str, str]:
        """Echo the input back to the user.

        Args:
            text: Text to echo

        Returns:
            Dictionary with the echoed text
        """
        return {"text": text}
