# TripSage MCP Servers

This directory contains the configuration and integration code for Model Context Protocol (MCP) servers used in the TripSage system.

## Overview

MCP servers provide specialized functionality to AI agents through a standardized protocol. The TripSage system integrates several MCP servers to enable comprehensive travel planning capabilities, including:

- Airbnb accommodation search
- Google Maps location services
- Weather forecasting
- Flight booking
- Web crawling
- Calendar integration

## Directory Structure

- `openai_agents_config.js`: Configuration for MCP servers used with OpenAI Agents SDK
- `openai_agents_integration.py`: Utilities for integrating MCP servers with OpenAI Agents SDK
- `claude_desktop_config.json`: Configuration for MCP servers used with Claude Desktop
- `package.json`: Node.js dependencies for MCP servers

## Setup

### Prerequisites

- Node.js (v18+) for running MCP servers
- Python (v3.8+) for the integration code

### Installation

Install the required MCP server packages:

```bash
# Install dependencies
cd mcp_servers
npm install
```

### Environment Variables

Set the following environment variables in your `.env` file:

```plaintext
AIRBNB_API_KEY=your_airbnb_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

## Usage

### Starting Individual MCP Servers

You can start individual MCP servers using the provided npm scripts:

```bash
# Start Airbnb MCP server
npm run start:airbnb

# Start Google Maps MCP server
npm run start:google-maps
```

### With OpenAI Agents SDK

Use the `MCPServerManager` class from `openai_agents_integration.py` to manage MCP servers:

```python
import asyncio
from mcp_servers.openai_agents_integration import MCPServerManager
from agents import Agent, Runner

async def main():
    async with MCPServerManager() as manager:
        # Start specific MCP servers
        airbnb_server = await manager.start_server("airbnb")
        googlemaps_server = await manager.start_server("google-maps")

        # Create an agent with these servers
        agent = Agent(
            name="Travel Agent",
            instructions="Help users plan their travels...",
            mcp_servers=[airbnb_server, googlemaps_server],
        )

        # Run the agent
        result = await Runner.run(agent, "Find me a place to stay in Paris.")
        print(result.final_output)

asyncio.run(main())
```

Alternatively, use the helper function `create_agent_with_mcp_servers`:

```python
import asyncio
from mcp_servers.openai_agents_integration import create_agent_with_mcp_servers
from agents import Runner

async def main():
    # Create an agent with specific MCP servers
    agent = await create_agent_with_mcp_servers(
        name="Travel Agent",
        instructions="Help users plan their travels...",
        server_names=["airbnb", "google-maps"],
    )

    # Run the agent
    result = await Runner.run(agent, "Find me a place to stay in Paris.")
    print(result.final_output)

asyncio.run(main())
```

### With Claude Desktop

1. Start Claude Desktop
2. Open the Claude Desktop settings
3. Navigate to the "MCP" section
4. Click "Add Configuration"
5. Select the `claude_desktop_config.json` file

## Development Configuration

### Airbnb MCP Server with Options

You can pass additional options to the Airbnb MCP server:

```json
{
  "mcpServers": {
    "airbnb": {
      "command": "npx",
      "args": ["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"],
      "env": {
        "AIRBNB_API_KEY": "${AIRBNB_API_KEY}"
      }
    }
  }
}
```

### Google Maps MCP Server with Docker

If you prefer to run the Google Maps MCP server in a Docker container:

```json
{
  "mcpServers": {
    "google-maps": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GOOGLE_MAPS_API_KEY",
        "mcp/google-maps"
      ],
      "env": {
        "GOOGLE_MAPS_API_KEY": "${GOOGLE_MAPS_API_KEY}"
      }
    }
  }
}
```

## Deployment Considerations

For production deployment, consider:

- Using Docker containers for MCP servers
- Implementing a service manager for automatic restarts
- Configuring health checks and monitoring
- Setting up proper logging

## Additional Resources

- [OpenAI Agents SDK Documentation](https://openai.github.io/openai-agents-python/)
- [Model Context Protocol Documentation](https://github.com/lastmile-ai/ModelContextProtocol)
- [TripSage MCP Integration Guide](../docs/integrations/mcp_agents_sdk_integration.md)
- [OpenAI Agents SDK Implementation Guide](../docs/implementation/agents_sdk_implementation.md)
