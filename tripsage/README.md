# TripSage Core Package

This directory contains the core implementation of the TripSage AI travel planning system.

## Package Structure

- `tripsage/` - Core package
  - `agents/` - Agent implementations (TravelPlanningAgent, etc.)
  - `tools/` - Function tools for agents to use
  - `models/` - Core Pydantic data models
  - `utils/` - Common utility functions
  - `clients/` - MCP client implementations
  - `db/` - Database interactions
  - `api/` - API implementation
  - `cache/` - Caching implementation

## Agents

The `agents/` directory contains the agent implementations for the TripSage system. The base agent class (`BaseAgent`) provides common functionality for all agents, while specialized agents provide domain-specific capabilities.

## Tools

The `tools/` directory contains function tools that can be used by agents. Each module contains related tools:

- `time.py` - Time-related tools (getting current time, converting between timezones)
- `calendar.py` - Calendar-related tools (adding events, checking availability)
- `webcrawl.py` - Web crawling tools (searching, extracting information)
- `browser/` - Browser automation tools
- etc.

## Models

The `models/` directory contains Pydantic data models used throughout the system:

- `base.py` - Core response models
- `db.py` - Database entity models
- `mcp.py` - MCP request/response models

## Utils

The `utils/` directory contains common utility functions:

- `logging.py` - Logging configuration
- `settings.py` - Application settings
- `error_handling.py` - Error handling utilities
- `error_decorators.py` - Error handling decorators

## Clients

The `clients/` directory contains MCP client implementations that connect to external MCP servers:

- `base_client.py` - Base MCP client class
- `time_client.py` - Time MCP client
- `weather_client.py` - Weather MCP client
- etc.