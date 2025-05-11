"""
OpenAI Agents SDK MCP Server Integration for TripSage.

This module provides utilities for integrating MCP servers with the
OpenAI Agents SDK in the TripSage system.
"""

import asyncio
import os
from typing import Any, List, Optional

import dotenv

from agents import Agent, MCPServerStdio, Runner
from src.utils.logging import get_module_logger

# Load environment variables
dotenv.load_dotenv()

logger = get_module_logger(__name__)


class MCPServerManager:
    """Manager for MCP servers used with OpenAI Agents SDK."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the MCP server manager.

        Args:
            config_path: Path to the MCP server configuration file.
                Defaults to mcp_servers/openai_agents_config.js.
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), "openai_agents_config.js"
        )
        self.active_servers = {}
        logger.info("Initialized MCP Server Manager with config: %s", self.config_path)

    async def start_server(self, server_name: str) -> MCPServerStdio:
        """Start an MCP server by name.

        Args:
            server_name: Name of the MCP server to start

        Returns:
            The started MCP server instance

        Raises:
            ValueError: If the server name is not found in the configuration
        """
        if server_name in self.active_servers:
            logger.info("Server %s already started", server_name)
            return self.active_servers[server_name]

        # Import here to avoid circular imports
        import json
        import subprocess

        # Load the configuration
        try:
            # Execute node to load the config file and output as JSON
            process = subprocess.run(
                [
                    "node",
                    "-e",
                    f"const config = require('{self.config_path}'); console.log(JSON.stringify(config))",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            config = json.loads(process.stdout)
        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
            logger.error("Failed to load MCP server configuration: %s", str(e))
            raise ValueError(f"Failed to load MCP server configuration: {str(e)}")

        # Check if the server exists in the configuration
        if server_name not in config.get("mcpServers", {}):
            logger.error("MCP server %s not found in configuration", server_name)
            raise ValueError(f"MCP server {server_name} not found in configuration")

        # Get the server configuration
        server_config = config["mcpServers"][server_name]

        # Replace environment variables in the env configuration
        if "env" in server_config:
            env_config = {}
            for key, value in server_config["env"].items():
                if (
                    isinstance(value, str)
                    and value.startswith("${")
                    and value.endswith("}")
                ):
                    env_var = value[2:-1]
                    env_value = os.environ.get(env_var)
                    if env_value is not None:
                        env_config[key] = env_value
                else:
                    env_config[key] = value
            server_config["env"] = env_config

        # Start the MCP server
        logger.info("Starting MCP server: %s", server_name)
        server = MCPServerStdio(
            params={
                "command": server_config["command"],
                "args": server_config["args"],
                "env": server_config.get("env", {}),
            },
            cache_tools_list=True,  # Enable caching for better performance
        )

        # Initialize the server (this will start the process)
        await server.initialize()

        # Store the server instance
        self.active_servers[server_name] = server

        return server

    async def stop_server(self, server_name: str) -> None:
        """Stop an MCP server by name.

        Args:
            server_name: Name of the MCP server to stop

        Raises:
            ValueError: If the server is not currently running
        """
        if server_name not in self.active_servers:
            logger.warning("Server %s not running", server_name)
            return

        # Get the server instance
        server = self.active_servers[server_name]

        # Stop the server
        logger.info("Stopping MCP server: %s", server_name)
        await server.close()

        # Remove from active servers
        del self.active_servers[server_name]

    async def stop_all_servers(self) -> None:
        """Stop all running MCP servers."""
        for server_name in list(self.active_servers.keys()):
            await self.stop_server(server_name)

    async def get_mcp_servers(self, server_names: List[str]) -> List[MCPServerStdio]:
        """Get MCP server instances, starting them if necessary.

        Args:
            server_names: Names of the MCP servers to get or start

        Returns:
            List of MCP server instances
        """
        servers = []
        for name in server_names:
            server = await self.start_server(name)
            servers.append(server)
        return servers

    async def __aenter__(self) -> "MCPServerManager":
        """Enter the async context.

        Returns:
            The MCPServerManager instance
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context, stopping all servers.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        await self.stop_all_servers()


async def create_agent_with_mcp_servers(
    name: str,
    instructions: str,
    server_names: List[str],
    tools: Optional[List[Any]] = None,
    model: str = "gpt-4o",
) -> Agent:
    """Create an agent with access to MCP servers.

    Args:
        name: Name of the agent
        instructions: Instructions for the agent
        server_names: Names of MCP servers to connect to
        tools: Additional function tools to include
        model: Model to use for the agent

    Returns:
        The created agent with MCP servers connected
    """
    manager = MCPServerManager()
    mcp_servers = await manager.get_mcp_servers(server_names)

    # Create the agent with MCP servers
    agent = Agent(
        name=name,
        instructions=instructions,
        mcp_servers=mcp_servers,
        tools=tools or [],
        model=model,
    )

    return agent


if __name__ == "__main__":
    # Example of how to use the MCPServerManager
    async def main():
        # Start both MCP servers
        async with MCPServerManager() as manager:
            # Get MCP server instances for Airbnb and Google Maps
            airbnb_server = await manager.start_server("airbnb")
            googlemaps_server = await manager.start_server("google-maps")

            # List available tools
            airbnb_tools = await airbnb_server.list_tools()
            googlemaps_tools = await googlemaps_server.list_tools()

            print(
                f"Airbnb MCP tools: {', '.join(tool['name'] for tool in airbnb_tools)}"
            )
            print(
                f"Google Maps MCP tools: {', '.join(tool['name'] for tool in googlemaps_tools)}"
            )

            # Create an agent with both servers
            agent = Agent(
                name="TripSage Agent",
                instructions="You are a travel planning assistant that helps users find accommodations and navigate to destinations.",
                mcp_servers=[airbnb_server, googlemaps_server],
            )

            # Run the agent
            result = await Runner.run(
                agent,
                "Find me a place to stay in Paris and how to get there from the airport.",
            )
            print(result.final_output)

    # Run the example
    asyncio.run(main())
