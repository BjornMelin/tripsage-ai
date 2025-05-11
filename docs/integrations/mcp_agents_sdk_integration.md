# MCP Server Integration with OpenAI Agents SDK

This document describes how to integrate MCP servers with the OpenAI Agents SDK in the TripSage system.

## Table of Contents

- [MCP Server Integration with OpenAI Agents SDK](#mcp-server-integration-with-openai-agents-sdk)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Architecture](#architecture)
  - [Configuration](#configuration)
  - [Usage](#usage)
    - [Basic Usage](#basic-usage)
    - [Advanced Usage](#advanced-usage)
  - [Available MCP Servers](#available-mcp-servers)
    - [Airbnb MCP Server](#airbnb-mcp-server)
    - [Google Maps MCP Server](#google-maps-mcp-server)
  - [Best Practices](#best-practices)
  - [Troubleshooting](#troubleshooting)
    - [Server Fails to Start](#server-fails-to-start)
    - [Slow Performance](#slow-performance)
    - [API Rate Limits](#api-rate-limits)

## Introduction

The TripSage system integrates various Model Context Protocol (MCP) servers with the OpenAI Agents SDK to provide a comprehensive travel planning experience. MCP servers expose tools and functionality that can be accessed by AI agents, enabling them to interact with external services, APIs, and data sources.

This integration allows TripSage agents to leverage specialized services for:

- Searching and booking accommodations via Airbnb
- Retrieving location information, directions, and maps via Google Maps
- Collecting weather data, flight information, and more

## Architecture

The integration architecture follows this pattern:

```plaintext
┌─────────────────┐     ┌──────────────────┐    ┌───────────────────┐
│                 │     │                  │    │                   │
│  OpenAI Agent   │────▶│  MCP Manager     │───▶│  MCP Server 1     │
│                 │     │                  │    │                   │
└─────────────────┘     └──────────────────┘    └───────────────────┘
                              │                 ┌───────────────────┐
                              │                 │                   │
                              └────────────────▶│  MCP Server 2     │
                                                │                   │
                                                └───────────────────┘
```

Key components:

1. **OpenAI Agent**: Created using the OpenAI Agents SDK, configured with access to MCP servers
2. **MCP Manager**: Manages the lifecycle of MCP server processes
3. **MCP Servers**: Individual servers providing specialized functionality (e.g., Airbnb, Google Maps)

## Configuration

MCP servers are configured in the `mcp_servers/openai_agents_config.js` file. This file contains the settings for each server, including:

- Command to start the server
- Arguments to pass to the command
- Environment variables needed by the server

Example configuration:

```javascript
const config = {
  mcpServers: {
    // Airbnb MCP Server configuration
    airbnb: {
      command: "npx",
      args: ["-y", "@openbnb/mcp-server-airbnb"],
      env: {
        AIRBNB_API_KEY: "${AIRBNB_API_KEY}",
      },
    },
    // Google Maps MCP Server configuration
    "google-maps": {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-google-maps"],
      env: {
        GOOGLE_MAPS_API_KEY: "${GOOGLE_MAPS_API_KEY}",
      },
    },
  },
};
```

## Usage

### Basic Usage

To create an agent with MCP server integration:

```python
import asyncio
from mcp_servers.openai_agents_integration import create_agent_with_mcp_servers

async def main():
    # Create an agent with access to Airbnb and Google Maps MCP servers
    agent = await create_agent_with_mcp_servers(
        name="Travel Planning Agent",
        instructions="You are a travel planning assistant that helps users find accommodations and plan routes.",
        server_names=["airbnb", "google-maps"],
    )

    # Run the agent with a user query
    from agents import Runner
    result = await Runner.run(agent, "Find me a place to stay in Paris and how to get there from Charles de Gaulle airport.")
    print(result.final_output)

asyncio.run(main())
```

### Advanced Usage

For more control over the MCP server lifecycle:

```python
import asyncio
from mcp_servers.openai_agents_integration import MCPServerManager
from agents import Agent, Runner

async def main():
    # Start MCP servers using the context manager
    async with MCPServerManager() as manager:
        # Start specific servers
        airbnb_server = await manager.start_server("airbnb")
        googlemaps_server = await manager.start_server("google-maps")

        # Create an agent with these servers
        agent = Agent(
            name="Travel Planning Agent",
            instructions="You are a travel planning assistant that helps users find accommodations and plan routes.",
            mcp_servers=[airbnb_server, googlemaps_server],
        )

        # Run the agent
        result = await Runner.run(agent, "Find me a place to stay in Paris and how to get there from Charles de Gaulle airport.")
        print(result.final_output)

        # Servers will be automatically stopped when the context is exited

asyncio.run(main())
```

## Available MCP Servers

TripSage integrates the following MCP servers:

### Airbnb MCP Server

- **Package**: `@openbnb/mcp-server-airbnb`
- **Tools**:
  - `airbnb_search`: Search for accommodations
  - `airbnb_listing_details`: Get detailed information about a listing

### Google Maps MCP Server

- **Package**: `@modelcontextprotocol/server-google-maps`
- **Tools**:
  - `geocode`: Convert addresses to coordinates
  - `place_search`: Search for places
  - `place_details`: Get detailed information about a place
  - `directions`: Get directions between locations
  - `distance_matrix`: Calculate distances and travel times

## Best Practices

1. **Resource Management**: Use the `MCPServerManager` context manager to ensure proper cleanup of server processes.

2. **Caching**: MCP server responses are automatically cached using Redis. Configure appropriate TTLs for different data types.

3. **Error Handling**: Implement proper error handling in your agent workflows to handle API rate limits, service outages, etc.

4. **Environment Variables**: Store API keys and other sensitive information in environment variables.

5. **Tool Selection**: Configure your agent instructions to provide clear guidance on which tools to use for specific tasks.

## Troubleshooting

Common issues and solutions:

### Server Fails to Start

If an MCP server fails to start:

1. Check that the necessary package is installed (`npm list -g`).
2. Verify that the correct API keys are set in your environment.
3. Look for error messages in the console output.

### Slow Performance

If agent responses are slow:

1. Ensure Redis caching is properly configured.
2. Consider adjusting the cache TTLs for frequently accessed data.
3. Optimize agent prompts to reduce unnecessary tool calls.

### API Rate Limits

If you encounter API rate limits:

1. Implement retry logic with exponential backoff.
2. Consider upgrading your API subscription.
3. Use caching effectively to reduce the number of API calls.
