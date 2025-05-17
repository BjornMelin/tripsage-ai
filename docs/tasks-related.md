This file is a merged representation of a subset of the codebase, containing specifically included files, combined into a single document by Repomix.

# File Summary

## Purpose

This file contains a packed representation of the entire repository's contents.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format

The content is organized as follows:

1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
4. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines

- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes

- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Only files matching these patterns are included: implementation/, optimization/tripsage_optimization_strategy.md, reference/openai_agents_sdk.md, status/
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)

## Additional Info

# Directory Structure

```
implementation/
  agents_sdk_implementation.md
  dual_storage_refactoring_completed.md
  dual_storage_refactoring.md
  firecrawl_mcp_client_design.md
  flight_search_booking_implementation.md
  mcp_abstraction_layer.md
  mcp_integration_strategy.md
  README.md
  required_changes.md
  travel_agent_implementation.md
  tripsage_implementation_plan.md
  tripsage_todo_list.md
optimization/
  tripsage_optimization_strategy.md
reference/
  openai_agents_sdk.md
status/
  implementation_status.md
```

# Files

## File: implementation/agents_sdk_implementation.md

````markdown
# OpenAI Agents SDK Implementation Guide

This document provides a comprehensive guide for implementing AI agents using the OpenAI Agents SDK in the TripSage system.

## Table of Contents

- [Introduction](#introduction)
- [Setting Up OpenAI Agents SDK](#setting-up-openai-agents-sdk)
- [Agent Architecture](#agent-architecture)
- [MCP Integration](#mcp-integration)
- [Example Implementations](#example-implementations)
- [Best Practices](#best-practices)
- [Advanced Topics](#advanced-topics)

## Introduction

The OpenAI Agents SDK provides a lightweight, powerful framework for building and orchestrating AI agents with access to external tools and data sources. In TripSage, we use this SDK to implement travel planning agents that can access various Model Context Protocol (MCP) servers, databases, and other services.

Key advantages of the OpenAI Agents SDK:

- **Python-first approach**: Uses standard Python patterns instead of custom abstractions
- **Lightweight architecture**: Minimal core abstractions (Agents, Tools, Handoffs, Guardrails)
- **Flexible model support**: Works with various LLM providers through LiteLLM integration
- **MCP support**: Native integration with MCP servers
- **Tracing and observability**: Built-in tracing for debugging and monitoring

## Setting Up OpenAI Agents SDK

### Installation

```bash
pip install openai-agents
```

For additional features:

```bash
# For LiteLLM integration (non-OpenAI models)
pip install "openai-agents[litellm]"

# For visualization tools
pip install "openai-agents[viz]"
```

### Environment Setup

Configure the necessary environment variables:

```bash
# OpenAI API
export OPENAI_API_KEY=your_api_key

# MCP server API keys
export AIRBNB_API_KEY=your_airbnb_api_key
export GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

## Agent Architecture

In TripSage, we use a hierarchical agent architecture:

1. **Triage Agent**: Main entry point that determines the intent and routes to specialized agents
2. **Specialized Agents**:
   - **Travel Planning Agent**: Handles comprehensive travel itinerary planning
   - **Accommodation Agent**: Specializes in finding and booking accommodations
   - **Transportation Agent**: Focuses on flight and ground transportation
   - **Budget Agent**: Helps optimize travel budgets

### Basic Agent Implementation

```python
from agents import Agent, Runner

# Create a basic agent
agent = Agent(
    name="Travel Planning Agent",
    instructions="""
    You are an expert travel planning assistant for TripSage. Your goal is to help users
    plan optimal travel experiences by leveraging multiple data sources and adapting to
    their preferences and constraints.
    """,
    model="gpt-4o",  # Default model
)

# Run the agent
async def main():
    result = await Runner.run(agent, "I'm planning a trip to Paris next month.")
    print(result.final_output)
```

## MCP Integration

TripSage integrates several MCP servers with the OpenAI Agents SDK to provide specialized functionality.

### Configuring MCP Servers

MCP servers are defined in `mcp_servers/openai_agents_config.js` and integrated using the `MCPServerManager` from `mcp_servers/openai_agents_integration.py`.

Example integration:

```python
from mcp_servers.openai_agents_integration import MCPServerManager
from agents import Agent, Runner

async def main():
    # Initialize the MCP server manager
    async with MCPServerManager() as manager:
        # Start MCP servers
        airbnb_server = await manager.start_server("airbnb")
        googlemaps_server = await manager.start_server("google-maps")

        # Create an agent with MCP server access
        agent = Agent(
            name="Travel Agent",
            instructions="You are a travel planning assistant...",
            mcp_servers=[airbnb_server, googlemaps_server],
        )

        # Run the agent
        result = await Runner.run(agent, "Help me find a place to stay in Paris.")
        print(result.final_output)
```

### Simplified Integration

For simpler integration, use the `create_agent_with_mcp_servers` helper function:

```python
from mcp_servers.openai_agents_integration import create_agent_with_mcp_servers
from agents import Runner

async def main():
    # Create an agent with specific MCP servers
    agent = await create_agent_with_mcp_servers(
        name="Travel Agent",
        instructions="You are a travel planning assistant...",
        server_names=["airbnb", "google-maps"],
    )

    # Run the agent
    result = await Runner.run(agent, "Help me find a place to stay in Paris.")
    print(result.final_output)
```

## Example Implementations

### Travel Planning Agent with MCP Integration

```python
import asyncio
from agents import Agent, Runner, function_tool
from mcp_servers.openai_agents_integration import create_agent_with_mcp_servers

# Define custom function tools
@function_tool
def get_user_preferences(user_id: str) -> dict:
    """Get user preferences from the database.

    Args:
        user_id: The user's ID

    Returns:
        Dictionary of user preferences
    """
    # In a real implementation, fetch from database
    return {
        "budget": "medium",
        "preferred_accommodation_type": "hotel",
        "preferred_transportation": "public",
        "food_preferences": ["local cuisine", "vegetarian options"],
        "interests": ["museums", "architecture", "local culture"]
    }

async def create_travel_agent():
    # Create a travel agent with MCP server access
    agent = await create_agent_with_mcp_servers(
        name="TripSage Travel Planner",
        instructions="""
        You are an expert travel planner for TripSage. Help users plan their trips by:

        1. Understanding their destination, dates, budget, and preferences
        2. Suggesting accommodations using the Airbnb MCP server
        3. Providing transportation information using the Google Maps MCP server
        4. Creating detailed itineraries based on user interests
        5. Adjusting recommendations to fit budget constraints

        Always provide specific options with prices, ratings, and other relevant details.
        Use the get_user_preferences tool to fetch stored user preferences when available.
        """,
        server_names=["airbnb", "google-maps"],
        tools=[get_user_preferences],
        model="gpt-4o",
    )

    return agent

async def main():
    agent = await create_travel_agent()

    # Run the agent with a user query
    result = await Runner.run(agent, "I'm planning a 5-day trip to Paris in June for my anniversary. Budget is around $3000.")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
```

### Multi-Agent System with Handoffs

```python
import asyncio
from agents import Agent, Runner, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from mcp_servers.openai_agents_integration import create_agent_with_mcp_servers

async def setup_agent_system():
    # Create specialized agents
    accommodation_agent = await create_agent_with_mcp_servers(
        name="Accommodation Specialist",
        instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nYou are an accommodation specialist. Help users find the perfect place to stay based on their preferences, budget, and needs.",
        server_names=["airbnb"],
        model="gpt-4o",
    )

    transportation_agent = await create_agent_with_mcp_servers(
        name="Transportation Specialist",
        instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nYou are a transportation specialist. Help users plan their routes, find directions, and choose the best transportation options.",
        server_names=["google-maps"],
        model="gpt-4o",
    )

    # Create main triage agent
    triage_agent = Agent(
        name="TripSage Assistant",
        instructions="""
        You are the TripSage travel assistant. Your role is to:

        1. Understand the user's travel query
        2. For accommodation questions, handoff to the Accommodation Specialist
        3. For transportation and directions questions, handoff to the Transportation Specialist
        4. For general travel advice, answer directly

        Always maintain context throughout the conversation.
        """,
        handoffs=[accommodation_agent, transportation_agent],
        model="gpt-3.5-turbo",  # Using a cheaper model for triage
    )

    return triage_agent

async def main():
    agent = await setup_agent_system()

    # Run the agent with various queries
    queries = [
        "Can you help me find a nice hotel in Barcelona?",
        "How do I get from the Barcelona airport to the city center?",
        "What are some must-see attractions in Barcelona?"
    ]

    for query in queries:
        print(f"\nUser: {query}")
        result = await Runner.run(agent, query)
        print(f"Agent: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

When implementing agents with the OpenAI Agents SDK in TripSage:

1. **Write Clear Instructions**: Be specific about the agent's role, available tools, and how to use them

2. **Use the Right Model**: Choose models based on task complexity:

   - `gpt-4o` for complex planning and reasoning
   - `gpt-3.5-turbo` for simpler tasks like triage

3. **Implement Proper Error Handling**: Handle API errors, rate limits, etc. gracefully

4. **Use Handoffs Effectively**: Structure your agents hierarchically with clear handoff patterns

5. **Manage Context Size**: Keep prompts concise and use structured outputs to prevent context overflow

6. **Enable Tracing**: Use the SDK's built-in tracing for debugging and monitoring

7. **Secure Credentials**: Store API keys in environment variables, never in code

8. **Test Extensively**: Test agents with diverse queries and edge cases

## Advanced Topics

### Structured Output

Use structured output to ensure consistent, predictable agent responses:

```python
from pydantic import BaseModel
from typing import List, Optional
from agents import Agent

class TravelItinerary(BaseModel):
    destination: str
    start_date: str
    end_date: str
    accommodations: List[dict]
    activities: List[dict]
    transportation: List[dict]
    total_budget: float
    notes: Optional[str] = None

agent = Agent(
    name="Travel Planner",
    instructions="Create a travel itinerary based on user input...",
    output_type=TravelItinerary,
    # Other configuration...
)
```

### Guardrails

Implement guardrails to validate inputs and outputs:

```python
from agents import Agent, GuardrailFunctionOutput, InputGuardrail, Runner

async def validate_travel_request(ctx, agent, input_data):
    # Check if input contains required travel information
    has_destination = any(word in input_data.lower() for word in ["destination", "city", "location", "place", "country"])
    has_dates = any(word in input_data.lower() for word in ["date", "when", "month", "day", "week"])

    return GuardrailFunctionOutput(
        output_info={"valid_request": has_destination and has_dates},
        tripwire_triggered=not (has_destination and has_dates)
    )

agent = Agent(
    name="Travel Planner",
    instructions="Plan travel itineraries...",
    input_guardrails=[
        InputGuardrail(guardrail_function=validate_travel_request),
    ],
    # Other configuration...
)
```

### Custom Model Integration

To use non-OpenAI models:

```python
from agents import Agent
from agents.extensions.models.litellm_model import LitellmModel

# Create an agent with a different model provider
agent = Agent(
    name="Budget Travel Planner",
    instructions="You help users plan budget-friendly trips...",
    model=LitellmModel(model="anthropic/claude-3-5-sonnet-20240620"),
    # Other configuration...
)
```
````

## File: implementation/dual_storage_refactoring_completed.md

````markdown
# Dual Storage Pattern Refactoring: Completed

## Overview

This document provides a summary of the refactoring work completed for the dual storage pattern in TripSage. The refactoring has successfully:

1. Replaced the function-based approach with a service-based architecture
2. Eliminated redundant code patterns
3. Improved type safety with Pydantic models
4. Simplified the API for client code

## Changes Made

### 1. Created `DualStorageService` Abstract Base Class

Created a generic base class that provides a unified interface for dual storage operations:

```python
class DualStorageService(Generic[P, G], metaclass=abc.ABCMeta):
    """Base class for dual storage services in TripSage."""
    
    # CRUD operations with standardized implementation
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def retrieve(self, entity_id: str, include_graph: bool = False) -> Dict[str, Any]: ...
    async def update(self, entity_id: str, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def delete(self, entity_id: str) -> Dict[str, Any]: ...
    
    # Abstract methods to be implemented by entity-specific services
    @abc.abstractmethod
    async def _store_in_primary(self, data: Dict[str, Any]) -> str: ...
    @abc.abstractmethod
    async def _create_graph_entities(self, data: Dict[str, Any], entity_id: str) -> List[Dict[str, Any]]: ...
    # ...
```

### 2. Implemented `TripStorageService` Concrete Class

Created a concrete implementation for Trip entities that provides all the Trip-specific logic:

```python
class TripStorageService(DualStorageService[TripPrimaryModel, TripGraphModel]):
    """Service for storing and retrieving Trip data using the dual storage strategy."""
    
    def __init__(self):
        """Initialize the Trip Storage Service."""
        super().__init__(primary_client=db_client, graph_client=memory_client)
    
    async def _store_in_primary(self, data: Dict[str, Any]) -> str:
        """Store structured trip data in Supabase."""
        # Implementation...
    
    # ... other method implementations
```

### 3. Simplified `dual_storage.py` Module

Simplified the module to only expose the TripStorageService instance:

```python
"""
Dual storage strategy for TripSage.

This module provides direct access to the TripStorageService, which implements 
the dual storage strategy where structured data is stored in Supabase and 
relationships/unstructured data are stored in Neo4j via the Memory MCP.
"""

from src.utils.logging import get_module_logger
from src.utils.trip_storage_service import TripStorageService

logger = get_module_logger(__name__)

# Create service instance - the only thing needed from this module
trip_service = TripStorageService()
```

### 4. Updated Client Code

Updated the Travel Agent implementation to use the new service directly:

```python
@function_tool
async def create_trip(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new trip in the system."""
    try:
        from src.utils.dual_storage import trip_service
        
        # Make sure we have a user_id
        user_id = params.get("user_id")
        if not user_id:
            return {"success": False, "error": "User ID is required"}
        
        # Create trip using the TripStorageService
        result = await trip_service.create(params)
        
        # Return a simplified response
        return {
            "success": True,
            "trip_id": result["trip_id"],
            "message": "Trip created successfully",
            "entities_created": result["entities_created"],
            "relations_created": result["relations_created"],
            # ...
        }
    except Exception as e:
        # ...
```

## Benefits Achieved

1. **DRY principle**: Core dual storage logic is now implemented once in the base class
2. **Type safety**: Pydantic models ensure data validation for both primary and graph data
3. **Consistent interface**: All entity types (Trip, User, etc.) will use the same CRUD operations
4. **Extensibility**: New entity types can be added by implementing a new service
5. **Clear API**: Well-defined interface for all storage operations

## Future Work

1. Implement additional entity-specific storage services:
   - UserStorageService
   - DestinationStorageService
   - AccommodationStorageService

2. Enhance test coverage:
   - Add mocking for settings
   - Create comprehensive test suite for each service

3. Add documentation:
   - Create examples for each entity type
   - Document best practices for implementing new services

## Conclusion

The dual storage pattern refactoring has successfully transformed the function-based approach into a more maintainable, extensible service-based architecture. The new implementation follows SOLID principles and provides a clear, consistent interface for managing entities across both Supabase and Neo4j.

This refactoring reduces code duplication, improves type safety, and makes it easier to add support for new entity types in the future.
````

## File: implementation/dual_storage_refactoring.md

````markdown
# Dual Storage Pattern Refactoring

## Overview

The dual storage pattern is a key architectural component of TripSage, allowing us to store:

- Structured data in Supabase (relational database)
- Unstructured data and relationships in Neo4j (graph database via Memory MCP)

This document outlines the refactoring of this pattern to improve maintainability, testability, and extensibility.

## Previous Implementation

The previous implementation used a collection of functions in `src/utils/dual_storage.py` with specific implementations for each entity type. This approach had several limitations:

- Code duplication across entity types
- No clear interface for operations
- Difficult to extend to new entity types
- Limited testability due to tight coupling
- Lack of type safety for data validation

## New Design: Service-based Architecture

The refactored dual storage pattern uses a service-based architecture with:

1. **Abstract Base Class**: A generic `DualStorageService` class defines the interface and shared logic
2. **Entity-specific Services**: Concrete implementations for each entity type (e.g., `TripStorageService`)
3. **Standard CRUD Operations**: Create, Retrieve, Update, Delete operations for all entities
4. **Pydantic Models**: Type validation for both primary and graph data models
5. **Backwards Compatibility**: The original API is maintained for existing code

### Key Components

#### 1. `DualStorageService` (Base Class)

```python
class DualStorageService(Generic[P, G], metaclass=abc.ABCMeta):
    """Base class for dual storage services in TripSage."""
    
    # CRUD operations
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def retrieve(self, entity_id: str, include_graph: bool = False) -> Dict[str, Any]: ...
    async def update(self, entity_id: str, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def delete(self, entity_id: str) -> Dict[str, Any]: ...
    
    # Abstract methods to be implemented by subclasses
    @abc.abstractmethod
    async def _store_in_primary(self, data: Dict[str, Any]) -> str: ...
    
    @abc.abstractmethod
    async def _create_graph_entities(
        self, data: Dict[str, Any], entity_id: str
    ) -> List[Dict[str, Any]]: ...
    
    # ... other abstract methods
```

#### 2. `TripStorageService` (Concrete Implementation)

```python
class TripStorageService(DualStorageService[TripPrimaryModel, TripGraphModel]):
    """Service for storing and retrieving Trip data using the dual storage strategy."""
    
    def __init__(self):
        """Initialize the Trip Storage Service."""
        super().__init__(primary_client=db_client, graph_client=memory_client)
    
    async def _store_in_primary(self, data: Dict[str, Any]) -> str:
        """Store structured trip data in Supabase."""
        # Implementation
    
    # ... other method implementations
```

#### 3. Backwards Compatibility Layer

```python
# Create service instance
trip_service = TripStorageService()

async def store_trip_with_dual_storage(
    trip_data: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Store trip data using the dual storage strategy."""
    # Add user_id to trip_data
    trip_data["user_id"] = user_id
    
    # Use service to store trip
    result = await trip_service.create(trip_data)
    
    # Transform result to match existing API
    return {
        "trip_id": result["trip_id"],
        "entities_created": result["entities_created"],
        "relations_created": result["relations_created"],
        "supabase": result["primary_db"],
        "neo4j": result["graph_db"],
    }
```

## Benefits

1. **DRY principle**: Core logic is implemented once in the base class
2. **Type safety**: Pydantic models ensure data validation
3. **Consistent interface**: All entities use the same CRUD operations
4. **Extensibility**: New entity types can be added by implementing a new service
5. **Testability**: Services can be easily mocked and tested in isolation
6. **Clear API**: Well-defined interface for all storage operations

## Usage Example

### Creating a Trip

```python
# Old way
trip_id = await store_trip_with_dual_storage(trip_data, user_id)

# New way
trip_service = TripStorageService()
result = await trip_service.create({**trip_data, "user_id": user_id})
```

### Retrieving a Trip

```python
# Old way (was not previously implemented)
# New way
trip_service = TripStorageService()
trip = await trip_service.retrieve(trip_id)
```

## Todo

1. **Implement other entity services**:
   - UserStorageService
   - DestinationStorageService
   - AccommodationStorageService
   - ActivityStorageService

2. **Update tests**:
   - Create comprehensive test suite for the base class and all services
   - Mock dependencies for proper unit testing

3. **Documentation**:
   - Update API documentation
   - Add examples for all service operations

4. **Migration plan**:
   - Gradually migrate all code to use the new services
   - Eventually deprecate the old functions
````

## File: implementation/firecrawl_mcp_client_design.md

````markdown
# Firecrawl MCP Client Design and Implementation

## Overview

The `FirecrawlMCPClient` has been implemented to integrate with the Firecrawl MCP server (<https://github.com/mendableai/firecrawl-mcp-server>) for advanced web scraping and crawling capabilities in TripSage.

## Design Choices

### 1. Client Architecture

- **Singleton Pattern**: Implemented to ensure only one client instance exists, reducing resource overhead and ensuring consistent configuration.
- **Async Architecture**: All methods are asynchronous using `httpx.AsyncClient` for non-blocking I/O operations.
- **Error Handling**: Uses the `@with_error_handling` decorator for consistent error handling across all methods.

### 2. Caching Strategy

The client implements intelligent caching based on content type and domain:

- **Dynamic Content (Booking Sites)**:
  - Sites like `airbnb.com`, `booking.com`, `hotels.com` get a shorter TTL of 1 hour
  - This accounts for frequently changing prices and availability
  
- **Static Content**:
  - General web content gets a 24-hour TTL
  - Search results get a 12-hour TTL
  - Structured extraction data gets a 24-hour TTL

### 3. API Method Mapping

The client provides high-level methods that map to Firecrawl MCP tools:

- `scrape_url()` → `firecrawl_scrape` tool
- `crawl_url()` → `firecrawl_crawl` tool
- `extract_structured_data()` → `firecrawl_extract` tool
- `search_web()` → `firecrawl_search` tool
- `batch_scrape()` → `firecrawl_batch_scrape` tool
- `check_crawl_status()` → `firecrawl_check_crawl_status` tool

### 4. Configuration Integration

The client integrates with TripSage's MCP configuration system:

- Uses `FirecrawlMCPConfig` from `mcp_settings.py`
- Supports environment variable configuration
- Allows for both cloud and self-hosted Firecrawl instances

### 5. Parameter Models

Created Pydantic models for request parameters:

- `FirecrawlScrapeParams`: For single URL scraping
- `FirecrawlCrawlParams`: For website crawling
- `FirecrawlExtractParams`: For structured data extraction

These models:

- Provide type safety and validation
- Handle camelCase to snake_case conversion for MCP compatibility
- Support optional parameters with sensible defaults

## Implementation Details

### Request Flow

1. Client receives a request (e.g., `scrape_url()`)
2. Checks cache for existing result (if caching enabled)
3. If cache miss, builds MCP request using `_build_mcp_request()`
4. Sends request to MCP server using `httpx`
5. Processes response and extracts data
6. Caches result with appropriate TTL
7. Returns data to caller

### Error Handling

- HTTP errors are caught and logged
- The `@with_error_handling` decorator provides consistent error responses
- Failed requests are not cached

### Cache Key Strategy

Cache keys are constructed based on:

- Tool name (e.g., "firecrawl:scrape")
- Primary identifier (URL, query, etc.)
- Relevant parameters that affect the result

Example: `firecrawl:scrape:https://example.com`

## Usage Examples

```python
# Get the singleton client
client = get_firecrawl_client()

# Scrape a single URL
result = await client.scrape_url(
    "https://www.airbnb.com/rooms/123",
    params=FirecrawlScrapeParams(
        formats=["markdown", "html"],
        only_main_content=True
    )
)

# Extract structured data from multiple URLs
extracted_data = await client.extract_structured_data(
    urls=["https://hotel1.com", "https://hotel2.com"],
    prompt="Extract hotel name, price, and amenities",
    params=FirecrawlExtractParams(
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number"},
                "amenities": {"type": "array", "items": {"type": "string"}}
            }
        }
    )
)

# Search the web with content scraping
search_results = await client.search_web(
    query="best hotels in Paris",
    limit=10,
    scrape_results=True
)
```

## Future Enhancements

1. **Batch Processing Optimization**: Implement better handling for large batch operations
2. **Rate Limiting**: Add client-side rate limiting to complement MCP server limits
3. **Webhook Support**: Add support for crawl webhooks for long-running operations
4. **Metrics Collection**: Integrate with TripSage's metrics system for monitoring
5. **Content Type Detection**: Auto-adjust caching strategy based on detected content type

## Integration with TripSage

The `FirecrawlMCPClient` will be used by:

1. `SourceSelectionLogic` in `source_selector.py` for determining when to use Firecrawl
2. Unified webcrawl tools in `webcrawl_tools.py` for agent access
3. Accommodation and flight search agents for scraping booking sites
4. Destination research agents for extracting structured travel information
````

## File: implementation/flight_search_booking_implementation.md

````markdown
# Flight Search and Booking Implementation Guide

This document provides a comprehensive implementation guide for the Flight Search and Booking capabilities (TRAVELAGENT-002) in the TripSage system.

## Overview

The Flight Search and Booking module enables the TripSage Travel Planning Agent to search for flight options across multiple providers, compare prices, track historical pricing data, and facilitate the booking process. It leverages the Flights MCP Server's integration with the Duffel API while adding agent-specific capabilities for enhanced user experience and decision support.

## Architecture

The Flight Search and Booking functionality follows a layered architecture:

1. **User Interface Layer**: Handled by the Travel Planning Agent
2. **Business Logic Layer**: Implemented in the TripSageTravelAgent class
3. **Service Layer**: Flights MCP Server with Duffel API integration
4. **Data Layer**: Dual storage architecture (Supabase + Knowledge Graph)

## MCP Tools Exposed

The following tools are exposed by the Flights MCP and utilized by the Travel Planning Agent:

| Tool Name                   | Description                                          | Parameters                                                                        |
| --------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------- |
| `search_flights`            | Search for one-way or round-trip flights             | `origin`, `destination`, `departure_date`, `return_date`, `adults`, `cabin_class` |
| `search_multi_city`         | Search for multi-city flight itineraries             | `segments`, `adults`, `cabin_class`                                               |
| `get_airports`              | Get airport information by IATA code or search       | `code` or `search_term`                                                           |
| `check_flight_availability` | Check detailed availability for a specific flight    | `flight_id`                                                                       |
| `get_flight_prices`         | Get current and historical prices for a flight route | `origin`, `destination`, `departure_date`                                         |
| `track_flight_price`        | Start price tracking for a specific flight route     | `origin`, `destination`, `departure_date`, `return_date`, `notification_email`    |

## API Integrations

### Duffel API

The implementation utilizes the Duffel API through the Flights MCP Server:

```python
# Simplified example of Duffel API integration in Flights MCP Server
from duffel_api import Duffel
from datetime import datetime

class DuffelClient:
    def __init__(self, api_key: str):
        self.client = Duffel(access_token=api_key)

    async def search_flights(self, origin: str, destination: str,
                            departure_date: str, return_date: str = None,
                            passengers: int = 1, cabin_class: str = "economy"):
        """Search for flights using the Duffel API."""
        passengers_data = [{"type": "adult"}] * passengers

        # Build request
        request_data = {
            "slices": [
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date
                }
            ],
            "passengers": passengers_data,
            "cabin_class": cabin_class
        }

        # Add return slice if round-trip
        if return_date:
            request_data["slices"].append({
                "origin": destination,
                "destination": origin,
                "departure_date": return_date
            })

        # Create the offer request
        offer_request = await self.client.offer_requests.create(request_data)

        # Get the offers
        offers = await self.client.offers.list(offer_request_id=offer_request.id)

        return self._format_offers(offers)
```

## Implementation Details

### Flight Search Implementation

The TripSageTravelAgent class includes enhanced methods for flight search and comparison:

```python
# src/agents/flight_search.py

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
import asyncio
import logging

from src.cache.redis_cache import redis_cache
from src.db.client import get_client
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class FlightSearchParams(BaseModel):
    """Model for flight search parameters validation."""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin airport IATA code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination airport IATA code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(None, description="Return date for round trips (YYYY-MM-DD)")
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    cabin_class: str = Field("economy", description="Cabin class (economy, premium_economy, business, first)")
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price in USD")
    max_stops: Optional[int] = Field(None, ge=0, le=2, description="Maximum number of stops")
    preferred_airlines: Optional[List[str]] = Field(None, description="List of preferred airline codes")

    @validator("departure_date", "return_date")
    def validate_date_format(cls, v):
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @validator("return_date")
    def validate_return_date(cls, v, values):
        if v and "departure_date" in values:
            dep_date = datetime.strptime(values["departure_date"], "%Y-%m-%d")
            ret_date = datetime.strptime(v, "%Y-%m-%d")
            if ret_date <= dep_date:
                raise ValueError("Return date must be after departure date")
        return v


class TripSageFlightSearch:
    """Flight search functionality for the TripSage Travel Agent."""

    def __init__(self, flights_client):
        """Initialize with a flights MCP client."""
        self.flights_client = flights_client

    async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for flights with enhanced features and filtering.

        Args:
            params: Flight search parameters validated using FlightSearchParams

        Returns:
            Enhanced flight search results with filtering and sorting
        """
        try:
            # Validate parameters
            search_params = FlightSearchParams(**params)

            # Check cache first
            cache_key = f"flight_search:{search_params.origin}:{search_params.destination}:" \
                      f"{search_params.departure_date}:{search_params.return_date}:" \
                      f"{search_params.adults}:{search_params.cabin_class}"

            cached_result = await redis_cache.get(cache_key)
            if cached_result:
                # Apply post-search filtering to cached results
                filtered_results = self._filter_flights(
                    cached_result,
                    max_price=search_params.max_price,
                    max_stops=search_params.max_stops,
                    preferred_airlines=search_params.preferred_airlines
                )
                return {**filtered_results, "cache": "hit"}

            # Call Flights MCP client
            flight_results = await self.flights_client.search_flights(
                origin=search_params.origin,
                destination=search_params.destination,
                departure_date=search_params.departure_date,
                return_date=search_params.return_date,
                adults=search_params.adults,
                cabin_class=search_params.cabin_class
            )

            if "error" in flight_results:
                return flight_results

            # Cache raw results before filtering
            await redis_cache.set(
                cache_key,
                flight_results,
                ttl=3600  # Cache for 1 hour
            )

            # Apply post-search filtering
            filtered_results = self._filter_flights(
                flight_results,
                max_price=search_params.max_price,
                max_stops=search_params.max_stops,
                preferred_airlines=search_params.preferred_airlines
            )

            # Add price history data
            enhanced_results = await self._add_price_history(filtered_results)

            return {**enhanced_results, "cache": "miss"}

        except Exception as e:
            logger.error(f"Flight search error: {str(e)}")
            return {"error": f"Flight search error: {str(e)}"}

    def _filter_flights(self, results: Dict[str, Any],
                        max_price: Optional[float] = None,
                        max_stops: Optional[int] = None,
                        preferred_airlines: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply filters to flight search results.

        Args:
            results: Raw flight search results
            max_price: Maximum price filter
            max_stops: Maximum stops filter
            preferred_airlines: List of preferred airlines

        Returns:
            Filtered flight results
        """
        if "offers" not in results:
            return results

        filtered_offers = results["offers"].copy()

        # Apply price filter
        if max_price is not None:
            filtered_offers = [
                offer for offer in filtered_offers
                if offer.get("total_amount") <= max_price
            ]

        # Apply stops filter
        if max_stops is not None:
            filtered_offers = [
                offer for offer in filtered_offers
                if all(len(slice.get("segments", [])) - 1 <= max_stops
                      for slice in offer.get("slices", []))
            ]

        # Apply airline preference filter
        if preferred_airlines and len(preferred_airlines) > 0:
            # Boost preferred airlines by putting them first
            preferred = [
                offer for offer in filtered_offers
                if any(segment.get("operating_carrier_code") in preferred_airlines
                      for slice in offer.get("slices", [])
                      for segment in slice.get("segments", []))
            ]

            non_preferred = [
                offer for offer in filtered_offers
                if not any(segment.get("operating_carrier_code") in preferred_airlines
                          for slice in offer.get("slices", [])
                          for segment in slice.get("segments", []))
            ]

            filtered_offers = preferred + non_preferred

        # Sort by price (lowest first)
        filtered_offers.sort(key=lambda x: x.get("total_amount", float("inf")))

        # Return updated results
        return {
            **results,
            "offers": filtered_offers,
            "filtered_count": len(filtered_offers),
            "original_count": len(results.get("offers", []))
        }

    async def _add_price_history(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Add price history data to flight search results.

        Args:
            results: Filtered flight results

        Returns:
            Enhanced results with price history
        """
        if "origin" not in results or "destination" not in results:
            return results

        try:
            # Get price history data
            origin = results["origin"]
            destination = results["destination"]
            departure_date = results.get("departure_date")

            price_history = await self._get_price_history(
                origin, destination, departure_date
            )

            # Add pricing insights
            if price_history and "prices" in price_history:
                current_price = min(
                    offer.get("total_amount", float("inf"))
                    for offer in results.get("offers", [])
                )

                # Calculate pricing insights
                avg_price = sum(price_history["prices"]) / len(price_history["prices"])
                min_price = min(price_history["prices"])
                max_price = max(price_history["prices"])

                price_insights = {
                    "current_vs_avg": round((current_price / avg_price - 1) * 100, 1),
                    "current_vs_min": round((current_price / min_price - 1) * 100, 1),
                    "current_vs_max": round((current_price / max_price - 1) * 100, 1),
                    "avg_price": avg_price,
                    "min_price": min_price,
                    "max_price": max_price,
                    "recommendation": self._generate_price_recommendation(
                        current_price, avg_price, min_price, price_history
                    )
                }

                return {
                    **results,
                    "price_history": price_history,
                    "price_insights": price_insights
                }

            return results

        except Exception as e:
            logger.warning(f"Error adding price history: {str(e)}")
            return results

    async def _get_price_history(
        self, origin: str, destination: str, departure_date: Optional[str]
    ) -> Dict[str, Any]:
        """Get price history for a route.

        Args:
            origin: Origin airport code
            destination: Destination airport code
            departure_date: Departure date

        Returns:
            Price history data
        """
        try:
            # Get data from database
            db_client = get_client()
            history = await db_client.get_flight_price_history(
                origin=origin,
                destination=destination,
                date_from=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                date_to=datetime.now().strftime("%Y-%m-%d")
            )

            # Format history data
            if history:
                return {
                    "prices": [item["price"] for item in history],
                    "dates": [item["date"] for item in history],
                    "count": len(history)
                }

            # If no history in database, try getting from Flights MCP
            if hasattr(self.flights_client, "get_flight_prices"):
                try:
                    return await self.flights_client.get_flight_prices(
                        origin=origin,
                        destination=destination,
                        departure_date=departure_date
                    )
                except Exception as e:
                    logger.warning(f"Failed to get price history from MCP: {str(e)}")

            return {}

        except Exception as e:
            logger.error(f"Error retrieving price history: {str(e)}")
            return {}

    def _generate_price_recommendation(
        self, current_price: float, avg_price: float, min_price: float, history: Dict[str, Any]
    ) -> str:
        """Generate a price recommendation based on historical data.

        Args:
            current_price: Current lowest price
            avg_price: Average historical price
            min_price: Minimum historical price
            history: Price history data

        Returns:
            Price recommendation string
        """
        # Calculate thresholds
        good_deal_threshold = avg_price * 0.9  # 10% below average
        great_deal_threshold = avg_price * 0.8  # 20% below average

        if current_price <= min_price * 1.05:  # Within 5% of historical minimum
            return "Book now - this is among the lowest prices we've seen"
        elif current_price <= great_deal_threshold:
            return "Great deal - price significantly below average"
        elif current_price <= good_deal_threshold:
            return "Good deal - price below average"
        elif current_price <= avg_price * 1.1:  # Within 10% of average
            return "Fair price - close to typical prices for this route"
        else:
            return "Price higher than average - consider monitoring for better deals"
```

### Flight Booking Implementation

The booking functionality provides a streamlined workflow for reservations:

```python
# src/agents/flight_booking.py

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator
import asyncio
import logging
import uuid

from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class FlightBookingParams(BaseModel):
    """Model for flight booking parameters validation."""
    offer_id: str = Field(..., description="Duffel offer ID to book")
    trip_id: Optional[str] = Field(None, description="TripSage trip ID for association")
    passengers: List[Dict[str, Any]] = Field(..., min_items=1, description="Passenger information")
    payment_details: Dict[str, Any] = Field(..., description="Payment information")
    contact_details: Dict[str, Any] = Field(..., description="Contact information")

    @validator("passengers")
    def validate_passengers(cls, v):
        for passenger in v:
            required_fields = ["given_name", "family_name", "gender", "born_on"]
            for field in required_fields:
                if field not in passenger:
                    raise ValueError(f"Passenger missing required field: {field}")
        return v

    @validator("payment_details")
    def validate_payment(cls, v):
        required_fields = ["type", "amount", "currency"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Payment details missing required field: {field}")
        return v

    @validator("contact_details")
    def validate_contact(cls, v):
        required_fields = ["email", "phone"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Contact details missing required field: {field}")
        return v


class TripSageFlightBooking:
    """Flight booking functionality for the TripSage Travel Agent."""

    def __init__(self, flights_client):
        """Initialize with a flights MCP client."""
        self.flights_client = flights_client

    async def book_flight(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Book a flight based on a selected offer.

        Args:
            params: Booking parameters validated using FlightBookingParams

        Returns:
            Booking confirmation and status
        """
        try:
            # Validate parameters
            booking_params = FlightBookingParams(**params)

            # Call Flights MCP client to create order
            booking_result = await self.flights_client.create_order(
                offer_id=booking_params.offer_id,
                passengers=booking_params.passengers,
                payment_details=booking_params.payment_details,
                contact_details=booking_params.contact_details
            )

            if "error" in booking_result:
                return booking_result

            # If booking successful, store in TripSage database
            if booking_params.trip_id:
                await self._store_booking_in_database(
                    trip_id=booking_params.trip_id,
                    booking_result=booking_result
                )

            # Store in knowledge graph
            await self._update_knowledge_graph(booking_result)

            return {
                "success": True,
                "booking_id": booking_result.get("booking_id"),
                "confirmed": booking_result.get("status") == "confirmed",
                "total_price": booking_result.get("total_amount"),
                "currency": booking_result.get("currency"),
                "booking_details": booking_result
            }

        except Exception as e:
            logger.error(f"Flight booking error: {str(e)}")
            return {"error": f"Flight booking error: {str(e)}"}

    async def _store_booking_in_database(
        self, trip_id: str, booking_result: Dict[str, Any]
    ) -> None:
        """Store booking details in TripSage database.

        Args:
            trip_id: TripSage trip ID
            booking_result: Booking result from Flights MCP
        """
        try:
            from src.db.client import get_client
            db_client = get_client()

            # Extract flight information
            slices = booking_result.get("slices", [])
            for slice_idx, slice_data in enumerate(slices):
                # Create flight record for each slice
                flight_data = {
                    "trip_id": trip_id,
                    "airline": slice_data.get("operating_carrier", {}).get("name"),
                    "flight_number": "-".join([
                        segment.get("operating_carrier_code", ""),
                        segment.get("operating_flight_number", "")
                    ]) for segment in slice_data.get("segments", []),
                    "origin": slice_data.get("origin", {}).get("iata_code"),
                    "destination": slice_data.get("destination", {}).get("iata_code"),
                    "departure_time": slice_data.get("departure_datetime"),
                    "arrival_time": slice_data.get("arrival_datetime"),
                    "price": booking_result.get("total_amount") / len(slices) if len(slices) > 0 else 0,
                    "booking_reference": booking_result.get("booking_reference"),
                    "status": "booked"
                }

                # Add flight to database
                await db_client.create_flight(flight_data)

        except Exception as e:
            logger.error(f"Error storing booking in database: {str(e)}")

    async def _update_knowledge_graph(self, booking_result: Dict[str, Any]) -> None:
        """Update knowledge graph with booking information.

        Args:
            booking_result: Booking result from Flights MCP
        """
        try:
            # Only proceed if memory client is available
            if not hasattr(self, "memory_client") or not self.memory_client:
                return

            # Extract entities and observations
            booking_id = booking_result.get("booking_id")
            airline = booking_result.get("slices", [{}])[0].get("operating_carrier", {}).get("name")
            route = f"{booking_result.get('origin', {}).get('iata_code')}-{booking_result.get('destination', {}).get('iata_code')}"

            # Create booking entity
            await self.memory_client.create_entities([{
                "name": f"Booking:{booking_id}",
                "entityType": "Booking",
                "observations": [
                    f"Booking reference: {booking_result.get('booking_reference')}",
                    f"Airline: {airline}",
                    f"Route: {route}",
                    f"Price: {booking_result.get('total_amount')} {booking_result.get('currency')}",
                    f"Status: {booking_result.get('status')}"
                ]
            }])

            # Create relations
            relations = []

            # Relation to airline
            if airline:
                relations.append({
                    "from": f"Booking:{booking_id}",
                    "relationType": "with_airline",
                    "to": airline
                })

            # Relation to origin/destination
            origin = booking_result.get("origin", {}).get("iata_code")
            destination = booking_result.get("destination", {}).get("iata_code")

            if origin:
                relations.append({
                    "from": f"Booking:{booking_id}",
                    "relationType": "departs_from",
                    "to": origin
                })

            if destination:
                relations.append({
                    "from": f"Booking:{booking_id}",
                    "relationType": "arrives_at",
                    "to": destination
                })

            # Create relations if any exist
            if relations:
                await self.memory_client.create_relations(relations)

        except Exception as e:
            logger.warning(f"Error updating knowledge graph: {str(e)}")
```

### Integration with the Travel Planning Agent

This functionality is integrated into the TripSageTravelAgent class:

```python
# src/agents/travel_agent_impl.py
# Existing imports...
from .flight_search import TripSageFlightSearch, FlightSearchParams
from .flight_booking import TripSageFlightBooking, FlightBookingParams

class TripSageTravelAgent(TravelAgent):
    """Comprehensive travel planning agent for TripSage with all integrated tools."""

    def __init__(
        self,
        name: str = "TripSage Travel Planner",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the TripSage travel agent with all required tools and integrations."""
        super().__init__(name=name, model=model, temperature=temperature)

        # Initialize MCP clients
        self.flights_client = get_flights_client()
        # Other clients...

        # Initialize specialized modules
        self.flight_search = TripSageFlightSearch(self.flights_client)
        self.flight_booking = TripSageFlightBooking(self.flights_client)

        # Register all MCP tools
        self._register_all_mcp_tools()

        # Initialize knowledge graph
        self._initialize_knowledge_graph()

        logger.info("TripSage Travel Agent fully initialized with all MCP tools")

    # Existing methods...

    @function_tool
    async def enhanced_flight_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced flight search with filtering, price history, and recommendations.

        Args:
            params: Search parameters including:
                origin: Origin airport IATA code (e.g., 'SFO')
                destination: Destination airport IATA code (e.g., 'JFK')
                departure_date: Departure date (YYYY-MM-DD)
                return_date: Return date for round trips (YYYY-MM-DD)
                adults: Number of adult passengers (default: 1)
                cabin_class: Cabin class (economy, premium_economy, business, first)
                max_price: Maximum price in USD (optional)
                max_stops: Maximum number of stops (optional)
                preferred_airlines: List of preferred airline codes (optional)

        Returns:
            Comprehensive flight search results with price insights and recommendations
        """
        return await self.flight_search.search_flights(params)

    @function_tool
    async def advanced_flight_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for flight options with flexible dates to find the best deals.

        Args:
            params: Search parameters including:
                origin: Origin airport IATA code
                destination: Destination airport IATA code
                date_from: Start of date range (YYYY-MM-DD)
                date_to: End of date range (YYYY-MM-DD)
                trip_length: Length of trip in days for return flights
                adults: Number of adult passengers
                cabin_class: Cabin class

        Returns:
            Best flight options across the date range
        """
        try:
            # Validate core parameters
            required = ["origin", "destination", "date_from", "date_to"]
            for param in required:
                if param not in params:
                    return {"error": f"Missing required parameter: {param}"}

            origin = params["origin"]
            destination = params["destination"]
            date_from = datetime.strptime(params["date_from"], "%Y-%m-%d")
            date_to = datetime.strptime(params["date_to"], "%Y-%m-%d")
            trip_length = params.get("trip_length")
            adults = params.get("adults", 1)
            cabin_class = params.get("cabin_class", "economy")

            # Generate dates to search
            if (date_to - date_from).days > 30:
                # Limit search to 30 days to avoid too many API calls
                date_to = date_from + timedelta(days=30)

            dates_to_search = []
            current_date = date_from
            while current_date <= date_to:
                dates_to_search.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)

            # Search flights for each date combination
            results = []

            # Limit number of concurrent searches
            sem = asyncio.Semaphore(3)

            async def search_for_date(dep_date):
                async with sem:
                    search_params = {
                        "origin": origin,
                        "destination": destination,
                        "departure_date": dep_date,
                        "adults": adults,
                        "cabin_class": cabin_class
                    }

                    # Add return date if trip length specified
                    if trip_length:
                        ret_date = (datetime.strptime(dep_date, "%Y-%m-%d") +
                                   timedelta(days=trip_length)).strftime("%Y-%m-%d")
                        search_params["return_date"] = ret_date

                    result = await self.flight_search.search_flights(search_params)

                    # Extract best price for this date
                    if "offers" in result and result["offers"]:
                        best_price = min(
                            offer.get("total_amount", float("inf"))
                            for offer in result["offers"]
                        )

                        return {
                            "departure_date": dep_date,
                            "return_date": search_params.get("return_date"),
                            "best_price": best_price,
                            "currency": result["offers"][0].get("currency", "USD"),
                            "offer_count": len(result["offers"])
                        }

                    return None

            # Run searches concurrently
            search_tasks = [search_for_date(date) for date in dates_to_search]
            date_results = await asyncio.gather(*search_tasks)

            # Filter out None results and sort by price
            valid_results = [r for r in date_results if r]
            valid_results.sort(key=lambda x: x.get("best_price", float("inf")))

            return {
                "origin": origin,
                "destination": destination,
                "date_range": {
                    "from": params["date_from"],
                    "to": params["date_to"]
                },
                "trip_length": trip_length,
                "best_date": valid_results[0] if valid_results else None,
                "all_dates": valid_results,
                "total_options": len(valid_results)
            }

        except Exception as e:
            logger.error(f"Advanced flight search error: {str(e)}")
            return {"error": f"Advanced flight search error: {str(e)}"}

    @function_tool
    async def book_flight(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Book a flight based on a selected offer.

        Args:
            params: Booking parameters including:
                offer_id: Duffel offer ID to book
                trip_id: TripSage trip ID for association (optional)
                passengers: List of passenger information
                payment_details: Payment information
                contact_details: Contact information

        Returns:
            Booking confirmation and details
        """
        return await self.flight_booking.book_flight(params)

    @function_tool
    async def track_flight_prices(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set up price tracking for a specific flight route.

        Args:
            params: Tracking parameters including:
                origin: Origin airport IATA code
                destination: Destination airport IATA code
                departure_date: Departure date or date range
                return_date: Return date or date range (optional)
                email: Email address for notifications
                price_threshold: Target price for alerts (optional)

        Returns:
            Confirmation of price tracking setup
        """
        try:
            # Validate required parameters
            required = ["origin", "destination", "departure_date", "email"]
            for param in required:
                if param not in params:
                    return {"error": f"Missing required parameter: {param}"}

            # Call Flights MCP to set up tracking
            if hasattr(self.flights_client, "track_flight_price"):
                tracking_result = await self.flights_client.track_flight_price(
                    origin=params["origin"],
                    destination=params["destination"],
                    departure_date=params["departure_date"],
                    return_date=params.get("return_date"),
                    notification_email=params["email"],
                    price_threshold=params.get("price_threshold")
                )

                return tracking_result

            # Fallback implementation if MCP doesn't support tracking
            tracking_id = str(uuid.uuid4())

            # Store tracking request in database
            from src.db.client import get_client
            db_client = get_client()

            await db_client.create_price_tracking(
                tracking_id=tracking_id,
                origin=params["origin"],
                destination=params["destination"],
                departure_date=params["departure_date"],
                return_date=params.get("return_date"),
                email=params["email"],
                price_threshold=params.get("price_threshold"),
                status="active"
            )

            return {
                "tracking_id": tracking_id,
                "status": "active",
                "message": "Price tracking created successfully"
            }

        except Exception as e:
            logger.error(f"Flight price tracking error: {str(e)}")
            return {"error": f"Flight price tracking error: {str(e)}"}
```

## Caching Strategy

The flight search implementation includes a caching strategy for improved performance:

1. **Client-side Cache**: Raw flight search results are cached before filtering
2. **Cache Keys**: Based on origin, destination, dates, passengers, and cabin class
3. **TTL Strategy**: 1-hour TTL for flight search results due to price volatility
4. **Filtering**: Post-cache filtering for max_price, max_stops, and airline preferences

This approach allows for efficient retrieval of flight data while still providing flexible filtering options.

## Dual Storage Implementation

The flight booking functionality leverages the dual storage architecture:

1. **Supabase**: Stores structured flight booking data in the `flights` table

   - Linked to `trips` table via `trip_id` foreign key
   - Includes booking references, prices, and flight details

2. **Knowledge Graph**: Stores semantic relationships and observations
   - Creates `Booking` entity type with observations
   - Establishes relationships like `with_airline`, `departs_from`, and `arrives_at`
   - Links bookings to airports, airlines, and destinations

This dual approach allows for both structured queries and semantic reasoning about flight bookings.

## Testing Strategy

### Unit Tests

```python
# tests/agents/test_flight_search.py
import pytest
from unittest.mock import AsyncMock, patch
import datetime

from src.agents.flight_search import TripSageFlightSearch, FlightSearchParams

@pytest.fixture
def mock_flights_client():
    client = AsyncMock()
    client.search_flights.return_value = {
        "origin": "SFO",
        "destination": "JFK",
        "departure_date": "2025-06-15",
        "offers": [
            {
                "id": "offer_1",
                "total_amount": 299.99,
                "currency": "USD",
                "slices": [
                    {
                        "segments": [
                            {
                                "operating_carrier_code": "UA",
                                "operating_flight_number": "1234",
                                "departure": {
                                    "airport": {"iata_code": "SFO"},
                                    "datetime": "2025-06-15T08:00:00"
                                },
                                "arrival": {
                                    "airport": {"iata_code": "JFK"},
                                    "datetime": "2025-06-15T16:30:00"
                                }
                            }
                        ]
                    }
                ]
            },
            {
                "id": "offer_2",
                "total_amount": 349.99,
                "currency": "USD",
                "slices": [
                    {
                        "segments": [
                            {
                                "operating_carrier_code": "DL",
                                "operating_flight_number": "5678",
                                "departure": {
                                    "airport": {"iata_code": "SFO"},
                                    "datetime": "2025-06-15T10:00:00"
                                },
                                "arrival": {
                                    "airport": {"iata_code": "JFK"},
                                    "datetime": "2025-06-15T18:30:00"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
    return client

@pytest.mark.asyncio
async def test_search_flights(mock_flights_client):
    """Test the flight search functionality."""
    # Setup
    search = TripSageFlightSearch(mock_flights_client)

    # Mock redis cache
    with patch("src.cache.redis_cache.redis_cache.get") as mock_get:
        mock_get.return_value = None  # No cache hit

        with patch("src.cache.redis_cache.redis_cache.set") as mock_set:
            # Test search
            result = await search.search_flights({
                "origin": "SFO",
                "destination": "JFK",
                "departure_date": "2025-06-15",
                "adults": 1,
                "cabin_class": "economy",
                "max_price": 400
            })

            # Assertions
            assert result["cache"] == "miss"
            assert len(result["offers"]) == 2
            assert result["filtered_count"] == 2
            assert result["origin"] == "SFO"
            assert result["destination"] == "JFK"

            # Test max_price filter
            result = await search.search_flights({
                "origin": "SFO",
                "destination": "JFK",
                "departure_date": "2025-06-15",
                "adults": 1,
                "cabin_class": "economy",
                "max_price": 300
            })

            assert len(result["offers"]) == 1
            assert result["offers"][0]["id"] == "offer_1"

@pytest.mark.asyncio
async def test_flight_search_params_validation():
    """Test parameter validation for flight search."""
    # Valid parameters
    valid_params = {
        "origin": "SFO",
        "destination": "JFK",
        "departure_date": "2025-06-15",
        "adults": 1,
        "cabin_class": "economy"
    }
    params = FlightSearchParams(**valid_params)
    assert params.origin == "SFO"

    # Invalid origin (too short)
    with pytest.raises(ValueError):
        FlightSearchParams(**{**valid_params, "origin": "SF"})

    # Invalid date format
    with pytest.raises(ValueError):
        FlightSearchParams(**{**valid_params, "departure_date": "15/06/2025"})

    # Invalid return date (before departure)
    with pytest.raises(ValueError):
        FlightSearchParams(**{
            **valid_params,
            "return_date": "2025-06-10"  # Before departure
        })
```

### Integration Tests

```python
# tests/agents/test_flight_integration.py
import pytest
from unittest.mock import AsyncMock, patch
import asyncio

from src.agents.travel_agent_impl import TripSageTravelAgent

@pytest.fixture
async def setup_agent():
    """Set up a TripSageTravelAgent with mocked clients."""
    agent = TripSageTravelAgent()

    # Mock the flights client
    mock_flights = AsyncMock()
    mock_flights.search_flights.return_value = {
        "origin": "SFO",
        "destination": "JFK",
        "departure_date": "2025-06-15",
        "offers": [
            {
                "id": "offer_1",
                "total_amount": 299.99,
                "currency": "USD",
                "slices": [...]
            }
        ]
    }

    mock_flights.create_order.return_value = {
        "booking_id": "booking_1",
        "booking_reference": "ABC123",
        "status": "confirmed",
        "total_amount": 299.99,
        "currency": "USD",
        "slices": [...]
    }

    # Replace the real client with mock
    agent.flights_client = mock_flights

    # Also update the specialized modules to use the mock
    agent.flight_search.flights_client = mock_flights
    agent.flight_booking.flights_client = mock_flights

    return agent

@pytest.mark.asyncio
async def test_agent_enhanced_flight_search(setup_agent):
    """Test the enhanced flight search via the agent."""
    agent = await setup_agent

    # Test the enhanced flight search
    result = await agent.enhanced_flight_search({
        "origin": "SFO",
        "destination": "JFK",
        "departure_date": "2025-06-15",
        "adults": 1
    })

    # Assertions
    assert "offers" in result
    assert len(result["offers"]) > 0
    assert result["origin"] == "SFO"
    assert result["destination"] == "JFK"

    # Verify the flights client was called
    agent.flights_client.search_flights.assert_called_once()

@pytest.mark.asyncio
async def test_agent_book_flight(setup_agent):
    """Test the flight booking via the agent."""
    agent = await setup_agent

    # Test booking
    result = await agent.book_flight({
        "offer_id": "offer_1",
        "passengers": [
            {
                "given_name": "John",
                "family_name": "Doe",
                "gender": "m",
                "born_on": "1980-01-01"
            }
        ],
        "payment_details": {
            "type": "credit_card",
            "amount": 299.99,
            "currency": "USD"
        },
        "contact_details": {
            "email": "john.doe@example.com",
            "phone": "+1234567890"
        }
    })

    # Assertions
    assert result["success"] is True
    assert result["booking_id"] == "booking_1"
    assert result["confirmed"] is True

    # Verify the flights client was called
    agent.flights_client.create_order.assert_called_once()
```

## Deployment Requirements

### Resources

- **CPU**: 2-4 cores recommended
- **Memory**: 4-8GB RAM
- **Storage**: Minimal (primarily uses Supabase and Neo4j)
- **Network**: Internet connection for API access
- **Dependencies**: Redis for caching, Supabase for relational data, Neo4j for knowledge graph

### Environment Variables

```
# Duffel API credentials
DUFFEL_API_KEY=duffel_test_...

# Database connection
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Cache configuration
REDIS_URL=redis://localhost:6379/0

# Memory MCP (Neo4j) connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

## Monitoring

The TripSageTravelAgent includes metrics for monitoring flight search and booking activities:

```python
import prometheus_client
from prometheus_client import Counter, Histogram, Summary

# Flight search metrics
FLIGHT_SEARCH_REQUESTS = Counter(
    'tripsage_flight_search_requests_total',
    'Total number of flight search requests',
    ['origin', 'destination']
)

FLIGHT_SEARCH_DURATION = Histogram(
    'tripsage_flight_search_duration_seconds',
    'Flight search request duration in seconds',
    ['origin', 'destination'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

FLIGHT_BOOKING_REQUESTS = Counter(
    'tripsage_flight_booking_requests_total',
    'Total number of flight booking requests',
    ['status']
)

FLIGHT_SEARCH_RESULTS = Summary(
    'tripsage_flight_search_results',
    'Statistics on flight search results',
    ['origin', 'destination']
)

# Update metrics in search method
async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
    origin = params.get("origin", "unknown")
    destination = params.get("destination", "unknown")

    # Increment counter
    FLIGHT_SEARCH_REQUESTS.labels(origin=origin, destination=destination).inc()

    # Time the search
    with FLIGHT_SEARCH_DURATION.labels(origin=origin, destination=destination).time():
        result = await self._perform_search(params)

    # Record result count
    if "offers" in result:
        FLIGHT_SEARCH_RESULTS.labels(
            origin=origin, destination=destination
        ).observe(len(result["offers"]))

    return result
```

## Conclusion

The Flight Search and Booking implementation leverages the TripSageTravelAgent's capabilities and the Flights MCP Server to provide a comprehensive solution for finding and booking flights. Key features include:

1. **Enhanced Search**: Advanced filtering, price history, and recommendations
2. **Flexible Dates**: Search across date ranges to find best prices
3. **Booking Workflow**: Streamlined booking process with database integration
4. **Price Tracking**: Monitoring flight prices for better deals
5. **Caching Strategy**: Efficient caching for improved performance
6. **Dual Storage**: Integration with both Supabase and knowledge graph

This implementation follows TripSage's architectural principles including proper error handling, validation, logging, and testing, ensuring a robust and maintainable solution.
````

## File: implementation/mcp_abstraction_layer.md

````markdown
# TripSage MCP Abstraction Layer

This document describes the unified abstraction layer for interacting with various external MCP clients in TripSage. The abstraction layer provides a consistent interface, standardized error handling, and dependency injection support for all MCP interactions.

## Architecture Overview

The MCP abstraction layer consists of four main components:

1. **Manager (MCPManager)**: Central orchestrator for all MCP operations
2. **Registry (MCPClientRegistry)**: Maintains mapping of MCP names to wrapper classes
3. **Base Wrapper (BaseMCPWrapper)**: Abstract interface that all wrappers implement
4. **Specific Wrappers**: Concrete implementations for each MCP type

```plaintext
┌─────────────────────────────────────────┐
│           Agent/Tool/Service            │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│            MCP Manager                  │
│  - Configuration loading                │
│  - Client initialization                │
│  - Method invocation routing            │
│  - Error handling & logging             │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│          MCP Registry                   │
│  - Wrapper registration                 │
│  - Instance management                  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         MCP Wrappers                    │
│  ┌──────────────┐  ┌───────────────┐   │
│  │ Playwright   │  │ Google Maps   │   │
│  │   Wrapper    │  │   Wrapper     │   │
│  └──────────────┘  └───────────────┘   │
│  ┌──────────────┐  ┌───────────────┐   │
│  │   Weather    │  │   [Future]    │   │
│  │   Wrapper    │  │   Wrappers    │   │
│  └──────────────┘  └───────────────┘   │
└─────────────────────────────────────────┘
```

## Design Pattern

The abstraction layer implements a **Manager/Registry pattern** with **type-safe wrapper interfaces**:

- **Manager Pattern**: Centralizes lifecycle management and routing
- **Registry Pattern**: Enables dynamic registration of MCP wrappers
- **Wrapper Pattern**: Provides consistent interface across different MCPs
- **Singleton Pattern**: Ensures single instances of manager and registry

## Key Features

### 1. Consistent Interface

All MCP interactions go through the same interface:

```python
# Using the manager
result = await mcp_manager.invoke(
    mcp_name="weather",
    method_name="get_current_weather",
    params={"city": "New York"}
)

# Direct wrapper access
wrapper = await mcp_manager.initialize_mcp("weather")
result = await wrapper.invoke_method("get_current_weather", params={...})
```

### 2. Type Safety

The abstraction layer maintains type safety through:

- Pydantic models for configuration
- Generic type parameters in base classes
- Strong typing in method signatures

### 3. Configuration Management

MCP configurations are loaded from `mcp_settings.py`:

- Automatic configuration validation
- Environment variable support
- Sensible defaults

### 4. Error Handling

Standardized error handling across all MCPs:

- Custom exception hierarchy
- Error categorization
- Consistent error messages
- Proper error propagation

### 5. Dependency Injection

Easy integration with FastAPI and other frameworks:

```python
# FastAPI dependency
async def get_mcp_manager_dep() -> MCPManager:
    return get_mcp_manager()

@router.get("/weather/{city}")
async def get_weather(
    city: str,
    mcp_manager: MCPManager = Depends(get_mcp_manager_dep)
):
    result = await mcp_manager.invoke("weather", "get_current_weather", {"city": city})
    return result
```

## Implementation Guide

### Creating a New MCP Wrapper

1. Create a new wrapper class inheriting from `BaseMCPWrapper`:

   ```python
   from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper

   class NewMCPWrapper(BaseMCPWrapper[NewMCPClient]):
       def __init__(self, client=None, mcp_name="new_mcp"):
           if client is None:
               # Create client from configuration
               config = mcp_settings.new_mcp
               client = NewMCPClient(config)
           super().__init__(client, mcp_name)

       def _build_method_map(self) -> Dict[str, str]:
           return {
               "standard_method": "client_specific_method",
               # Map all methods
           }

       def get_available_methods(self) -> List[str]:
           return list(self._method_map.keys())
   ```

2. Register the wrapper in `registration.py`:

   ```python
   mcp_registry.register(
       mcp_name="new_mcp",
       wrapper_class=NewMCPWrapper,
       replace=True
   )
   ```

### Using the Abstraction Layer in Tools

```python
from agents import function_tool
from tripsage.mcp_abstraction import mcp_manager

@function_tool
async def my_tool(param: str) -> dict:
    """Tool using MCP abstraction layer."""
    result = await mcp_manager.invoke(
        mcp_name="my_mcp",
        method_name="my_method",
        params={"param": param}
    )
    return result
```

### Advanced Usage

```python
# Initialize all enabled MCPs
await mcp_manager.initialize_all_enabled()

# Check available MCPs
available = mcp_manager.get_available_mcps()

# Get specific wrapper for advanced operations
wrapper = await mcp_manager.initialize_mcp("weather")
methods = wrapper.get_available_methods()

# Direct client access (when needed)
client = wrapper.get_client()
```

## Benefits

1. **Consistency**: All MCPs accessed through same patterns
2. **Extensibility**: Easy to add new MCP integrations
3. **Maintainability**: Centralized configuration and error handling
4. **Testability**: Easy to mock and test MCP interactions
5. **Type Safety**: Full type checking throughout the system
6. **Flexibility**: Multiple levels of access (manager, wrapper, client)

## Migration Path

To migrate existing tools to use the abstraction layer:

1. Replace direct client instantiation with `mcp_manager.invoke()`
2. Update error handling to use abstraction layer exceptions
3. Remove client-specific configuration code
4. Update tests to mock the abstraction layer

## Future Enhancements

1. **Caching Layer**: Add caching at the abstraction level
2. **Metrics Collection**: Track MCP usage and performance
3. **Circuit Breakers**: Add resilience patterns
4. **Batch Operations**: Support batch method invocations
5. **Async Event System**: Publish events for MCP operations

## Example Integration

### Weather Tools Example

Original implementation:

```python
from tripsage.clients.weather import WeatherMCPClient

async def get_weather(city: str):
    client = WeatherMCPClient.get_client()
    return await client.get_current_weather(city)
```

Using abstraction layer:

```python
from tripsage.mcp_abstraction import mcp_manager

async def get_weather(city: str):
    return await mcp_manager.invoke(
        "weather",
        "get_current_weather",
        {"city": city}
    )
```

This abstraction layer provides a robust foundation for all MCP interactions in TripSage, ensuring consistency, maintainability, and extensibility.
````

## File: implementation/mcp_integration_strategy.md

````markdown
# TripSage MCP Integration Strategy

This document provides a comprehensive, actionable integration strategy for TripSage's Model Context Protocol (MCP) servers based on extensive research and evaluation. It serves as the definitive guide for TripSage's API framework, MCP server selection, web data extraction, caching, and browser automation strategies.

## 1. API Framework Strategy

**Recommendation:** Implement a dual-framework approach with **FastAPI** (main API) + **FastMCP** (MCP server components).

- **FastAPI:** Powers TripSage's core web API, handling user authentication, trip management, and client communication.
- **FastMCP:** Provides a standardized framework for building custom MCP servers when required, ensuring consistent implementation patterns.

**Rationale:** This approach leverages FastAPI's robust performance, type safety, and async capabilities for the main application while using FastMCP's specialized MCP development capabilities for custom MCP servers. Both frameworks share Python's typing system and Pydantic models, creating a cohesive development experience.

## 2. MCP Server Strategy for OpenAI Agent Integration

**Recommendation:** Adopt a **hybrid approach** that leverages existing external MCPs for standardized functionality while developing custom FastMCP servers only for core TripSage-specific logic.

**Key Principles:**

1. **External First:** Use existing, well-maintained external MCPs whenever possible.
2. **Custom When Necessary:** Build custom MCPs only when:
   - The functionality is central to TripSage's core business logic
   - Direct database integration is required
   - Privacy/security requirements can't be met with external MCPs
3. **Thin Wrapper Pattern:** Create lightweight wrapper clients around external MCPs that add TripSage-specific validation, error handling, and metrics.
4. **Domain-Based Routing:** Implement intelligent routing for web crawling operations based on domain-specific performance metrics.

**Justification:** This approach minimizes development and maintenance burden while maximizing the benefits of specialized MCP implementations. It allows TripSage to focus development resources on its core travel planning functionality while leveraging the ecosystem of existing MCP servers for common operations.

## 3. Definitive List of External MCP Servers

| MCP Server                       | Functionality                                                        | Integration Approach                                                                                          |
| -------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Supabase MCP**                 | Relational database operations for structured travel data            | Implement client in `tripsage/tools/supabase_tools.py` with wrapper functions for CRUD operations             |
| **Neo4j Memory MCP**             | Knowledge graph operations for travel relationships and entities     | Configure client in `tripsage/tools/memory_tools.py` with entity/relationship management functions            |
| **Duffel Flights MCP**           | Flight search and booking operations                                 | Create client in `tripsage/tools/flight_tools.py` with methods for search, pricing, and offer retrieval       |
| **Airbnb MCP**                   | Accommodation search and listing details                             | Implement client in `tripsage/tools/accommodation_tools.py` with search and detail functions                  |
| **Firecrawl MCP (MendableAI)**   | Web scraping for booking sites (Airbnb, Booking.com, etc.)           | Create client in `tripsage/tools/webcrawl/firecrawl_client.py` focusing on structured data extraction         |
| **Crawl4AI MCP**                 | Web scraping for informational sites (TripAdvisor, WikiTravel, etc.) | Implement client in `tripsage/tools/webcrawl/crawl4ai_client.py` optimized for rich text and RAG capabilities |
| **Playwright MCP**               | Browser automation for complex travel workflows                      | Create toolkit in `tripsage/tools/browser/tools.py` with session persistence and travel-specific operations   |
| **Google Maps MCP**              | Location-based services for trip planning                            | Implement client in `tripsage/tools/googlemaps_tools.py` with geocoding and place search functions            |
| **Time MCP**                     | Timezone and temporal operations                                     | Create client in `tripsage/tools/time_tools.py` for timezone conversion and current time retrieval            |
| **Weather MCP (szypetike)**      | Weather forecasting for trip planning                                | Implement client in `tripsage/tools/weather_tools.py` with forecast and current conditions functions          |
| **Google Calendar MCP (nspady)** | Calendar integration for trip scheduling                             | Create client in `tripsage/tools/calendar_tools.py` with event creation and scheduling tools                  |
| **Redis MCP**                    | Distributed caching for performance optimization                     | Implement client in `tripsage/tools/cache_tools.py` with TTL-based caching operations                         |

## 4. Web Data Extraction Strategy

**Recommendation:** Implement a **hybrid web crawling strategy** using domain-specific routing between Crawl4AI and Firecrawl MCPs, with Playwright MCP as a fallback for complex sites.

**Key Components:**

1. **Domain-Based Routing:**

   - Implement `source_selector.py` that routes requests to the optimal crawler based on domain type:
     - **Firecrawl MCP:** For booking sites, commerce platforms, and structured data (Airbnb, Booking.com, etc.)
     - **Crawl4AI MCP:** For informational, content-heavy sites (TripAdvisor, WikiTravel, destination guides)

2. **Result Normalization:**

   - Implement `result_normalizer.py` to transform crawler-specific outputs into a consistent schema
   - Ensure consistent data format regardless of the underlying crawler used

3. **Fallback Mechanism:**

   - Use Playwright MCP for sites that block traditional crawlers
   - Implement escalation logic to attempt Playwright when other crawlers fail
   - Focus on authenticated workflows and complex interactions

4. **Content Aggregator Wrapper:**
   - Build a thin wrapper in `webcrawl_tools.py` that provides a unified interface
   - Implement content enrichment for travel-specific data extraction
   - Utilize WebOperationsCache for performance optimization

**Benefits:** This approach maximizes extraction performance by using domain-specialized tools while presenting a consistent interface to agents. The fallback mechanism ensures reliability when faced with anti-scraping measures.

## 5. Caching Strategy

**Recommendation:** Implement the centralized `WebOperationsCache` system (Issue #38) with content-aware TTL management for all web operations.

**Key Components:**

1. **Content-Type-Based TTL Management:**

   - Implemented `ContentType` enum with five categories:
     - REALTIME (100s): Weather, stocks, flight availability
     - TIME_SENSITIVE (5m): News, social media, events
     - DAILY (1h): Flight prices, hotel availability
     - SEMI_STATIC (8h): Business info, operating hours
     - STATIC (24h): Historical data, destination information

2. **Tool-Specific Implementations:**

   - `CachedWebSearchTool`: Wrapper around OpenAI's WebSearchTool with transparent caching
   - `web_cached` decorator: Apply to other web operations functions
   - Redis-based distributed caching using `redis.asyncio`

3. **Performance Metrics Collection:**

   - Hit/miss tracking with time windows (1h, 24h, 7d)
   - Sampling to reduce Redis overhead
   - Cache size estimation and monitoring

4. **Integration Points:**
   - WebSearchTool usage in TravelPlanningAgent and DestinationResearchAgent
   - Webcrawl operations from Firecrawl and Crawl4AI
   - Browser automation results from Playwright MCP

**Benefits:** This strategy optimizes performance, reduces API costs, and improves response times while ensuring appropriate content freshness based on volatility.

## 6. Browser Automation Strategy

**Recommendation:** Use **Playwright MCP** as the primary browser automation solution, implemented as a fallback mechanism for scenarios where API and crawler approaches fail.

**Key Implementation Aspects:**

1. **Primary Use Cases:**

   - Authenticated workflows (booking verification, user account operations)
   - Sites with strong anti-scraping measures
   - Complex multi-step interactions (checkout processes, etc.)

2. **Implementation Approach:**

   - Configure Playwright MCP server with Python integration
   - Create browser toolkit in `tripsage/tools/browser/tools.py`
   - Implement session persistence for authenticated workflows
   - Add travel-specific browser operations (booking verification, check-ins)
   - Implement anti-detection measures for travel websites

3. **Integration with Web Crawling:**
   - Create clear escalation paths from crawler failures to browser automation
   - Implement result normalization to maintain consistent schema regardless of source
   - Add comprehensive caching for browser automation results

**Rationale:** Playwright MCP provides the most robust, maintained solution for browser automation with excellent Python support. By positioning it as a fallback rather than primary approach, we reduce overhead while ensuring reliability for complex scenarios.

## 7. Gaps & Custom Development Needs

**Recommendation:** Create three custom wrapper MCPs for TripSage-specific functionality that coordinates across multiple external MCPs.

1. **Unified Travel Search Wrapper:**

   - **Purpose:** Aggregate search results across multiple travel data sources
   - **Implementation:** Thin layer coordinating Duffel Flights MCP, Airbnb MCP, and web crawling tools
   - **Key Features:**
     - Unified search parameters and result schema
     - Parallel execution for performance
     - Result ranking and normalization

2. **Trip Planning Coordinator:**

   - **Purpose:** Orchestrate complex planning operations across multiple MCPs
   - **Implementation:** Wrapper that coordinates sequenced MCP operations for trip planning
   - **Key Features:**
     - Itinerary optimization algorithms
     - Constraint satisfaction logic (budget, time, preferences)
     - Coordinated execution of dependent operations

3. **Content Aggregator:**
   - **Purpose:** Provide unified access to travel content from diverse sources
   - **Implementation:** Wrapper around hybrid Crawl4AI/Firecrawl solution
   - **Key Features:**
     - Domain-based source selection
     - Content normalization
     - Comprehensive caching with WebOperationsCache
     - Intelligent fallback to Playwright MCP

**Development Guidelines:**

- Use FastMCP 2.0 for all custom MCP development
- Implement Pydantic v2 models for all schemas
- Use function tool pattern with decorator-based error handling
- Focus on thin coordination layers rather than reimplementing functionality

## 8. Operational Considerations

**Neo4j AuraDB API MCP (Issue #39):**

**Recommendation:** Maintain as **Post-MVP / Low Priority**. Do not implement the Neo4j AuraDB API MCP integration at this time.

**Rationale:**

- TripSage's architecture uses Neo4j as a persistent knowledge graph with stable connections
- Neo4j Memory MCP already provides all needed application-level interactions
- Administrative operations are better handled through Neo4j Aura's web interface
- Dynamic instance management would add unnecessary complexity and security concerns
- KISS/YAGNI principles suggest avoiding this integration until specific operational needs arise

**Implementation Prerequisites (if needed in future):**

- Production decision to use Neo4j AuraDB (not yet determined)
- Clear operational needs requiring programmatic instance management
- Security requirements and access control strategy for administrative operations

## 9. Considerations for Other Evaluated MCPs

| MCP Server                  | Evaluation Status               | Potential Niche Use                                          | Reason for Deferral/Exclusion                                    |
| --------------------------- | ------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------- |
| **Postgres MCP**            | Evaluated, not prioritized      | Direct database operations when Supabase MCP is insufficient | Supabase MCP provides better abstraction for TripSage's needs    |
| **SQLite MCP**              | Evaluated, not prioritized      | Local development and testing                                | Not needed for production; better alternatives exist             |
| **Stagehand MCP**           | Evaluated, not prioritized      | Potential supplement to Playwright for specific scenarios    | Overlapping functionality with Playwright; less mature ecosystem |
| **Browserbase MCP**         | Evaluated, not prioritized      | Alternative if Playwright adoption faces challenges          | Duplicates Playwright capabilities with fewer features           |
| **Exa MCP**                 | Suggested for future evaluation | Alternative web search beyond built-in WebSearchTool         | Initial research shows potential but needs deeper evaluation     |
| **LinkUp MCP**              | Suggested for future evaluation | Additional web search provider for destination research      | Initial research shows potential but needs deeper evaluation     |
| **Sequential Thinking MCP** | Suggested for future evaluation | Complex multi-step travel planning logic                     | May add value for complex reasoning tasks; needs evaluation      |

## 10. Alignment with Software Design Principles

The proposed MCP integration strategy strongly adheres to TripSage's core design principles:

1. **KISS (Keep It Simple, Stupid):**

   - Leverages existing MCPs instead of building custom solutions
   - Implements minimal wrapper code around external services
   - Uses direct interfaces rather than complex abstractions

2. **YAGNI (You Aren't Gonna Need It):**

   - Defers Neo4j AuraDB API MCP until a concrete need emerges
   - Focuses implementation on immediate travel planning needs
   - Avoids speculative features without clear use cases

3. **DRY (Don't Repeat Yourself):**

   - Standardizes client interfaces across different MCPs
   - Creates reusable abstractions for common patterns
   - Implements WebOperationsCache as a centralized caching solution

4. **SIMPLE:**

   - Prioritizes straightforward integration paths over complex architectures
   - Creates clear boundaries between components
   - Uses consistent patterns across different MCP integrations

5. **Pragmatic Development:**
   - Balances ideal architecture with practical implementation constraints
   - Focuses resources on core travel planning functionality
   - Creates flexible implementation plan with phased delivery

## 11. Impact on TODO.md and Documentation

The comprehensive MCP integration strategy has directly shaped TripSage's implementation plan as reflected in `TODO.md`:

1. **TODO.md Structured Tasks:**

   - Created detailed MCP integration tasks for each external server
   - Specified implementation phases for the hybrid web crawling strategy
   - Added comprehensive tasks for WebOperationsCache implementation
   - Prioritized tasks based on dependencies and impact

2. **New Documentation:**

   - `web_crawling_strategy.md`: Detailed implementation plan for hybrid crawler approach
   - `isolated_mcp_testing.md`: Guidelines for testing MCP clients without environmental dependencies
   - `webcrawl_search_caching.md`: Specification for WebOperationsCache implementation
   - `dual_storage_refactoring.md`: Guide for the Supabase + Neo4j dual storage pattern

3. **Updated Research Documentation:**

   - Completed evaluation of Issues #37, #38, and #39 in `RESEARCH_ISSUES.md`
   - Added specific MCP integration findings to relevant documentation
   - Updated `mcp_service_patterns.md` with standardized implementation guidance

4. **Implementation Timeline:**
   - Organized MCP integration into immediate, short-term, and medium-term phases
   - Prioritized core travel functionality MCPs (Flights, Accommodations, Maps)
   - Established clear dependencies between integration tasks

This strategy provides a comprehensive roadmap for TripSage's MCP integration, ensuring focused development effort on high-impact components while maintaining alignment with design principles.
````

## File: implementation/README.md

````markdown
# Implementation Documentation

This directory contains implementation plans, guidelines, and reference materials for the TripSage project.

## Contents

- `agents_sdk_implementation.md` - Agent implementation using OpenAI Agents SDK
- `flight_search_booking_implementation.md` - Flight search and booking implementation details
- `required_changes.md` - Required changes and updates to the system
- `travel_agent_implementation.md` - Travel agent implementation details
- `tripsage_implementation_plan.md` - Overall implementation plan for TripSage
- `tripsage_todo_list.md` - Implementation todo list and tracking
````

## File: implementation/required_changes.md

````markdown
# Required Code Changes for TripSage Implementation

This document outlines the necessary code changes required to implement the complete TripSage system based on the documented architecture and specifications.

## Core Architecture Changes

### 1. MCP Server Integration

The existing implementation is built around OpenAI's Assistants API, but our architecture requires a shift to MCP servers. The following changes are needed:

#### BaseAgent Class Refactoring

Current location: `/src/agents/base_agent.py`

The current `BaseAgent` implementation needs to be refactored to:

1. Replace direct OpenAI Assistant API dependency with MCP server integrations
2. Implement the dual storage architecture (Supabase + Knowledge Graph)
3. Add support for sequential thinking and planning capabilities

```python
# New imports required
from memory import MemoryClient  # Knowledge Graph client
from sequential_thinking import SequentialThinking
from time_management import TimeManager
from supabase import create_client

class BaseAgent:
    """Base class for all TripSage agents with MCP server integration"""

    def __init__(
        self,
        name: str,
        instructions: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ):
        # Initialize existing properties
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.model = model or config.model_name
        self.metadata = metadata or {"agent_type": "tripsage"}

        # Initialize MCP clients
        self.memory_client = MemoryClient(config.memory_endpoint)
        self.sequential_thinking = SequentialThinking()
        self.time_manager = TimeManager()

        # Initialize dual storage
        self.supabase = create_client(config.supabase_url, config.supabase_key)

        # Track conversation state
        self.messages_history = []
```

#### Tool Interface Standardization

Create a new module to standardize tool interfaces across MCP servers:

```python
# New file: /src/agents/tool_interface.py
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

@runtime_checkable
class MCPTool(Protocol):
    """Protocol defining the standard interface for all MCP tools"""

    name: str
    description: str

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the given parameters"""
        ...
```

### 2. New MCP Server Implementation

Create dedicated modules for each MCP server:

#### Google Maps MCP Server

```python
# New file: /src/mcp/google_maps_mcp.py
from tool_interface import MCPTool
import httpx
from typing import Any, Dict, List

class GoogleMapsGeocoding(MCPTool):
    name = "google_maps_geocoding"
    description = "Convert addresses to geographic coordinates"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...

class GoogleMapsPlaces(MCPTool):
    name = "google_maps_places"
    description = "Search for places and points of interest"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...

class GoogleMapsDirections(MCPTool):
    name = "google_maps_directions"
    description = "Get directions between locations"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...
```

#### Airbnb MCP Server

```python
# New file: /src/mcp/airbnb_mcp.py
from tool_interface import MCPTool
import httpx
from playwright.async_api import async_playwright
from typing import Any, Dict, List

class AirbnbSearch(MCPTool):
    name = "airbnb_search"
    description = "Search for accommodations on Airbnb"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation using Playwright for HTML parsing
        ...

class AirbnbGetListing(MCPTool):
    name = "airbnb_get_listing"
    description = "Get detailed information about an Airbnb listing"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...
```

#### Time MCP Server

```python
# New file: /src/mcp/time_mcp.py
from tool_interface import MCPTool
from typing import Any, Dict, List
from datetime import datetime
import pendulum

class TimeConversion(MCPTool):
    name = "time_conversion"
    description = "Convert times between time zones"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation using pendulum for timezone handling
        ...

class TimeCalculation(MCPTool):
    name = "time_calculation"
    description = "Calculate time differences, durations, etc."

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...
```

### 3. Knowledge Graph Implementation

```python
# New file: /src/memory/knowledge_graph.py
from typing import Any, Dict, List, Optional
import httpx
from config import config

class MemoryClient:
    """Client for interacting with the Knowledge Graph MCP Server"""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.api_key = config.memory_api_key

    async def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create new entities in the knowledge graph"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/entities",
                json={"entities": entities},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()

    async def create_relations(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create relations between entities in the knowledge graph"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/relations",
                json={"relations": relations},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()

    async def search_nodes(self, query: str) -> Dict[str, Any]:
        """Search for nodes in the knowledge graph"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.endpoint}/search",
                params={"query": query},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()
```

### 4. Sequential Thinking Implementation

```python
# New file: /src/agents/sequential_thinking.py
from typing import Any, Dict, List, Optional
import httpx
from config import config

class SequentialThinking:
    """Integration with Sequential Thinking MCP Server for complex planning"""

    def __init__(self):
        self.endpoint = config.sequential_thinking_endpoint
        self.api_key = config.sequential_thinking_api_key

    async def plan(self, problem: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan a solution to a complex problem using sequential thinking"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/plan",
                json={
                    "problem": problem,
                    "context": context,
                    "total_thoughts": 10,  # Default, can be adjusted
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()
```

## API Layer Changes

### 1. New API Routes

Add new routes to the FastAPI application to support the MCP server architecture:

```python
# New file: /src/api/routes/knowledge.py
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_active_user
from memory.knowledge_graph import MemoryClient
from typing import Any, Dict, List

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    dependencies=[Depends(get_current_active_user)],
)

@router.get("/search")
async def search_knowledge(query: str):
    """Search the knowledge graph"""
    memory_client = MemoryClient(config.memory_endpoint)
    results = await memory_client.search_nodes(query)
    return results

@router.post("/entities")
async def create_entities(entities: List[Dict[str, Any]]):
    """Create new entities in the knowledge graph"""
    memory_client = MemoryClient(config.memory_endpoint)
    result = await memory_client.create_entities(entities)
    return result
```

### 2. Update main.py

Update the main FastAPI application to include the new routers:

```python
# Updated file: /src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, flights, trips, users, knowledge, maps, accommodations, time_management

# Update FastAPI app
app = FastAPI(
    title="TripSage API",
    description="API for TripSage travel planning system with MCP server integration",
    version="0.2.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(flights.router)
app.include_router(knowledge.router)
app.include_router(maps.router)
app.include_router(accommodations.router)
app.include_router(time_management.router)
```

## Database Schema Updates

### 1. New Tables for Dual Storage

Add new tables to the Supabase schema to support the dual storage architecture:

```sql
-- New migration file: /migrations/20250509_01_knowledge_integration.sql

-- Table for tracking knowledge graph entities
CREATE TABLE IF NOT EXISTS kg_entities (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    name TEXT NOT NULL,
    properties JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT kg_entities_entity_id_unique UNIQUE (entity_id)
);

COMMENT ON TABLE kg_entities IS 'Knowledge graph entities referenced in the relational database';

-- Table for caching
CREATE TABLE IF NOT EXISTS cache_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cache_key TEXT NOT NULL,
    cache_value JSONB NOT NULL,
    source TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT cache_items_key_source_unique UNIQUE (cache_key, source)
);

COMMENT ON TABLE cache_items IS 'Cache for API results and computed data';

-- Add search history table
CREATE TABLE IF NOT EXISTS search_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    search_type TEXT NOT NULL,
    search_params JSONB NOT NULL,
    results_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT search_history_type_check CHECK (search_type IN ('flight', 'accommodation', 'activity', 'destination'))
);

COMMENT ON TABLE search_history IS 'History of user searches for analytics and recommendations';
```

### 2. Add TypeScript Types

Add TypeScript types to match the updated database schema:

```typescript
// Updated file: /src/types/supabase.ts
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: number;
          name: string | null;
          email: string;
          preferences_json: Json | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: number;
          name?: string | null;
          email: string;
          preferences_json?: Json | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: number;
          name?: string | null;
          email?: string;
          preferences_json?: Json | null;
          created_at?: string;
          updated_at?: string;
        };
        Relationships: [];
      };
      trips: {
        Row: {
          id: number;
          name: string;
          start_date: string;
          end_date: string;
          destination: string;
          budget: number;
          travelers: number;
          status: string;
          trip_type: string;
          flexibility: Json | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: number;
          name: string;
          start_date: string;
          end_date: string;
          destination: string;
          budget: number;
          travelers: number;
          status: string;
          trip_type: string;
          flexibility?: Json | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: number;
          name?: string;
          start_date?: string;
          end_date?: string;
          destination?: string;
          budget?: number;
          travelers?: number;
          status?: string;
          trip_type?: string;
          flexibility?: Json | null;
          created_at?: string;
          updated_at?: string;
        };
        Relationships: [];
      };
      kg_entities: {
        Row: {
          id: number;
          entity_id: string;
          entity_type: string;
          name: string;
          properties: Json | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: number;
          entity_id: string;
          entity_type: string;
          name: string;
          properties?: Json | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: number;
          entity_id?: string;
          entity_type?: string;
          name?: string;
          properties?: Json | null;
          created_at?: string;
          updated_at?: string;
        };
        Relationships: [];
      };
      // Additional tables omitted for brevity
    };
    // Views, functions, etc. omitted for brevity
  };
}
```

## TravelAgent Class Updates

Update the TravelAgent class to use the new MCP server architecture:

```python
# Updated file: /src/agents/travel_agent.py
from typing import Any, Dict, List, Optional
from base_agent import BaseAgent
from config import config
from memory.knowledge_graph import MemoryClient
from mcp.google_maps_mcp import GoogleMapsGeocoding, GoogleMapsPlaces
from mcp.airbnb_mcp import AirbnbSearch
from mcp.time_mcp import TimeConversion
from supabase import create_client

class TravelAgent(BaseAgent):
    """
    Primary travel planning agent that coordinates the planning process
    using the MCP server architecture.
    """

    def __init__(self):
        instructions = """
        You are a travel planning assistant for TripSage. Your role is to help users plan their travels...
        """

        # Initialize base agent
        super().__init__(
            name="TripSage Travel Planner",
            instructions=instructions,
            metadata={"agent_type": "travel_planner", "version": "2.0.0"},
        )

        # Initialize MCP tools
        self.mcp_tools = {
            "google_maps_geocoding": GoogleMapsGeocoding(),
            "google_maps_places": GoogleMapsPlaces(),
            "airbnb_search": AirbnbSearch(),
            "time_conversion": TimeConversion(),
            # Additional tools
        }

    async def process_message(self, message: str, user_id: str) -> str:
        """Process a user message and return a response"""
        # Add message to history
        self.add_message(message)

        # Create context from knowledge graph
        context = await self._build_context(user_id)

        # Use sequential thinking for complex queries
        if self._is_complex_query(message):
            plan = await self.sequential_thinking.plan(message, context)
            # Execute the plan
            response = await self._execute_plan(plan)
        else:
            # Simple query handling
            response = await self._handle_simple_query(message, context)

        # Update knowledge graph with new information
        await self._update_knowledge(user_id, message, response)

        return response

    async def _build_context(self, user_id: str) -> Dict[str, Any]:
        """Build context from knowledge graph and Supabase"""
        # Get user data from Supabase
        user_data = await self._get_user_data(user_id)

        # Get relevant knowledge from memory
        memory_client = MemoryClient(config.memory_endpoint)
        knowledge = await memory_client.search_nodes(f"user:{user_id}")

        return {
            "user_data": user_data,
            "knowledge": knowledge,
            "travel_preferences": user_data.get("preferences_json", {})
        }

    async def _handle_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call using the appropriate MCP server"""
        if tool_name in self.mcp_tools:
            return await self.mcp_tools[tool_name].execute(args)

        # Fall back to standard tools for backward compatibility
        if tool_name == "search_flights":
            return await self._search_flights(args)
        elif tool_name == "search_accommodations":
            return await self._search_accommodations(args)
        elif tool_name == "search_activities":
            return await self._search_activities(args)
        elif tool_name == "create_trip":
            return await self._create_trip(args)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
```

## Configuration Updates

Update the configuration to include the new MCP server endpoints:

```python
# Updated file: /src/agents/config.py
import os
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Application settings"""

    # OpenAI settings (legacy)
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    model_name: str = "gpt-4"

    # Supabase settings
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_ANON_KEY")

    # MCP server endpoints
    memory_endpoint: str = Field(..., env="MEMORY_MCP_ENDPOINT")
    memory_api_key: str = Field(..., env="MEMORY_MCP_API_KEY")

    google_maps_endpoint: str = Field(..., env="GOOGLE_MAPS_MCP_ENDPOINT")
    google_maps_api_key: str = Field(..., env="GOOGLE_MAPS_MCP_API_KEY")

    airbnb_endpoint: str = Field(..., env="AIRBNB_MCP_ENDPOINT")
    airbnb_api_key: str = Field(..., env="AIRBNB_MCP_API_KEY")

    time_endpoint: str = Field(..., env="TIME_MCP_ENDPOINT")
    time_api_key: str = Field(..., env="TIME_MCP_API_KEY")

    sequential_thinking_endpoint: str = Field(..., env="SEQ_THINKING_MCP_ENDPOINT")
    sequential_thinking_api_key: str = Field(..., env="SEQ_THINKING_MCP_API_KEY")

    # Redis cache configuration
    redis_url: str = Field(..., env="REDIS_URL")
    cache_ttl_short: int = 300  # 5 minutes
    cache_ttl_medium: int = 3600  # 1 hour
    cache_ttl_long: int = 86400  # 24 hours

    class Config:
        env_file = ".env"

# Create config instance
config = Settings()
```

## Frontend Integration

Create a new API client in the frontend to interact with the updated backend:

```typescript
// New file: src/frontend/api/tripSageApi.ts
import { createClient } from "@supabase/supabase-js";
import type { Database } from "../../types/supabase";

export class TripSageApiClient {
  private supabase;
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string, supabaseUrl: string, supabaseKey: string) {
    this.baseUrl = baseUrl;
    this.supabase = createClient<Database>(supabaseUrl, supabaseKey);
  }

  async login(email: string, password: string) {
    const { data, error } = await this.supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;

    this.token = data.session?.access_token || null;
    return data.user;
  }

  async createTrip(tripData: any) {
    const response = await fetch(`${this.baseUrl}/trips`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.token}`,
      },
      body: JSON.stringify(tripData),
    });

    if (!response.ok) {
      throw new Error(`Failed to create trip: ${response.statusText}`);
    }

    return await response.json();
  }

  // Additional methods for interacting with the API
  // ...

  async searchKnowledge(query: string) {
    const response = await fetch(
      `${this.baseUrl}/knowledge/search?query=${encodeURIComponent(query)}`,
      {
        headers: {
          Authorization: `Bearer ${this.token}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Knowledge search failed: ${response.statusText}`);
    }

    return await response.json();
  }
}
```

## Caching Implementation

Create a Redis-based caching system:

```python
# New file: /src/cache/redis_cache.py
import json
from typing import Any, Dict, Optional, Union
import redis.asyncio as redis
from config import config

class RedisCache:
    """Redis-based caching system for TripSage"""

    def __init__(self):
        self.redis = redis.from_url(config.redis_url)

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a value from the cache"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> bool:
        """Set a value in the cache with a TTL"""
        return await self.redis.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache"""
        return await self.redis.delete(key) > 0

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching the pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0
```

## Environment Setup

Create a comprehensive environment file template:

```bash
# New file: .env.example

# OpenAI API (Legacy)
OPENAI_API_KEY=your-openai-api-key

# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key

# Memory MCP Server
MEMORY_MCP_ENDPOINT=https://memory-mcp.example.com
MEMORY_MCP_API_KEY=your-memory-mcp-api-key

# Google Maps MCP Server
GOOGLE_MAPS_MCP_ENDPOINT=https://google-maps-mcp.example.com
GOOGLE_MAPS_MCP_API_KEY=your-google-maps-mcp-api-key

# Airbnb MCP Server
AIRBNB_MCP_ENDPOINT=https://airbnb-mcp.example.com
AIRBNB_MCP_API_KEY=your-airbnb-mcp-api-key

# Time MCP Server
TIME_MCP_ENDPOINT=https://time-mcp.example.com
TIME_MCP_API_KEY=your-time-mcp-api-key

# Sequential Thinking MCP Server
SEQ_THINKING_MCP_ENDPOINT=https://seq-thinking-mcp.example.com
SEQ_THINKING_MCP_API_KEY=your-seq-thinking-mcp-api-key

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# Server Configuration
PORT=8000
NODE_ENV=development
```

## Project Structure Updates

Updated project structure to support the new architecture:

```plaintext
src/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py         # Updated for MCP integration
│   ├── config.py             # Updated with new configuration
│   ├── sequential_thinking.py # New file
│   ├── tool_interface.py     # New file
│   └── travel_agent.py       # Updated to use MCP servers
├── api/
│   ├── __init__.py
│   ├── auth.py
│   ├── database.py
│   ├── main.py               # Updated with new routers
│   └── routes/
│       ├── __init__.py
│       ├── auth.py
│       ├── flights.py
│       ├── knowledge.py      # New file
│       ├── maps.py           # New file
│       ├── accommodations.py # New file
│       ├── time_management.py # New file
│       ├── trips.py
│       └── users.py
├── cache/
│   ├── __init__.py
│   └── redis_cache.py        # New file
├── memory/
│   ├── __init__.py
│   └── knowledge_graph.py    # New file
├── mcp/
│   ├── __init__.py
│   ├── airbnb_mcp.py         # New file
│   ├── google_maps_mcp.py    # New file
│   └── time_mcp.py           # New file
└── types/
    └── supabase.ts           # Updated with new tables
```

## Implementation Timeline

1. **Phase 1: Core Architecture (Week 1-2)**

   - Refactor BaseAgent class
   - Implement tool interface standardization
   - Set up knowledge graph integration
   - Update config system

2. **Phase 2: MCP Server Implementation (Week 3-4)**

   - Implement Google Maps MCP server
   - Implement Airbnb MCP server
   - Implement Time MCP server
   - Implement Sequential Thinking integration

3. **Phase 3: API Layer Updates (Week 5)**

   - Create new API routes
   - Update existing routes for MCP integration
   - Implement caching system

4. **Phase 4: Database Updates (Week 6)**

   - Create new database migrations
   - Update TypeScript types
   - Implement dual storage architecture

5. **Phase 5: Frontend Integration (Week 7-8)**

   - Create frontend API client
   - Update UI components for new capabilities
   - Implement real-time updates

6. **Phase 6: Testing and Optimization (Week 9-10)**
   - Comprehensive testing
   - Performance optimization
   - Documentation updates
````

## File: implementation/travel_agent_implementation.md

````markdown
# Travel Agent Implementation Guide

This document provides a comprehensive implementation guide for the Travel Planning Agent (TRAVELAGENT-001) in the TripSage system.

## Overview

The Travel Planning Agent serves as the primary orchestrator for the TripSage platform, integrating various MCP tools, dual storage architecture, and specialized search capabilities to provide a comprehensive travel planning experience. It acts as the main interface between users and the underlying travel services, handling queries ranging from flight and accommodation searches to weather forecasts and itinerary planning.

## Architecture

The Travel Planning Agent follows the OpenAI Agents SDK pattern, with specific enhancements for travel planning:

1. **Base Framework**: Built on the `TravelAgent` class that extends `BaseAgent`
2. **MCP Integration**: Seamless access to all TripSage MCP servers
3. **Tool Registration**: Automatic registration of domain-specific tools
4. **Dual Storage**: Integration with both Supabase and Knowledge Graph
5. **Hybrid Search Strategy**: Combination of WebSearchTool and specialized crawling

### Class Hierarchy

```plaintext
BaseAgent
└── TravelAgent
    └── TripSageTravelAgent (Implementation)
```

## Implementation Details

### Core Components

```python
# src/agents/travel_agent_impl.py
"""
Implementation of the Travel Planning Agent for TripSage.

This module provides the concrete implementation of the TravelAgent class,
integrating all MCP clients and specialized tools for comprehensive travel planning.
"""

import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from agents import WebSearchTool, function_tool
from agents.extensions.allowed_domains import AllowedDomains
from src.cache.redis_cache import redis_cache
from src.utils.config import get_config
from src.utils.error_handling import MCPError, TripSageError
from src.utils.logging import get_module_logger

from .base_agent import TravelAgent
from src.mcp.flights import get_client as get_flights_client
from src.mcp.weather import get_client as get_weather_client
from src.mcp.accommodations import get_client as get_accommodations_client
from src.mcp.googlemaps import get_client as get_maps_client
from src.mcp.time import get_client as get_time_client
from src.mcp.webcrawl import get_client as get_webcrawl_client
from src.mcp.memory import get_client as get_memory_client

logger = get_module_logger(__name__)
config = get_config()


class TripCreationParams(BaseModel):
    """Parameters for creating a new trip."""

    user_id: str = Field(..., description="User ID for trip association")
    title: str = Field(..., description="Trip title")
    description: Optional[str] = Field(None, description="Trip description")
    destination: str = Field(..., description="Primary destination")
    start_date: str = Field(..., description="Trip start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Trip end date (YYYY-MM-DD)")
    budget: float = Field(..., gt=0, description="Total trip budget in USD")

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: str, values: Dict[str, Any]) -> str:
        """Validate that end_date is after start_date."""
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class TripSageTravelAgent(TravelAgent):
    """Comprehensive travel planning agent for TripSage with all integrated tools."""

    def __init__(
        self,
        name: str = "TripSage Travel Planner",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the TripSage travel agent with all required tools and integrations.

        Args:
            name: Agent name
            model: Model name to use
            temperature: Temperature for model sampling
        """
        super().__init__(name=name, model=model, temperature=temperature)

        # Initialize MCP clients
        self.flights_client = get_flights_client()
        self.weather_client = get_weather_client()
        self.accommodations_client = get_accommodations_client()
        self.maps_client = get_maps_client()
        self.time_client = get_time_client()
        self.webcrawl_client = get_webcrawl_client()
        self.memory_client = get_memory_client()

        # Register all MCP tools
        self._register_all_mcp_tools()

        # Initialize knowledge graph
        self._initialize_knowledge_graph()

        logger.info("TripSage Travel Agent fully initialized with all MCP tools")

    def _register_all_mcp_tools(self) -> None:
        """Register all MCP tools with the agent."""
        # Register all MCP client tools
        self._register_mcp_client_tools(self.flights_client, prefix="flights_")
        self._register_mcp_client_tools(self.weather_client, prefix="weather_")
        self._register_mcp_client_tools(self.accommodations_client, prefix="accommodations_")
        self._register_mcp_client_tools(self.maps_client, prefix="maps_")
        self._register_mcp_client_tools(self.time_client, prefix="time_")
        self._register_mcp_client_tools(self.webcrawl_client, prefix="webcrawl_")
        self._register_mcp_client_tools(self.memory_client, prefix="memory_")

        # Register direct travel tools
        self._register_travel_tools()

        logger.info("Registered all MCP tools with the TripSage Travel Agent")

    def _register_mcp_client_tools(
        self, mcp_client: Any, prefix: str = ""
    ) -> None:
        """Register tools from an MCP client with appropriate prefixing.

        Args:
            mcp_client: MCP client to register tools from
            prefix: Prefix to add to tool names
        """
        # Get all methods decorated with function_tool
        for attr_name in dir(mcp_client):
            if attr_name.startswith("_"):
                continue

            attr = getattr(mcp_client, attr_name)
            if hasattr(attr, "_function_tool"):
                # Register the tool with the agent
                self._register_tool(attr)
                logger.debug("Registered MCP tool: %s%s", prefix, attr_name)

    def _register_travel_tools(self) -> None:
        """Register travel-specific tools directly implemented in this class."""
        # Trip management tools
        self._register_tool(self.create_trip)
        self._register_tool(self.update_trip)
        self._register_tool(self.get_trip_details)

        # Planning tools
        self._register_tool(self.search_destination_info)
        self._register_tool(self.compare_travel_options)
        self._register_tool(self.optimize_itinerary)
        self._register_tool(self.calculate_budget_breakdown)

        # Knowledge graph tools
        self._register_tool(self.get_travel_recommendations)
        self._register_tool(self.store_travel_knowledge)

        logger.info("Registered travel-specific tools")

    def _initialize_knowledge_graph(self) -> None:
        """Initialize the knowledge graph connection and load initial context."""
        try:
            # This will be implemented when Memory MCP is available
            logger.info("Knowledge graph initialization will be implemented with Memory MCP")
        except Exception as e:
            logger.warning("Failed to initialize knowledge graph: %s", str(e))

    async def run_with_history(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the agent and update the knowledge graph.

        Args:
            user_input: User input text
            context: Optional context data

        Returns:
            Dictionary with the agent's response and other information
        """
        # Run the agent
        result = await self.run(user_input, context)

        # Process the interaction for knowledge graph updates (when implemented)
        try:
            # Update knowledge graph with new insights from this interaction
            await self._update_knowledge_graph(user_input, result)
        except Exception as e:
            logger.error("Failed to update knowledge graph: %s", str(e))

        return result

    async def _update_knowledge_graph(self, user_input: str, response: Dict[str, Any]) -> None:
        """Update the knowledge graph with insights from the conversation.

        Args:
            user_input: User input text
            response: Agent response dictionary
        """
        # This will be implemented when Memory MCP is available
        pass

    @function_tool
    async def create_trip(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new trip in the TripSage system.

        Args:
            params: Trip parameters including user_id, title,
                destination, dates, and budget

        Returns:
            Created trip information
        """
        try:
            # Validate parameters
            trip_params = TripCreationParams(**params)

            # Connect to Supabase database
            from src.db.client import get_client
            db_client = get_client()

            # Create the trip record
            trip_id = await db_client.create_trip(
                user_id=trip_params.user_id,
                title=trip_params.title,
                description=trip_params.description,
                destination=trip_params.destination,
                start_date=trip_params.start_date,
                end_date=trip_params.end_date,
                budget=trip_params.budget,
            )

            # Add to knowledge graph when available
            if hasattr(self, "memory_client") and self.memory_client:
                try:
                    await self.memory_client.create_entities([{
                        "name": f"Trip:{trip_id}",
                        "entityType": "Trip",
                        "observations": [
                            f"Destination: {trip_params.destination}",
                            f"Dates: {trip_params.start_date} to {trip_params.end_date}",
                            f"Budget: ${trip_params.budget}",
                            trip_params.description or "No description provided"
                        ]
                    }])

                    await self.memory_client.create_relations([{
                        "from": f"User:{trip_params.user_id}",
                        "relationType": "plans",
                        "to": f"Trip:{trip_id}"
                    }])

                    await self.memory_client.create_relations([{
                        "from": f"Trip:{trip_id}",
                        "relationType": "has_destination",
                        "to": trip_params.destination
                    }])
                except Exception as e:
                    logger.warning("Failed to update knowledge graph: %s", str(e))

            return {
                "success": True,
                "trip_id": trip_id,
                "message": "Trip created successfully",
                "trip_details": {
                    "user_id": trip_params.user_id,
                    "title": trip_params.title,
                    "description": trip_params.description,
                    "destination": trip_params.destination,
                    "start_date": trip_params.start_date,
                    "end_date": trip_params.end_date,
                    "budget": trip_params.budget,
                }
            }

        except Exception as e:
            logger.error("Error creating trip: %s", str(e))
            return {"success": False, "error": f"Trip creation error: {str(e)}"}

    @function_tool
    async def update_trip(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing trip in the TripSage system.

        Args:
            params: Trip update parameters including trip_id and fields to update

        Returns:
            Updated trip information
        """
        try:
            # Extract trip ID
            trip_id = params.get("trip_id")
            if not trip_id:
                return {"success": False, "error": "Trip ID is required"}

            # Connect to Supabase database
            from src.db.client import get_client
            db_client = get_client()

            # Get current trip data
            current_trip = await db_client.get_trip(trip_id)
            if not current_trip:
                return {"success": False, "error": f"Trip with ID {trip_id} not found"}

            # Update fields
            update_fields = {}
            for field in ["title", "description", "destination", "start_date", "end_date", "budget", "status"]:
                if field in params and params[field] is not None:
                    update_fields[field] = params[field]

            # Update the trip
            await db_client.update_trip(trip_id, update_fields)

            # Get updated trip
            updated_trip = await db_client.get_trip(trip_id)

            # Update knowledge graph when available
            if hasattr(self, "memory_client") and self.memory_client:
                try:
                    new_observations = []
                    if "destination" in update_fields:
                        new_observations.append(f"Destination: {update_fields['destination']}")
                    if "start_date" in update_fields or "end_date" in update_fields:
                        start_date = update_fields.get("start_date", current_trip["start_date"])
                        end_date = update_fields.get("end_date", current_trip["end_date"])
                        new_observations.append(f"Dates: {start_date} to {end_date}")
                    if "budget" in update_fields:
                        new_observations.append(f"Budget: ${update_fields['budget']}")
                    if "description" in update_fields:
                        new_observations.append(update_fields["description"])

                    if new_observations:
                        await self.memory_client.add_observations([{
                            "entityName": f"Trip:{trip_id}",
                            "contents": new_observations
                        }])
                except Exception as e:
                    logger.warning("Failed to update knowledge graph: %s", str(e))

            return {
                "success": True,
                "trip_id": trip_id,
                "message": "Trip updated successfully",
                "trip_details": updated_trip
            }

        except Exception as e:
            logger.error("Error updating trip: %s", str(e))
            return {"success": False, "error": f"Trip update error: {str(e)}"}

    @function_tool
    async def get_trip_details(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get details of a trip from the TripSage system.

        Args:
            params: Parameters including trip_id

        Returns:
            Trip details including flights, accommodations, and activities
        """
        try:
            # Extract trip ID
            trip_id = params.get("trip_id")
            if not trip_id:
                return {"success": False, "error": "Trip ID is required"}

            # Connect to Supabase database
            from src.db.client import get_client
            db_client = get_client()

            # Get trip data
            trip = await db_client.get_trip(trip_id)
            if not trip:
                return {"success": False, "error": f"Trip with ID {trip_id} not found"}

            # Get related data
            flights = await db_client.get_trip_flights(trip_id)
            accommodations = await db_client.get_trip_accommodations(trip_id)
            activities = await db_client.get_trip_activities(trip_id)

            # Get knowledge graph data when available
            kg_data = {}
            if hasattr(self, "memory_client") and self.memory_client:
                try:
                    kg_trip = await self.memory_client.open_nodes([f"Trip:{trip_id}"])
                    if kg_trip:
                        kg_data = kg_trip[0]
                except Exception as e:
                    logger.warning("Failed to get knowledge graph data: %s", str(e))

            return {
                "success": True,
                "trip_id": trip_id,
                "trip_details": trip,
                "flights": flights,
                "accommodations": accommodations,
                "activities": activities,
                "knowledge_graph": kg_data
            }

        except Exception as e:
            logger.error("Error getting trip details: %s", str(e))
            return {"success": False, "error": f"Error retrieving trip details: {str(e)}"}

    @function_tool
    async def search_destination_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for comprehensive information about a travel destination.

        Uses both the WebSearchTool and specialized travel resources to gather and
        analyze detailed information about a destination.

        Args:
            params: Parameters including destination name and info types to search for
                destination: Name of the destination (city, country, attraction)
                info_types: List of info types (e.g., "attractions", "safety",
                    "transportation", "best_time")

        Returns:
            Dictionary containing structured information about the destination
        """
        try:
            # Extract parameters
            destination = params.get("destination")
            info_types = params.get("info_types", ["general"])

            if not destination:
                return {"error": "Destination parameter is required"}

            # Build queries for each info type
            search_results = {}

            for info_type in info_types:
                query = self._build_destination_query(destination, info_type)

                # Check cache first
                cache_key = f"destination:{destination}:info_type:{info_type}"
                cached_result = await redis_cache.get(cache_key)

                if cached_result:
                    search_results[info_type] = cached_result
                    search_results[info_type]["cache"] = "hit"
                    continue

                # Use WebCrawl MCP for specialized extraction if available
                if hasattr(self, "webcrawl_client") and self.webcrawl_client:
                    try:
                        # Use WebCrawl's specialized destination search
                        crawl_result = await self.webcrawl_client.search_destination_info(
                            destination=destination,
                            info_type=info_type
                        )

                        if crawl_result and not crawl_result.get("error"):
                            # Cache the result
                            await redis_cache.set(
                                cache_key,
                                crawl_result,
                                ttl=3600  # Cache for 1 hour
                            )

                            crawl_result["cache"] = "miss"
                            search_results[info_type] = crawl_result
                            continue
                    except Exception as e:
                        logger.warning(
                            "WebCrawl extraction failed for %s/%s: %s",
                            destination, info_type, str(e)
                        )

                # Fallback: Let the agent use WebSearchTool directly
                search_results[info_type] = {
                    "query": query,
                    "cache": "miss",
                    "source": "web_search",
                    "note": (
                        "Data will be provided by WebSearchTool and "
                        "processed by the agent"
                    ),
                }

            # Update knowledge graph when available
            if hasattr(self, "memory_client") and self.memory_client:
                try:
                    # Check if destination entity exists
                    destination_nodes = await self.memory_client.search_nodes(destination)
                    destination_exists = any(
                        node["name"] == destination and node["type"] == "Destination"
                        for node in destination_nodes
                    )

                    # Create destination entity if it doesn't exist
                    if not destination_exists:
                        await self.memory_client.create_entities([{
                            "name": destination,
                            "entityType": "Destination",
                            "observations": [
                                f"Destination name: {destination}",
                                "Created from search_destination_info"
                            ]
                        }])
                except Exception as e:
                    logger.warning("Failed to update knowledge graph: %s", str(e))

            return {
                "destination": destination,
                "info_types": info_types,
                "search_results": search_results,
            }

        except Exception as e:
            logger.error("Error searching destination info: %s", str(e))
            return {"error": f"Destination search error: {str(e)}"}

    def _build_destination_query(self, destination: str, info_type: str) -> str:
        """Build an optimized search query for a destination and info type.

        Args:
            destination: Name of the destination
            info_type: Type of information to search for

        Returns:
            A formatted search query string
        """
        query_templates = {
            "general": "travel guide {destination} best things to do",
            "attractions": "top attractions in {destination} must-see sights",
            "safety": "{destination} travel safety information for tourists",
            "transportation": "how to get around {destination} public transportation",
            "best_time": "best time to visit {destination} weather seasons",
            "budget": "{destination} travel cost budget accommodation food",
            "food": "best restaurants in {destination} local cuisine food specialties",
            "culture": "{destination} local customs culture etiquette tips",
            "day_trips": "best day trips from {destination} nearby attractions",
            "family": "things to do in {destination} with children family-friendly",
        }

        template = query_templates.get(
            info_type, "travel information about {destination} {info_type}"
        )
        return template.format(destination=destination, info_type=info_type)

    @function_tool
    async def compare_travel_options(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare travel options for a specific category using WebSearchTool
        and specialized APIs.

        Args:
            params: Parameters for the comparison
                category: Type of comparison ("flights", "accommodations", "activities")
                origin: Origin location (for flights)
                destination: Destination location
                dates: Travel dates
                preferences: Any specific preferences to consider

        Returns:
            Dictionary containing comparison results
        """
        try:
            # Extract parameters
            category = params.get("category")
            destination = params.get("destination")

            if not category or not destination:
                return {"error": "Category and destination parameters are required"}

            # Specialized handling based on category
            if category == "flights":
                origin = params.get("origin")
                if not origin:
                    return {
                        "error": "Origin parameter is required for flight comparisons"
                    }

                departure_date = params.get("departure_date")
                return_date = params.get("return_date")

                if not departure_date:
                    return {"error": "Departure date is required for flight comparisons"}

                # Use Flights MCP if available
                if hasattr(self, "flights_client") and self.flights_client:
                    try:
                        flight_results = await self.flights_client.search_flights(
                            origin=origin,
                            destination=destination,
                            departure_date=departure_date,
                            return_date=return_date,
                            adults=params.get("adults", 1),
                            cabin_class=params.get("cabin_class", "economy"),
                        )

                        if "error" not in flight_results:
                            return {
                                "category": "flights",
                                "origin": origin,
                                "destination": destination,
                                "results": flight_results,
                                "source": "flights_mcp"
                            }
                    except Exception as e:
                        logger.warning("Flights MCP search failed: %s", str(e))

                # Fallback to web search
                return {
                    "category": "flights",
                    "origin": origin,
                    "destination": destination,
                    "search_strategy": "hybrid",
                    "note": (
                        "The agent will use WebSearchTool for flight information"
                    ),
                }

            elif category == "accommodations":
                check_in_date = params.get("check_in_date")
                check_out_date = params.get("check_out_date")

                if not check_in_date or not check_out_date:
                    return {"error": "Check-in and check-out dates are required"}

                # Use Accommodations MCP if available
                if hasattr(self, "accommodations_client") and self.accommodations_client:
                    try:
                        accommodation_results = await self.accommodations_client.search_accommodations(
                            location=destination,
                            check_in_date=check_in_date,
                            check_out_date=check_out_date,
                            adults=params.get("adults", 1),
                            children=params.get("children", 0),
                            rooms=params.get("rooms", 1),
                            max_price_per_night=params.get("max_price_per_night")
                        )

                        if "error" not in accommodation_results:
                            return {
                                "category": "accommodations",
                                "destination": destination,
                                "results": accommodation_results,
                                "source": "accommodations_mcp"
                            }
                    except Exception as e:
                        logger.warning("Accommodations MCP search failed: %s", str(e))

                return {
                    "category": "accommodations",
                    "destination": destination,
                    "search_strategy": "hybrid",
                    "note": (
                        "The agent will use WebSearchTool for accommodation information"
                    ),
                }

            elif category == "activities":
                # Use WebCrawl MCP if available
                if hasattr(self, "webcrawl_client") and self.webcrawl_client:
                    try:
                        activity_results = await self.webcrawl_client.search_activities(
                            location=destination,
                            category=params.get("activity_type"),
                            max_price=params.get("max_price")
                        )

                        if "error" not in activity_results:
                            return {
                                "category": "activities",
                                "destination": destination,
                                "results": activity_results,
                                "source": "webcrawl_mcp"
                            }
                    except Exception as e:
                        logger.warning("WebCrawl MCP search failed: %s", str(e))

                return {
                    "category": "activities",
                    "destination": destination,
                    "search_strategy": "hybrid",
                    "note": (
                        "The agent will use WebSearchTool to find activity information"
                    ),
                }

            else:
                return {
                    "category": category,
                    "destination": destination,
                    "search_strategy": "web_search",
                    "note": (
                        "The agent will use WebSearchTool to find general information"
                    ),
                }

        except Exception as e:
            logger.error("Error comparing travel options: %s", str(e))
            return {"error": f"Comparison error: {str(e)}"}

    @function_tool
    async def optimize_itinerary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize a travel itinerary based on various constraints.

        Args:
            params: Parameters for optimization
                trip_id: ID of the trip to optimize
                constraints: Dictionary of constraints (e.g., budget, time, preferences)
                priorities: List of priorities (e.g., ["cost", "time", "experience"])

        Returns:
            Optimized itinerary information
        """
        try:
            # Extract parameters
            trip_id = params.get("trip_id")
            constraints = params.get("constraints", {})
            priorities = params.get("priorities", ["cost", "experience", "time"])

            if not trip_id:
                return {"error": "Trip ID is required"}

            # Connect to database
            from src.db.client import get_client
            db_client = get_client()

            # Get trip data
            trip = await db_client.get_trip(trip_id)
            if not trip:
                return {"error": f"Trip with ID {trip_id} not found"}

            # Get related data
            flights = await db_client.get_trip_flights(trip_id)
            accommodations = await db_client.get_trip_accommodations(trip_id)
            activities = await db_client.get_trip_activities(trip_id)
            itinerary_items = await db_client.get_trip_itinerary_items(trip_id)

            # Prepare optimization data
            optimization_data = {
                "trip": trip,
                "flights": flights,
                "accommodations": accommodations,
                "activities": activities,
                "itinerary": itinerary_items,
                "constraints": constraints,
                "priorities": priorities
            }

            # Check if we already have an optimized itinerary
            existing_optimization = await db_client.get_trip_optimization(trip_id)
            if existing_optimization:
                return {
                    "trip_id": trip_id,
                    "optimization_id": existing_optimization["id"],
                    "optimized_itinerary": existing_optimization["optimized_itinerary"],
                    "optimization_notes": existing_optimization["optimization_notes"],
                    "updated": False
                }

            # This would implement actual optimization logic in a real implementation
            # For now, just reorder activities based on priorities

            # Apply simple optimization based on priorities
            optimized_itinerary = self._apply_simple_optimization(
                itinerary_items, constraints, priorities
            )

            # Create optimization record in database
            optimization_id = await db_client.create_trip_optimization(
                trip_id=trip_id,
                optimized_itinerary=optimized_itinerary,
                optimization_notes=f"Optimized based on priorities: {', '.join(priorities)}"
            )

            return {
                "trip_id": trip_id,
                "optimization_id": optimization_id,
                "optimized_itinerary": optimized_itinerary,
                "optimization_notes": f"Optimized based on priorities: {', '.join(priorities)}",
                "updated": True
            }

        except Exception as e:
            logger.error("Error optimizing itinerary: %s", str(e))
            return {"error": f"Optimization error: {str(e)}"}

    def _apply_simple_optimization(
        self, itinerary_items: List[Dict[str, Any]],
        constraints: Dict[str, Any],
        priorities: List[str]
    ) -> List[Dict[str, Any]]:
        """Apply a simple optimization to itinerary items.

        Args:
            itinerary_items: List of itinerary items to optimize
            constraints: Dictionary of constraints
            priorities: List of priorities

        Returns:
            Optimized list of itinerary items
        """
        # Clone the itinerary items to avoid modifying the original
        optimized_items = itinerary_items.copy()

        # Apply sorting based on priorities
        if "cost" in priorities:
            # Sort by cost (lowest first) for cost-sensitive travelers
            optimized_items.sort(key=lambda x: x.get("cost", float("inf")))
        elif "time" in priorities:
            # Group by day and optimize for shortest travel times
            optimized_items.sort(key=lambda x: (x.get("day_number", 0), x.get("start_time", "")))
        elif "experience" in priorities:
            # Sort by priority/importance for experience-focused travelers
            optimized_items.sort(key=lambda x: x.get("priority", 0), reverse=True)

        return optimized_items

    @function_tool
    async def calculate_budget_breakdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate a detailed budget breakdown for a trip.

        Args:
            params: Parameters for budget calculation
                trip_id: ID of the trip to calculate budget for
                include_booked: Whether to include only booked items (default: true)
                include_planned: Whether to include planned but not booked items (default: true)

        Returns:
            Detailed budget breakdown by category
        """
        try:
            # Extract parameters
            trip_id = params.get("trip_id")
            include_booked = params.get("include_booked", True)
            include_planned = params.get("include_planned", True)

            if not trip_id:
                return {"error": "Trip ID is required"}

            # Connect to database
            from src.db.client import get_client
            db_client = get_client()

            # Get trip data
            trip = await db_client.get_trip(trip_id)
            if not trip:
                return {"error": f"Trip with ID {trip_id} not found"}

            # Get trip items by category
            flights = await db_client.get_trip_flights(trip_id)
            accommodations = await db_client.get_trip_accommodations(trip_id)
            transportation = await db_client.get_trip_transportation(trip_id)
            activities = await db_client.get_trip_activities(trip_id)

            # Filter by booking status
            statuses = []
            if include_booked:
                statuses.append("booked")
            if include_planned:
                statuses.append("planned")

            if statuses:
                flights = [f for f in flights if f.get("status") in statuses]
                accommodations = [a for a in accommodations if a.get("status") in statuses]
                transportation = [t for t in transportation if t.get("status") in statuses]
                activities = [a for a in activities if a.get("status") in statuses]

            # Calculate total and breakdown
            flight_total = sum(f.get("price", 0) for f in flights)
            accommodation_total = sum(a.get("price", 0) for a in accommodations)
            transportation_total = sum(t.get("price", 0) for t in transportation)
            activity_total = sum(a.get("price", 0) for a in activities)

            # Calculate total spent
            total_spent = flight_total + accommodation_total + transportation_total + activity_total

            # Calculate remaining budget
            remaining = trip.get("budget", 0) - total_spent

            # Calculate percentage breakdown
            total_budget = trip.get("budget", 0)
            breakdown_percentages = {}
            if total_budget > 0:
                breakdown_percentages = {
                    "flights": (flight_total / total_budget) * 100,
                    "accommodations": (accommodation_total / total_budget) * 100,
                    "transportation": (transportation_total / total_budget) * 100,
                    "activities": (activity_total / total_budget) * 100,
                    "remaining": (remaining / total_budget) * 100
                }

            return {
                "trip_id": trip_id,
                "total_budget": total_budget,
                "total_spent": total_spent,
                "remaining": remaining,
                "breakdown": {
                    "flights": flight_total,
                    "accommodations": accommodation_total,
                    "transportation": transportation_total,
                    "activities": activity_total
                },
                "percentages": breakdown_percentages
            }

        except Exception as e:
            logger.error("Error calculating budget breakdown: %s", str(e))
            return {"error": f"Budget calculation error: {str(e)}"}

    @function_tool
    async def get_travel_recommendations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get personalized travel recommendations from knowledge graph.

        Args:
            params: Parameters for recommendation generation
                user_id: ID of the user to get recommendations for
                destination: Optional destination to filter recommendations
                interests: List of user interests to consider
                budget_range: Optional budget range for recommendations

        Returns:
            List of personalized travel recommendations
        """
        try:
            user_id = params.get("user_id")
            if not user_id:
                return {"error": "User ID is required"}

            # Use Memory MCP if available
            if hasattr(self, "memory_client") and self.memory_client:
                try:
                    # Get user entity from knowledge graph
                    user_nodes = await self.memory_client.open_nodes([f"User:{user_id}"])
                    if not user_nodes:
                        # User not found in knowledge graph
                        return {
                            "recommendations": [],
                            "reason": "User not found in knowledge graph"
                        }

                    user_node = user_nodes[0]

                    # Get user preferences and previous trips
                    preferences = []
                    for observation in user_node.get("observations", []):
                        if observation.startswith("Prefers "):
                            preferences.append(observation)

                    # Search for relevant nodes based on destination and interests
                    destination = params.get("destination")
                    interests = params.get("interests", [])

                    search_terms = []
                    if destination:
                        search_terms.append(destination)
                    search_terms.extend(interests)

                    # Construct search query
                    search_query = " OR ".join(search_terms) if search_terms else None

                    if search_query:
                        relevant_nodes = await self.memory_client.search_nodes(search_query)
                    else:
                        # If no specific search terms, get popular destinations
                        relevant_nodes = await self.memory_client.search_nodes("popular destination")

                    # Filter and rank recommendations based on user preferences
                    recommendations = []
                    for node in relevant_nodes:
                        if node["type"] == "Destination":
                            match_score = 0

                            # Check for preference matches
                            for pref in preferences:
                                for obs in node.get("observations", []):
                                    if pref in obs:
                                        match_score += 1

                            # Add to recommendations if score is positive
                            if match_score > 0 or not preferences:
                                recommendations.append({
                                    "destination": node["name"],
                                    "match_score": match_score,
                                    "observations": node.get("observations", [])
                                })

                    # Sort by match score
                    recommendations.sort(key=lambda x: x["match_score"], reverse=True)

                    # Apply budget filtering if specified
                    budget_range = params.get("budget_range")
                    if budget_range:
                        min_budget = budget_range.get("min")
                        max_budget = budget_range.get("max")

                        if min_budget is not None or max_budget is not None:
                            filtered_recommendations = []
                            for rec in recommendations:
                                # Extract budget info from observations
                                budget_info = next(
                                    (obs for obs in rec.get("observations", []) if "budget" in obs.lower()),
                                    None
                                )

                                if budget_info:
                                    # Simple budget extraction (would be more sophisticated in real impl)
                                    try:
                                        budget_text = budget_info.split("$")[1].split(" ")[0]
                                        budget = float(budget_text.replace(",", ""))

                                        if (min_budget is None or budget >= min_budget) and \
                                           (max_budget is None or budget <= max_budget):
                                            filtered_recommendations.append(rec)
                                    except (IndexError, ValueError):
                                        # If we can't parse budget, include it anyway
                                        filtered_recommendations.append(rec)
                                else:
                                    # No budget info, include it
                                    filtered_recommendations.append(rec)

                            recommendations = filtered_recommendations

                    return {
                        "user_id": user_id,
                        "preferences": preferences,
                        "recommendations": recommendations,
                        "source": "knowledge_graph"
                    }

                except Exception as e:
                    logger.error("Error getting recommendations from knowledge graph: %s", str(e))

            # Fallback if Memory MCP not available or failed
            return {
                "user_id": user_id,
                "recommendations": [],
                "source": "fallback",
                "note": "Personalized recommendations require knowledge graph integration"
            }

        except Exception as e:
            logger.error("Error getting travel recommendations: %s", str(e))
            return {"error": f"Recommendation error: {str(e)}"}

    @function_tool
    async def store_travel_knowledge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Store travel knowledge in the knowledge graph.

        Args:
            params: Parameters for knowledge storage
                entity_type: Type of entity (e.g., "Destination", "Accommodation")
                entity_name: Name of the entity
                observations: List of observations about the entity
                relations: List of relations to other entities

        Returns:
            Confirmation of knowledge storage
        """
        try:
            # Extract parameters
            entity_type = params.get("entity_type")
            entity_name = params.get("entity_name")
            observations = params.get("observations", [])
            relations = params.get("relations", [])

            if not entity_type or not entity_name:
                return {"error": "Entity type and name are required"}

            # Use Memory MCP if available
            if hasattr(self, "memory_client") and self.memory_client:
                try:
                    # Create entity if it doesn't exist
                    existing_nodes = await self.memory_client.search_nodes(entity_name)

                    entity_exists = any(
                        node["name"] == entity_name and node["type"] == entity_type
                        for node in existing_nodes
                    )

                    if not entity_exists:
                        # Create new entity
                        await self.memory_client.create_entities([{
                            "name": entity_name,
                            "entityType": entity_type,
                            "observations": observations
                        }])
                    else:
                        # Add observations to existing entity
                        await self.memory_client.add_observations([{
                            "entityName": entity_name,
                            "contents": observations
                        }])

                    # Create relations
                    if relations:
                        relation_objects = []
                        for relation in relations:
                            if "from" in relation and "to" in relation and "type" in relation:
                                relation_objects.append({
                                    "from": relation["from"],
                                    "relationType": relation["type"],
                                    "to": relation["to"]
                                })

                        if relation_objects:
                            await self.memory_client.create_relations(relation_objects)

                    return {
                        "success": True,
                        "entity_type": entity_type,
                        "entity_name": entity_name,
                        "observations_count": len(observations),
                        "relations_count": len(relation_objects) if relations else 0,
                        "message": "Knowledge stored successfully"
                    }

                except Exception as e:
                    logger.error("Error storing knowledge in graph: %s", str(e))
                    return {"error": f"Knowledge graph error: {str(e)}"}

            # Memory MCP not available
            return {
                "success": False,
                "error": "Knowledge graph not available",
                "note": "This feature requires Memory MCP integration"
            }

        except Exception as e:
            logger.error("Error storing travel knowledge: %s", str(e))
            return {"error": f"Knowledge storage error: {str(e)}"}


def create_travel_agent() -> TripSageTravelAgent:
    """Create and return a TripSageTravelAgent instance with all tools initialized."""
    return TripSageTravelAgent()
```

## Integration with MCP Servers

The Travel Planning Agent integrates with multiple MCP servers to provide comprehensive functionality. Here's how each MCP server is integrated:

### Weather MCP

```python
from src.mcp.weather.client import WeatherMCPClient

# Initialize client in TripSageTravelAgent.__init__
self.weather_client = WeatherMCPClient()

# Register tools
self._register_mcp_client_tools(self.weather_client, prefix="weather_")

# Example weather-specific code
async def check_destination_weather(self, destination, dates):
    """Check weather for a destination during specific dates."""
    try:
        # Get location coordinates
        location = await self.maps_client.geocode(destination)

        # Get weather forecast
        forecast = await self.weather_client.get_forecast(
            lat=location["lat"],
            lon=location["lng"],
            days=7
        )

        # Filter for relevant dates
        # ...

        return forecast
    except Exception as e:
        logger.error("Weather check failed: %s", str(e))
        return {"error": str(e)}
```

### Flight MCP

```python
from src.mcp.flights.client import FlightsMCPClient

# Initialize client in TripSageTravelAgent.__init__
self.flights_client = FlightsMCPClient()

# Register tools
self._register_mcp_client_tools(self.flights_client, prefix="flights_")

# Flight search usage example
async def find_optimal_flights(self, origin, destination, date_range):
    """Find optimal flights within a date range."""
    best_flight = None
    best_price = float('inf')

    for date in date_range:
        try:
            results = await self.flights_client.search_flights(
                origin=origin,
                destination=destination,
                departure_date=date.strftime("%Y-%m-%d")
            )

            # Find cheapest flight
            if results.get("flights"):
                for flight in results["flights"]:
                    if flight["price"] < best_price:
                        best_price = flight["price"]
                        best_flight = flight
        except Exception as e:
            logger.error("Flight search failed: %s", str(e))

    return best_flight
```

### Accommodations MCP

```python
from src.mcp.accommodations.client import AccommodationsMCPClient

# Initialize client in TripSageTravelAgent.__init__
self.accommodations_client = AccommodationsMCPClient()

# Register tools
self._register_mcp_client_tools(self.accommodations_client, prefix="accommodations_")

# Accommodation search example
async def find_best_accommodation(self, destination, check_in, check_out, preferences):
    """Find best accommodation matching preferences."""
    try:
        results = await self.accommodations_client.search_accommodations(
            location=destination,
            check_in_date=check_in,
            check_out_date=check_out,
            property_type=preferences.get("property_type"),
            max_price_per_night=preferences.get("max_price"),
            amenities=preferences.get("amenities", [])
        )

        # Filter and rank results based on preferences
        # ...

        return results
    except Exception as e:
        logger.error("Accommodation search failed: %s", str(e))
        return {"error": str(e)}
```

### Google Maps MCP

```python
from src.mcp.googlemaps.client import GoogleMapsMCPClient

# Initialize client in TripSageTravelAgent.__init__
self.maps_client = GoogleMapsMCPClient()

# Register tools
self._register_mcp_client_tools(self.maps_client, prefix="maps_")

# Example usage in itinerary planning
async def optimize_daily_routes(self, destination, activities):
    """Optimize daily routes between activities."""
    try:
        # Get coordinates for activities
        locations = []
        for activity in activities:
            place = await self.maps_client.geocode(
                f"{activity['name']}, {destination}"
            )
            locations.append({
                "id": activity["id"],
                "name": activity["name"],
                "location": place
            })

        # Calculate distance matrix
        matrix = await self.maps_client.distance_matrix(
            origins=[loc["location"] for loc in locations],
            destinations=[loc["location"] for loc in locations],
            mode="walking"
        )

        # Use matrix to optimize route
        # ...

        return optimized_route
    except Exception as e:
        logger.error("Route optimization failed: %s", str(e))
        return {"error": str(e)}
```

### Web Crawling MCP

```python
from src.mcp.webcrawl.client import WebCrawlMCPClient

# Initialize client in TripSageTravelAgent.__init__
self.webcrawl_client = WebCrawlMCPClient()

# Register tools
self._register_mcp_client_tools(self.webcrawl_client, prefix="webcrawl_")

# Example use case for specialized content extraction
async def get_hotel_reviews(self, hotel_name, location):
    """Get detailed reviews for a hotel."""
    try:
        # Create search query
        query = f"{hotel_name} {location} reviews"

        # Search for relevant pages
        search_results = await self.webcrawl_client.search(query)

        # Extract content from top results
        review_content = []
        for result in search_results[:3]:
            content = await self.webcrawl_client.extract_page_content(
                url=result["url"],
                selectors=["#reviews", ".review-content", "[itemprop='review']"]
            )
            review_content.append({
                "url": result["url"],
                "content": content
            })

        return {
            "hotel": hotel_name,
            "location": location,
            "reviews": review_content
        }
    except Exception as e:
        logger.error("Review extraction failed: %s", str(e))
        return {"error": str(e)}
```

### Memory MCP

```python
from src.mcp.memory.client import MemoryMCPClient

# Initialize client in TripSageTravelAgent.__init__
self.memory_client = MemoryMCPClient()

# Register tools
self._register_mcp_client_tools(self.memory_client, prefix="memory_")

# Example knowledge graph operations
async def record_user_preferences(self, user_id, preferences):
    """Record user preferences in knowledge graph."""
    try:
        # Check if user entity exists
        user_node = f"User:{user_id}"
        nodes = await self.memory_client.open_nodes([user_node])

        # Create user entity if it doesn't exist
        if not nodes:
            await self.memory_client.create_entities([{
                "name": user_node,
                "entityType": "User",
                "observations": [f"User ID: {user_id}"]
            }])

        # Convert preferences to observations
        observations = []
        for category, preference in preferences.items():
            observations.append(f"Prefers {preference} for {category}")

        # Add observations to user entity
        await self.memory_client.add_observations([{
            "entityName": user_node,
            "contents": observations
        }])

        return {
            "success": True,
            "user_id": user_id,
            "preferences_stored": len(observations)
        }
    except Exception as e:
        logger.error("Failed to record preferences: %s", str(e))
        return {"error": str(e)}
```

## Dual Storage Architecture Integration

The Travel Planning Agent integrates with both Supabase and the knowledge graph for comprehensive data management:

```python
async def get_trip_with_knowledge(self, trip_id):
    """Get trip details from both Supabase and knowledge graph."""
    try:
        # Get structured data from Supabase
        from src.db.client import get_client
        db_client = get_client()

        trip = await db_client.get_trip(trip_id)
        flights = await db_client.get_trip_flights(trip_id)
        accommodations = await db_client.get_trip_accommodations(trip_id)

        # Get semantic data from knowledge graph
        kg_data = {}
        if hasattr(self, "memory_client") and self.memory_client:
            trip_node = await self.memory_client.open_nodes([f"Trip:{trip_id}"])
            if trip_node:
                kg_data = trip_node[0]

                # Get related entities
                destination = trip.get("destination")
                if destination:
                    destination_node = await self.memory_client.open_nodes([destination])
                    if destination_node:
                        kg_data["destination_knowledge"] = destination_node[0]

        return {
            "trip": trip,
            "flights": flights,
            "accommodations": accommodations,
            "knowledge_graph": kg_data
        }
    except Exception as e:
        logger.error("Error retrieving trip data: %s", str(e))
        return {"error": str(e)}
```

## WebSearchTool Integration

The Travel Planning Agent integrates with OpenAI's WebSearchTool for general web search capabilities:

```python
def __init__(self, name="TripSage Travel Planner", model="gpt-4", temperature=0.2):
    super().__init__(name=name, model=model, temperature=temperature)

    # Add WebSearchTool with travel-specific domain configuration
    self.web_search_tool = WebSearchTool(
        allowed_domains=AllowedDomains(
            domains=[
                # Travel information and guides
                "tripadvisor.com", "lonelyplanet.com", "wikitravel.org",
                "travel.state.gov", "wikivoyage.org", "frommers.com",
                # Transportation sites
                "kayak.com", "skyscanner.com", "expedia.com", "booking.com",
                "hotels.com", "airbnb.com", "vrbo.com",
                # Airlines
                "united.com", "aa.com", "delta.com", "southwest.com",
                "britishairways.com", "lufthansa.com",
                # Weather
                "weather.com", "accuweather.com", "weatherspark.com",
                # Government travel advisories
                "travel.state.gov", "smartraveller.gov.au",
                "gov.uk/foreign-travel-advice",
            ]
        ),
        blocked_domains=["pinterest.com", "quora.com"],
    )
    self.agent.tools.append(self.web_search_tool)
```

## Caching Strategy

The Travel Planning Agent implements a robust caching strategy for performance optimization:

```python
from src.cache.redis_cache import redis_cache

async def get_cached_destination_info(self, destination, info_type):
    """Get destination information with caching."""
    cache_key = f"destination:{destination}:info_type:{info_type}"

    # Check cache first
    cached_result = await redis_cache.get(cache_key)
    if cached_result:
        return {**cached_result, "cache": "hit"}

    # Fetch from appropriate source
    if info_type == "weather":
        result = await self.weather_client.get_forecast(city=destination)
    elif info_type == "attractions":
        result = await self.webcrawl_client.search_destination_info(
            destination=destination, info_type="attractions"
        )
    else:
        # Use search for general info
        query = self._build_destination_query(destination, info_type)
        # WebSearchTool will be used by the agent
        result = {"query": query, "source": "web_search"}

    # Cache the result with appropriate TTL
    if "error" not in result:
        ttl = self._determine_cache_ttl(info_type)
        await redis_cache.set(cache_key, result, ttl=ttl)

    return {**result, "cache": "miss"}

def _determine_cache_ttl(self, info_type):
    """Determine appropriate cache TTL based on content volatility."""
    ttl_map = {
        "weather": 3600,  # 1 hour
        "attractions": 86400,  # 1 day
        "safety": 86400 * 7,  # 1 week
        "transportation": 86400 * 3,  # 3 days
        "best_time": 86400 * 30,  # 30 days
        "culture": 86400 * 30,  # 30 days
    }
    return ttl_map.get(info_type, 3600 * 12)  # 12 hours default
```

## Testing Strategy

```python
# tests/agents/test_travel_agent.py
import pytest
from unittest.mock import AsyncMock, patch

from src.agents.travel_agent_impl import TripSageTravelAgent

@pytest.fixture
def travel_agent():
    """Create a travel agent for testing."""
    agent = TripSageTravelAgent()

    # Mock MCP clients
    agent.flights_client = AsyncMock()
    agent.weather_client = AsyncMock()
    agent.accommodations_client = AsyncMock()
    agent.maps_client = AsyncMock()
    agent.webcrawl_client = AsyncMock()
    agent.memory_client = AsyncMock()

    return agent

@pytest.mark.asyncio
async def test_create_trip(travel_agent):
    """Test create_trip functionality."""
    # Mock database client
    with patch("src.db.client.get_client") as mock_get_client:
        mock_db = AsyncMock()
        mock_db.create_trip.return_value = "trip_123"
        mock_get_client.return_value = mock_db

        # Call method
        result = await travel_agent.create_trip({
            "user_id": "user_1",
            "title": "Trip to Paris",
            "destination": "Paris",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "budget": 2000.0
        })

        # Assertions
        assert result["success"] is True
        assert result["trip_id"] == "trip_123"
        mock_db.create_trip.assert_called_once()

@pytest.mark.asyncio
async def test_search_destination_info(travel_agent):
    """Test search_destination_info functionality."""
    # Mock WebCrawl client
    travel_agent.webcrawl_client.search_destination_info.return_value = {
        "destination": "Paris",
        "highlights": ["Eiffel Tower", "Louvre Museum"]
    }

    # Mock Redis cache
    with patch("src.cache.redis_cache.redis_cache.get") as mock_get:
        mock_get.return_value = None  # Cache miss

        # Call method
        result = await travel_agent.search_destination_info({
            "destination": "Paris",
            "info_types": ["attractions"]
        })

        # Assertions
        assert result["destination"] == "Paris"
        assert "attractions" in result["search_results"]
        travel_agent.webcrawl_client.search_destination_info.assert_called_once()
```

## Production Deployment

For production deployment, the Travel Planning Agent should be containerized and deployed with proper resource allocation:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Start the agent service
CMD ["python", "-m", "src.agents.service"]
```

## Resource Requirements

- **CPU**: 2-4 cores recommended
- **Memory**: 4-8GB minimum (depends on concurrent users)
- **Storage**: Minimal (20GB sufficient for code and logs)
- **Database**: PostgreSQL via Supabase, Neo4j for knowledge graph
- **Cache**: Redis for distributed caching

## Monitoring and Logging

Comprehensive monitoring should be implemented for the Travel Planning Agent:

```python
# src/agents/service.py
import logging
import prometheus_client
from prometheus_client import Counter, Histogram
from fastapi import FastAPI, Request

# Set up metrics
REQUEST_COUNT = Counter('travel_agent_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('travel_agent_request_latency_seconds', 'Request latency')
ERROR_COUNT = Counter('travel_agent_errors_total', 'Total errors')

app = FastAPI()

# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    return prometheus_client.generate_latest()

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy"}

# Create agent instance
travel_agent = TripSageTravelAgent()

@app.post("/agent/run")
@REQUEST_LATENCY.time()
async def run_agent(request: Request):
    REQUEST_COUNT.inc()
    try:
        data = await request.json()
        user_input = data.get("input")
        context = data.get("context", {})

        response = await travel_agent.run(user_input, context)
        return response
    except Exception as e:
        ERROR_COUNT.inc()
        logging.error(f"Agent run error: {str(e)}")
        return {"error": str(e)}
```

## Conclusion

The Travel Planning Agent serves as the primary interface for users of the TripSage platform, integrating multiple specialized MCP services, dual storage architecture, and hybrid search strategies. By following this implementation guide, you can create a robust, comprehensive travel planning solution that meets all the requirements outlined in the TripSage implementation plan.

The agent is designed to be:

1. **Comprehensive**: Integrating all travel-related services
2. **Personalized**: Utilizing knowledge graph for customized recommendations
3. **Efficient**: Implementing caching strategies for performance
4. **Reliable**: Including thorough error handling and testing
5. **Maintainable**: Following the project's coding standards and patterns

This implementation leverages the OpenAI Agents SDK pattern while extending it with travel-specific capabilities, making it a perfect fit for the TripSage ecosystem.
````

## File: implementation/tripsage_implementation_plan.md

````markdown
# TripSage Implementation Plan

This document provides a comprehensive implementation plan for completing the TripSage AI travel planning system. It outlines all necessary tasks, their dependencies, and links to relevant documentation.

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Core Infrastructure](#2-core-infrastructure)
3. [MCP Server Implementation](#3-mcp-server-implementation)
4. [Database Implementation](#4-database-implementation)
5. [Agent Development](#5-agent-development)
6. [API Integration](#6-api-integration)
7. [Testing Strategy](#7-testing-strategy)
8. [Security Implementation](#8-security-implementation)
9. [Deployment Strategy](#9-deployment-strategy)
10. [Post-MVP Enhancements](#10-post-mvp-enhancements)

## 1. Environment Setup

### 1.1 Development Environment Setup

- [ ] Set up Python virtual environment using uv

  ```bash
  uv venv
  uv pip install -r requirements.txt
  ```

- [ ] Configure environment variables in `.env` file

  ```plaintext
  OPENAI_API_KEY=sk-...
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_ANON_KEY=eyJ...
  DUFFEL_API_KEY=duffel_test_...
  OPENWEATHERMAP_API_KEY=...
  ```

- [ ] Install necessary development tools (pytest, ruff, etc.)

  ```bash
  uv pip install pytest ruff mypy
  ```

### 1.2 Repository Organization

- [ ] Set up project structure following the established pattern

  ```plaintext
  src/
    mcp/           # MCP server implementations
    agents/        # Agent implementations
    api/           # FastAPI backend
    database/      # Database access layers
    utils/         # Shared utilities
  ```

- [ ] Configure Git hooks for linting and testing
- [ ] Set up branch strategy (main, dev, feature branches)

**Reference Documentation:**

- [CLAUDE.md](../../CLAUDE.md) - Project overview and coding standards
- [docs/installation/setup_guide.md](../installation/setup_guide.md) - Detailed setup instructions

## 2. Core Infrastructure

### 2.1 FastMCP 2.0 Configuration

- [ ] Install FastMCP 2.0

  ```bash
  uv pip install fastmcp==2.0.*
  ```

- [ ] Create base MCP server class

  ```python
  # src/mcp/base_mcp_server.py
  from fastmcp import FastMCP

  class BaseMCPServer:
      def __init__(self, name, port=3000):
          self.app = FastMCP()
          self.name = name
          self.port = port

      def run(self):
          self.app.run(host="0.0.0.0", port=self.port)
  ```

- [ ] Implement MCP client base class

  ```python
  # src/mcp/base_client.py
  import httpx
  import asyncio

  class BaseMCPClient:
      def __init__(self, endpoint):
          self.endpoint = endpoint

      async def call_tool(self, tool_name, params):
          async with httpx.AsyncClient() as client:
              response = await client.post(
                  f"{self.endpoint}/api/v1/tools/{tool_name}/call",
                  json={"params": params},
                  timeout=60.0
              )
              response.raise_for_status()
              return response.json()
  ```

### 2.2 Caching Infrastructure

- [ ] Set up Redis connection

  ```python
  # src/utils/redis_cache.py
  import redis
  import json
  from functools import wraps

  class RedisCache:
      def __init__(self, host="localhost", port=6379, db=0):
          self.client = redis.Redis(host=host, port=port, db=db)

      def get(self, key):
          value = self.client.get(key)
          if value:
              return json.loads(value)
          return None

      def set(self, key, value, ttl=None):
          self.client.set(key, json.dumps(value), ex=ttl)

      def cache(self, prefix, ttl=3600):
          def decorator(func):
              @wraps(func)
              async def wrapper(*args, **kwargs):
                  key = f"{prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
                  cached = self.get(key)
                  if cached:
                      return cached
                  result = await func(*args, **kwargs)
                  self.set(key, result, ttl)
                  return result
              return wrapper
          return decorator
  ```

### 2.3 Common Utility Functions

- [ ] Implement logging utilities

  ```python
  # src/utils/logging.py
  import logging
  import os
  from datetime import datetime

  def configure_logging(name, level=logging.INFO):
      logger = logging.getLogger(name)
      logger.setLevel(level)

      if not logger.handlers:
          handler = logging.StreamHandler()
          formatter = logging.Formatter(
              '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
          )
          handler.setFormatter(formatter)
          logger.addHandler(handler)

          # Add file handler
          os.makedirs("logs", exist_ok=True)
          file_handler = logging.FileHandler(
              f"logs/{name}_{datetime.now().strftime('%Y%m%d')}.log"
          )
          file_handler.setFormatter(formatter)
          logger.addHandler(file_handler)

      return logger
  ```

**Reference Documentation:**

- [docs/optimization/tripsage_optimization_strategy.md](../optimization/tripsage_optimization_strategy.md) - Overall architecture strategy
- [docs/optimization/search_and_caching_strategy.md](../optimization/search_and_caching_strategy.md) - Caching implementation

## 3. MCP Server Implementation

### 3.1 Weather MCP Server

- [ ] Create Weather MCP Server

  ```python
  # src/mcp/weather/server.py
  from fastmcp import FastMCP
  from pydantic import BaseModel
  from datetime import datetime
  from typing import List, Optional

  app = FastMCP()

  class LocationParams(BaseModel):
      lat: float
      lon: float
      city: Optional[str] = None
      country: Optional[str] = None

  class ForecastParams(BaseModel):
      location: LocationParams
      days: int = 5

  @app.tool
  async def get_current_weather(params: LocationParams):
      """Get current weather conditions for a location."""
      # Implementation using OpenWeatherMap

  @app.tool
  async def get_forecast(params: ForecastParams):
      """Get weather forecast for a location."""
      # Implementation using OpenWeatherMap with Visual Crossing fallback

  @app.tool
  async def get_travel_recommendation(params: LocationParams):
      """Get travel recommendations based on weather."""
      # Implementation using current weather and forecast data
  ```

- [ ] Implement OpenWeatherMap API client
- [ ] Implement Visual Crossing API client (secondary)
- [ ] Create Weather.gov API client (tertiary)
- [ ] Implement caching strategy for weather data
- [ ] Create Weather MCP Client class

**Reference Documentation:**

- [docs/integrations/weather_integration.md](../integrations/weather_integration.md) - Weather API integration guide
- [docs/integrations/weather_mcp_implementation.md](../integrations/weather_mcp_implementation.md) - Weather MCP server specification

### 3.2 Web Crawling MCP Server

- [ ] Set up Crawl4AI self-hosted environment
- [ ] Create Web Crawling MCP Server

  ```python
  # src/mcp/webcrawl/server.py
  from fastmcp import FastMCP
  from pydantic import BaseModel
  from typing import List, Optional, Dict, Union

  app = FastMCP()

  class ExtractionParams(BaseModel):
      url: str
      selectors: Optional[List[str]] = None
      include_images: bool = False
      format: str = "markdown"

  class DestinationParams(BaseModel):
      destination: str
      topics: Optional[List[str]] = None
      max_results: int = 5

  @app.tool
  async def extract_page_content(params: ExtractionParams):
      """Extract content from a webpage."""
      # Implementation using Crawl4AI

  @app.tool
  async def search_destination_info(params: DestinationParams):
      """Search for information about a travel destination."""
      # Implementation using Crawl4AI with fallback to Firecrawl
  ```

- [ ] Implement source selection logic for different content types
- [ ] Create adapter layer for Crawl4AI, Firecrawl, and Enhanced Playwright
- [ ] Implement batch processing for efficient parallel extractions
- [ ] Set up caching strategy with content-aware TTL
- [ ] Create Web Crawling MCP Client class

**Reference Documentation:**

- [docs/integrations/web_crawling.md](../integrations/web_crawling.md) - Web crawling specification
- [docs/integrations/webcrawl_mcp_implementation.md](../integrations/webcrawl_mcp_implementation.md) - Web crawling MCP implementation
- [docs/integrations/web_crawling_evaluation.md](../integrations/web_crawling_evaluation.md) - Evaluation of crawling technologies

### 3.3 Browser Automation MCP Server

- [ ] Install Playwright and dependencies

  ```bash
  uv pip install playwright
  python -m playwright install
  ```

- [ ] Create Browser Automation MCP Server using Playwright with Python

  ```python
  # src/mcp/browser/playwright_server.py
  from fastmcp import FastMCP
  from pydantic import BaseModel
  from playwright.async_api import async_playwright
  from typing import Dict, List, Optional

  app = FastMCP()

  # Create Pydantic models and implementations as specified in
  # docs/integrations/browser_automation.md
  ```

- [ ] Implement browser context management
- [ ] Create travel-specific automation functions
- [ ] Set up resource pooling and cleanup mechanisms
- [ ] Implement anti-detection strategies
- [ ] Create Browser Automation MCP Client class

**Reference Documentation:**

- [docs/integrations/browser_automation.md](../integrations/browser_automation.md) - Browser automation integration guide
- [docs/integrations/browser_automation_evaluation.md](../integrations/browser_automation_evaluation.md) - Evaluation of browser automation options

### 3.4 Flights MCP Server

- [ ] Create Flights MCP Server using Duffel API

  ```python
  # src/mcp/flights/server.py
  from fastmcp import FastMCP
  from pydantic import BaseModel
  from typing import List, Optional, Dict
  from datetime import date

  app = FastMCP()

  class FlightSearchParams(BaseModel):
      origin: str
      destination: str
      departure_date: date
      return_date: Optional[date] = None
      adults: int = 1
      children: int = 0
      infants: int = 0
      cabin_class: str = "economy"
      max_price: Optional[float] = None

  @app.tool
  async def search_flights(params: FlightSearchParams):
      """Search for available flights."""
      # Implementation using Duffel API
  ```

- [ ] Implement Duffel API client
- [ ] Create flight search and booking capabilities
- [ ] Set up price tracking and history
- [ ] Implement caching strategy for flight results
- [ ] Create Flights MCP Client class

**Reference Documentation:**

- [docs/integrations/flights_mcp_implementation.md](../integrations/flights_mcp_implementation.md) - Flights MCP server specification
- [docs/api/api_integration.md](../api/api_integration.md) - API integration guidelines

### 3.5 Accommodation MCP Server

- [ ] Create Accommodation MCP Server

  ```python
  # src/mcp/accommodations/server.py
  from fastmcp import FastMCP
  from pydantic import BaseModel
  from typing import List, Optional, Dict
  from datetime import date

  app = FastMCP()

  class AccommodationSearchParams(BaseModel):
      location: str
      check_in: date
      check_out: date
      adults: int = 2
      children: int = 0
      rooms: int = 1
      price_min: Optional[float] = None
      price_max: Optional[float] = None
      amenities: Optional[List[str]] = None

  @app.tool
  async def search_accommodations(params: AccommodationSearchParams):
      """Search for accommodations."""
      # Implementation using AirBnB and Booking.com APIs
  ```

- [ ] Implement AirBnB API integration
- [ ] Create Booking.com integration via Apify
- [ ] Develop unified accommodation search and comparison
- [ ] Set up caching strategy for accommodation results
- [ ] Create Accommodation MCP Client class

**Reference Documentation:**

- [docs/integrations/accommodations_mcp_implementation.md](../integrations/accommodations_mcp_implementation.md) - Accommodations MCP server specification
- [docs/integrations/airbnb_integration.md](../integrations/airbnb_integration.md) - AirBnB API integration

### 3.6 Calendar MCP Server

- [ ] Create Calendar MCP Server

  ```python
  # src/mcp/calendar/server.py
  from fastmcp import FastMCP
  from pydantic import BaseModel
  from typing import List, Optional, Dict
  from datetime import datetime

  app = FastMCP()

  class CalendarEventParams(BaseModel):
      title: str
      start_time: datetime
      end_time: datetime
      location: Optional[str] = None
      description: Optional[str] = None

  @app.tool
  async def create_calendar_event(params: CalendarEventParams):
      """Create a calendar event."""
      # Implementation using Google Calendar API
  ```

- [ ] Set up Google Calendar API integration
- [ ] Implement OAuth flow for user authorization
- [ ] Create tools for travel itinerary management
- [ ] Create Calendar MCP Client class

**Reference Documentation:**

- [docs/integrations/calendar_integration.md](../integrations/calendar_integration.md) - Calendar integration guide
- [docs/integrations/calendar_mcp_implementation.md](../integrations/calendar_mcp_implementation.md) - Calendar MCP server specification

### 3.7 Memory MCP Server

- [ ] Set up Neo4j with travel entity schemas
- [ ] Implement Memory MCP Server

  ```python
  # src/mcp/memory/server.py
  from fastmcp import FastMCP
  from pydantic import BaseModel
  from typing import List, Dict, Any, Optional

  app = FastMCP()

  class Entity(BaseModel):
      name: str
      entity_type: str
      observations: List[str]

  class Relation(BaseModel):
      from_entity: str
      to_entity: str
      relation_type: str

  @app.tool
  async def create_entities(entities: List[Entity]):
      """Create multiple entities in the knowledge graph."""
      # Implementation using Neo4j

  @app.tool
  async def create_relations(relations: List[Relation]):
      """Create relations between entities."""
      # Implementation using Neo4j
  ```

- [ ] Create tools for knowledge graph management
- [ ] Implement context persistence between sessions
- [ ] Set up travel entity schemas and relationships
- [ ] Create Memory MCP Client class

**Reference Documentation:**

- [docs/integrations/memory_integration.md](../integrations/memory_integration.md) - Memory integration guide

## 4. Database Implementation

### 4.1 Supabase Configuration

- [ ] Create Supabase project
- [ ] Implement database schema migrations

  ```sql
  -- migrations/20250508_01_initial_schema_core_tables.sql
  CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  );

  CREATE TABLE trips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    budget DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  );

  -- Additional tables as specified in database_setup.md
  ```

- [ ] Set up Row Level Security (RLS) policies
- [ ] Configure real-time subscriptions
- [ ] Implement database access layer

**Reference Documentation:**

- [docs/database_setup.md](../database_setup.md) - Database schema design
- [docs/database/supabase_integration.md](../database/supabase_integration.md) - Supabase integration guide

### 4.2 Neo4j Knowledge Graph

- [ ] Set up Neo4j database
- [ ] Create knowledge graph schema

  ```cypher
  // Create constraints and indexes
  CREATE CONSTRAINT IF NOT EXISTS FOR (d:Destination) REQUIRE d.name IS UNIQUE;
  CREATE CONSTRAINT IF NOT EXISTS FOR (h:Hotel) REQUIRE h.id IS UNIQUE;
  CREATE CONSTRAINT IF NOT EXISTS FOR (a:Airline) REQUIRE a.code IS UNIQUE;
  CREATE CONSTRAINT IF NOT EXISTS FOR (ap:Airport) REQUIRE ap.code IS UNIQUE;

  // Create indexes for frequent queries
  CREATE INDEX IF NOT EXISTS FOR (d:Destination) ON (d.country);
  CREATE INDEX IF NOT EXISTS FOR (h:Hotel) ON (h.city);
  ```

- [ ] Implement data synchronization between Supabase and Neo4j
- [ ] Create knowledge graph access layer

**Reference Documentation:**

- [docs/database/supabase_integration.md](../database/supabase_integration.md) - Knowledge graph integration

## 5. Agent Development

### 5.1 Base Agent Implementation

- [ ] Create base agent class using OpenAI Agents SDK

  ```python
  # src/agents/base_agent.py
  from agents import Agent, function_tool
  from typing import Dict, Any, List, Optional
  import asyncio

  class BaseAgent:
      def __init__(self, name, instructions, model="gpt-4", temperature=0.2):
          self.agent = Agent(
              name=name,
              instructions=instructions,
              model=model,
              temperature=temperature
          )
          self.tools = []

      def register_tool(self, tool):
          self.tools.append(tool)

      async def run(self, user_input):
          # Implementation using OpenAI Agents SDK
  ```

- [ ] Implement tool registration system
- [ ] Create MCP tool integration framework
- [ ] Set up error handling and retry mechanisms

**Reference Documentation:**

- [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md) - Agent design patterns

### 5.2 Travel Planning Agent

- [ ] Implement Travel Planning Agent

  ```python
  # src/agents/travel_agent.py
  from .base_agent import BaseAgent
  from src.mcp.flights.client import FlightsClient
  from src.mcp.accommodations.client import AccommodationsClient
  from src.mcp.weather.client import WeatherClient
  from src.mcp.webcrawl.client import WebCrawlClient

  class TravelPlanningAgent(BaseAgent):
      def __init__(self):
          super().__init__(
              name="Travel Planning Agent",
              instructions="""You are a comprehensive travel planning assistant..."""
          )

          # Initialize MCP clients
          self.flights_client = FlightsClient()
          self.accommodations_client = AccommodationsClient()
          self.weather_client = WeatherClient()
          self.webcrawl_client = WebCrawlClient()

          # Register tools
          self.register_tools()

      def register_tools(self):
          # Register flight search tools
          self.register_tool(self.search_flights)
          # Register accommodation search tools
          self.register_tool(self.search_accommodations)
          # Register weather tools
          self.register_tool(self.get_weather_forecast)
          # Register destination research tools
          self.register_tool(self.search_destination_info)
  ```

- [ ] Implement flight search and booking capabilities
- [ ] Create accommodation search and comparison features
- [ ] Develop destination research capabilities
- [ ] Implement itinerary creation and management

**Reference Documentation:**

- [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md) - Agent design patterns

### 5.3 Budget Planning Agent

- [ ] Implement Budget Planning Agent

  ```python
  # src/agents/budget_agent.py
  from .base_agent import BaseAgent

  class BudgetPlanningAgent(BaseAgent):
      def __init__(self):
          super().__init__(
              name="Budget Planning Agent",
              instructions="""You specialize in travel budget optimization..."""
          )

          # Initialize MCP clients

          # Register tools
  ```

- [ ] Create budget optimization capabilities
- [ ] Implement price tracking and comparison features
- [ ] Develop budgeting recommendations

**Reference Documentation:**

- [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md) - Agent design patterns

### 5.4 Itinerary Planning Agent

- [ ] Implement Itinerary Planning Agent

  ```python
  # src/agents/itinerary_agent.py
  from .base_agent import BaseAgent

  class ItineraryPlanningAgent(BaseAgent):
      def __init__(self):
          super().__init__(
              name="Itinerary Planning Agent",
              instructions="""You specialize in creating detailed travel itineraries..."""
          )

          # Initialize MCP clients

          # Register tools
  ```

- [ ] Create itinerary generation capabilities
- [ ] Implement calendar integration
- [ ] Develop event and activity scheduling features

**Reference Documentation:**

- [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md) - Agent design patterns

## 6. API Integration

### 6.1 FastAPI Backend

- [ ] Set up FastAPI application

  ```python
  # src/api/main.py
  from fastapi import FastAPI, Depends, HTTPException
  from fastapi.middleware.cors import CORSMiddleware
  import os

  app = FastAPI(title="TripSage API")

  # Add CORS middleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],  # Adjust for production
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  # Import routers
  from .routes.auth import router as auth_router
  from .routes.trips import router as trips_router
  from .routes.users import router as users_router

  # Register routers
  app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
  app.include_router(trips_router, prefix="/trips", tags=["Trips"])
  app.include_router(users_router, prefix="/users", tags=["Users"])
  ```

- [ ] Implement authentication routes
- [ ] Create trip management routes
- [ ] Develop user management routes
- [ ] Implement agent interaction endpoints

**Reference Documentation:**

- [docs/api/api_integration.md](../api/api_integration.md) - API integration guidelines

### 6.2 Authentication

- [ ] Set up JWT-based authentication

  ```python
  # src/api/auth.py
  from fastapi import Depends, HTTPException, status
  from fastapi.security import OAuth2PasswordBearer
  import jwt
  from datetime import datetime, timedelta
  from typing import Optional

  oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

  def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
      to_encode = data.copy()
      if expires_delta:
          expire = datetime.utcnow() + expires_delta
      else:
          expire = datetime.utcnow() + timedelta(minutes=15)
      to_encode.update({"exp": expire})
      encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
      return encoded_jwt

  async def get_current_user(token: str = Depends(oauth2_scheme)):
      # Implementation using JWT validation
  ```

- [ ] Implement Supabase authentication integration
- [ ] Create user management endpoints
- [ ] Implement role-based access control

**Reference Documentation:**

- [docs/api/api_integration.md](../api/api_integration.md) - Authentication implementation

### 6.3 Data Access Layer

- [ ] Create Supabase client

  ```python
  # src/database/supabase.py
  from supabase import create_client
  import os

  class SupabaseClient:
      def __init__(self):
          url = os.environ.get("SUPABASE_URL")
          key = os.environ.get("SUPABASE_ANON_KEY")
          self.client = create_client(url, key)

      async def get_trips(self, user_id):
          response = self.client.table("trips") \
              .select("*") \
              .eq("user_id", user_id) \
              .execute()
          return response.data
  ```

- [ ] Implement trip data access methods
- [ ] Create user data access methods
- [ ] Develop search and query capabilities

**Reference Documentation:**

- [docs/database/supabase_integration.md](../database/supabase_integration.md) - Supabase data access

## 7. Testing Strategy

### 7.1 Unit Tests

- [ ] Create unit tests for MCP services

  ```python
  # tests/mcp/test_weather_mcp.py
  import pytest
  from unittest.mock import AsyncMock, patch
  from src.mcp.weather.server import get_current_weather

  @pytest.fixture
  def mock_openweathermap():
      with patch("src.mcp.weather.apis.openweathermap.OpenWeatherMapAPI") as mock:
          mock.return_value.get_current_weather = AsyncMock(return_value={
              "temp": 25.5,
              "humidity": 65,
              "conditions": "Clear sky"
          })
          yield mock

  async def test_get_current_weather(mock_openweathermap):
      params = {
          "lat": 40.7128,
          "lon": -74.0060,
          "city": "New York"
      }
      result = await get_current_weather(params)
      assert "temp" in result
      assert result["temp"] == 25.5
  ```

- [ ] Implement tests for agent functions
- [ ] Create tests for API endpoints
- [ ] Develop tests for database access layers

### 7.2 Integration Tests

- [ ] Create integration tests for agent workflows
- [ ] Implement tests for MCP service interactions
- [ ] Develop tests for API-database interactions

### 7.3 End-to-End Tests

- [ ] Set up end-to-end testing framework
- [ ] Create tests for key user journeys
- [ ] Implement tests for complete workflows

## 8. Security Implementation

### 8.1 Authentication and Authorization

- [ ] Implement secure authentication flows
- [ ] Set up role-based access control
- [ ] Create secure session management

### 8.2 Secure Data Storage

- [ ] Implement encryption for sensitive data
- [ ] Set up secure environment variable management
- [ ] Create secure credential storage

### 8.3 API Security

- [ ] Implement rate limiting
- [ ] Set up CORS configuration
- [ ] Create input validation and sanitization

## 9. Deployment Strategy

### 9.1 Docker Containerization

- [ ] Create Docker configuration for MCP servers

  ```dockerfile
  # Dockerfile for MCP servers
  FROM python:3.10-slim

  WORKDIR /app

  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  COPY . .

  EXPOSE 3000

  CMD ["python", "src/mcp/server.py"]
  ```

- [ ] Create Docker Compose configuration

  ```yaml
  # docker-compose.yml
  version: "3"

  services:
    weather-mcp:
      build:
        context: .
        dockerfile: Dockerfile
      command: python src/mcp/weather/server.py
      ports:
        - "3001:3000"
      environment:
        - OPENWEATHERMAP_API_KEY=${OPENWEATHERMAP_API_KEY}
      restart: unless-stopped

    # Additional MCP services...

    api:
      build:
        context: .
        dockerfile: Dockerfile
      command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
      ports:
        - "8000:8000"
      depends_on:
        - weather-mcp
        - flights-mcp
        - accommodations-mcp
      environment:
        - WEATHER_MCP_ENDPOINT=http://weather-mcp:3000
        - FLIGHTS_MCP_ENDPOINT=http://flights-mcp:3000
        - ACCOMMODATIONS_MCP_ENDPOINT=http://accommodations-mcp:3000
      restart: unless-stopped
  ```

### 9.2 Kubernetes Deployment

- [ ] Create Kubernetes deployment manifests
- [ ] Set up service and ingress configurations
- [ ] Implement resource limits and requests

### 9.3 CI/CD Pipeline

- [ ] Set up GitHub Actions workflow

  ```yaml
  # .github/workflows/main.yml
  name: TripSage CI/CD

  on:
    push:
      branches: [main, dev]
    pull_request:
      branches: [main, dev]

  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - name: Set up Python
          uses: actions/setup-python@v4
          with:
            python-version: "3.10"
        - name: Install dependencies
          run: |
            python -m pip install --upgrade pip
            if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
            pip install pytest pytest-asyncio
        - name: Lint with ruff
          run: |
            pip install ruff
            ruff .
        - name: Test with pytest
          run: |
            pytest
  ```

- [ ] Create deployment workflows
- [ ] Set up testing and linting automation

## 10. Post-MVP Enhancements

### 10.1 Vector Search with Qdrant

- [ ] Set up Qdrant integration
- [ ] Implement embedding generation pipeline
- [ ] Create semantic search capabilities

### 10.2 Enhanced AI Capabilities

- [ ] Implement personalized recommendations
- [ ] Create trip optimization algorithms
- [ ] Develop sentiment analysis for reviews

### 10.3 Extended Integrations

- [ ] Add additional travel API integrations
- [ ] Implement social sharing capabilities
- [ ] Create export and import features

## Implementation Timeline

### Weeks 1-2: Foundation

- Set up development environment
- Implement Weather MCP Server
- Implement Web Crawling MCP Server
- Set up database schema

### Weeks 3-4: Travel Services

- Implement Flights MCP Server
- Implement Accommodation MCP Server
- Create Travel Planning Agent
- Develop API routes for trips

### Weeks 5-6: Context and Personalization

- Implement Calendar MCP Server
- Implement Memory MCP Server
- Create Budget Planning Agent
- Develop user authentication and profiles

### Weeks 7-8: Integration and Production

- Implement Itinerary Planning Agent
- Create end-to-end testing
- Set up deployment pipeline
- Optimize performance and reliability

### Post-MVP: Enhanced Capabilities

- Implement vector search with Qdrant
- Develop advanced recommendation algorithms
- Create additional travel integrations
````

## File: implementation/tripsage_todo_list.md

````markdown
# TripSage Implementation To-Do List

This document provides a complete implementation to-do list for the TripSage AI travel planning system. Tasks are organized by priority and component area with links to relevant documentation.

## Core Infrastructure

### High Priority

- [x] **ENV-001**: Set up Python development environment using uv

  - Dependencies: None
  - Reference: [docs/installation/setup_guide.md](../installation/setup_guide.md)
  - Status: Completed with pyproject.toml configuration and appropriate dependencies setup

- [x] **ENV-002**: Create project structure and repository organization

  - Dependencies: None
  - Reference: [CLAUDE.md](../../CLAUDE.md)
  - Status: Completed with organized directory structure following CLAUDE.md guidelines

- [x] **MCP-001**: Set up FastMCP 2.0 base infrastructure

  - Dependencies: ENV-001
  - Reference: [docs/optimization/tripsage_optimization_strategy.md](../optimization/tripsage_optimization_strategy.md)
  - Status: Completed with FastMCP 2.0 server and client classes, tool schema definitions, and compatibility layers

- [x] **DB-001**: Create Supabase project and implement database schema

  - Dependencies: None
  - Reference: [docs/database_setup.md](../database_setup.md), [docs/database/supabase_integration.md](../database/supabase_integration.md)
  - Status: Completed with adapter pattern supporting both Supabase and Neon

- [x] **DB-002**: Set up Neo4j instance for knowledge graph

  - Dependencies: None
  - Reference: [docs/integrations/memory_integration.md](../integrations/memory_integration.md)
  - Status: Completed with comprehensive Neo4j implementation guide and Memory MCP Server integration

- [x] **UTIL-001**: Implement logging and error handling infrastructure

  - Dependencies: ENV-001
  - Reference: [CLAUDE.md](../../CLAUDE.md)
  - Status: Completed with custom exception hierarchy and consistent error handling

- [x] **UTIL-003**: Implement centralized configuration with Pydantic

  - Dependencies: ENV-001
  - Reference: [docs/reference/centralized_settings.md](../reference/centralized_settings.md)
  - Status: Completed with AppSettings class using Pydantic, environment variable loading, and .env support (Issue #15)

- [x] **CACHE-001**: Set up Redis caching infrastructure
  - Dependencies: ENV-001
  - Reference: [docs/optimization/search_and_caching_strategy.md](../optimization/search_and_caching_strategy.md)
  - Status: Completed with TTL support, decorator patterns, and JSON serialization

### Medium Priority

- [ ] **SEC-001**: Create authentication and authorization infrastructure

  - Dependencies: DB-001
  - Reference: [docs/api/api_integration.md](../api/api_integration.md)

- [ ] **CI-001**: Set up GitHub Actions workflow for testing and linting

  - Dependencies: ENV-001, ENV-002
  - Reference: [docs/deployment/deployment_strategy.md](../deployment/deployment_strategy.md)

- [x] **UTIL-002**: Create common utility functions for date/time manipulation
  - Dependencies: ENV-001
  - Reference: [docs/integrations/time_integration.md](../integrations/time_integration.md)
  - Status: Completed with Time MCP implementation providing comprehensive time utilities

## MCP Server Implementation

### High Priority

### Core MCP Infrastructure

- [x] **MCP-002**: Standardize MCP client implementations with Pydantic v2 validation

  - Dependencies: MCP-001
  - Reference: PR #53, [docs/status/implementation_status.md](../status/implementation_status.md)
  - Status: Completed with standardized validation patterns, unified \_call_validate_tool method, and comprehensive tests for all MCP clients

- [x] **MCP-003**: Implement isolated testing pattern for MCP clients

  - Dependencies: MCP-002
  - Reference: [docs/optimization/isolated_mcp_testing.md](../optimization/isolated_mcp_testing.md)
  - Status: Completed with self-contained test modules, comprehensive fixtures, and no environment dependencies

### Weather MCP Server

- [x] **WEATHER-001**: Create Weather MCP Server structure

  - Dependencies: MCP-001
  - Reference: [docs/integrations/weather_integration.md](../integrations/weather_integration.md), [docs/integrations/weather_mcp_implementation.md](../integrations/weather_mcp_implementation.md)
  - Status: Completed with FastMCP 2.0 integration and dedicated tool handlers

- [x] **WEATHER-002**: Implement OpenWeatherMap API client

  - Dependencies: WEATHER-001
  - Reference: [docs/integrations/weather_integration.md](../integrations/weather_integration.md)
  - Status: Completed with Pydantic models for request and response validation

- [x] **WEATHER-003**: Create weather data caching strategy

  - Dependencies: WEATHER-001, CACHE-001
  - Reference: [docs/integrations/weather_mcp_implementation.md](../integrations/weather_mcp_implementation.md)
  - Status: Completed with Redis caching using appropriate TTLs

- [x] **WEATHER-004**: Implement travel recommendations based on weather data
  - Dependencies: WEATHER-002
  - Reference: [docs/integrations/weather_mcp_implementation.md](../integrations/weather_mcp_implementation.md)
  - Status: Completed with destination comparison and optimal travel time recommendations

### Web Crawling MCP Server

- [x] **WEBCRAWL-001**: Set up Crawl4AI self-hosted environment

  - Dependencies: MCP-001
  - Reference: [docs/integrations/web_crawling.md](../integrations/web_crawling.md), [docs/integrations/webcrawl_mcp_implementation.md](../integrations/webcrawl_mcp_implementation.md)
  - Status: Completed with Crawl4AI source implementation and configuration for self-hosted deployment (Issue #19)

- [x] **WEBCRAWL-002**: Create Web Crawling MCP Server structure

  - Dependencies: MCP-001, WEBCRAWL-001
  - Reference: [docs/integrations/web_crawling.md](../integrations/web_crawling.md)
  - Status: Completed with WebCrawlMCPServer implementation and tool registration

- [x] **WEBCRAWL-003**: Implement source selection strategy for different content types

  - Dependencies: WEBCRAWL-002
  - Reference: [docs/integrations/webcrawl_mcp_implementation.md](../integrations/webcrawl_mcp_implementation.md)
  - Status: Completed with intelligent source selection between Crawl4AI, Firecrawl, and Playwright

- [x] **WEBCRAWL-004**: Create page content extraction functionality

  - Dependencies: WEBCRAWL-002, WEBCRAWL-003
  - Reference: [docs/integrations/web_crawling.md](../integrations/web_crawling.md)
  - Status: Completed with extract_page_content handler in WebCrawlMCPServer

- [x] **WEBCRAWL-005**: Implement destination research capabilities

  - Dependencies: WEBCRAWL-004
  - Reference: [docs/integrations/webcrawl_mcp_implementation.md](../integrations/webcrawl_mcp_implementation.md)
  - Status: Completed with search_destination_info and crawl_travel_blog handlers in WebCrawlMCPServer

- [x] **WEBCRAWL-009**: Integrate Firecrawl API for advanced web crawling
  - Dependencies: WEBCRAWL-002, WEBCRAWL-003
  - Reference: [docs/integrations/webcrawl_mcp_implementation.md](../integrations/webcrawl_mcp_implementation.md)
  - Status: Completed with Firecrawl API integration for advanced content extraction (Issue #19)

### Browser Automation

- [x] **BROWSER-001**: Set up Playwright with Python infrastructure

  - Dependencies: MCP-001
  - Reference: [docs/integrations/browser_automation.md](../integrations/browser_automation.md)
  - Status: Completed with external Playwright MCP integration

- [x] **BROWSER-002**: Create Browser Automation Tools structure

  - Dependencies: BROWSER-001
  - Reference: [docs/integrations/browser_automation.md](../integrations/browser_automation.md)
  - Status: Completed with browser_tools.py implementation (Issue #26)

- [x] **BROWSER-003**: Implement browser MCP client integration

  - Dependencies: BROWSER-002
  - Reference: [docs/integrations/browser_automation.md](../integrations/browser_automation.md)
  - Status: Completed with PlaywrightClient and StagehandClient implementations

- [x] **BROWSER-004**: Create flight status checking functionality

  - Dependencies: BROWSER-003
  - Reference: [docs/integrations/browser_automation.md](../integrations/browser_automation.md)
  - Status: Completed with check_flight_status tool implementation in browser_tools.py

- [x] **BROWSER-005**: Implement booking verification capabilities with Pydantic v2

  - Dependencies: BROWSER-003
  - Reference: [docs/integrations/browser_automation.md](../integrations/browser_automation.md)
  - Status: Completed with Pydantic v2 validation, model validators, and Redis caching

- [x] **BROWSER-006**: Create price monitoring functionality

  - Dependencies: BROWSER-003
  - Reference: [docs/integrations/browser_automation.md](../integrations/browser_automation.md)
  - Status: Completed with monitor_price tool implementation in browser_tools.py

- [x] **BROWSER-007**: Replace custom Browser MCP with external MCPs
  - Dependencies: BROWSER-002, BROWSER-003, BROWSER-004, BROWSER-005, BROWSER-006
  - Reference: [docs/integrations/browser_automation.md](../integrations/browser_automation.md)
  - Status: Completed with Playwright MCP and Stagehand MCP integration (Issue #26)

### Flights MCP Server

- [x] **FLIGHTS-001**: Integrate ravinahp/flights-mcp server for Duffel API access

  - Dependencies: MCP-001
  - Reference: [docs/integrations/flights_mcp_implementation.md](../integrations/flights_mcp_implementation.md)
  - Status: Completed with successful integration with ravinahp/flights-mcp server (Issue #16)

- [x] **FLIGHTS-002**: Create client implementation for flights MCP

  - Dependencies: FLIGHTS-001
  - Reference: [docs/integrations/flights_mcp_implementation.md](../integrations/flights_mcp_implementation.md)
  - Status: Completed with comprehensive client implementation and proper error handling

- [x] **FLIGHTS-003**: Create flight search functionality

  - Dependencies: FLIGHTS-002
  - Reference: [docs/integrations/flights_mcp_implementation.md](../integrations/flights_mcp_implementation.md)
  - Status: Completed with search_flights and search_multi_city tools

- [x] **FLIGHTS-004**: Implement price tracking and history
  - Dependencies: FLIGHTS-003, DB-001
  - Reference: [docs/integrations/flights_mcp_implementation.md](../integrations/flights_mcp_implementation.md)
  - Status: Completed with price tracking implementation and Redis/Supabase integration

### Medium Priority

### Time MCP Integration

- [x] **TIME-001**: Integrate with official Time MCP server

  - Dependencies: MCP-001
  - Reference: [docs/integrations/time_integration.md](../integrations/time_integration.md)
  - Status: Completed with MCP client implementation for official Time MCP server

- [x] **TIME-002**: Create Time MCP client implementation

  - Dependencies: TIME-001
  - Reference: [docs/integrations/time_integration.md](../integrations/time_integration.md)
  - Status: Completed with comprehensive client implementation for official Time MCP

- [x] **TIME-003**: Develop agent function tools for time operations

  - Dependencies: TIME-002
  - Reference: [docs/integrations/time_integration.md](../integrations/time_integration.md)
  - Status: Completed with travel-specific time conversion, calculation, and timezone tools

- [x] **TIME-004**: Create deployment script for Time MCP server

  - Dependencies: TIME-001
  - Reference: [docs/integrations/time_integration.md](../integrations/time_integration.md)
  - Status: Completed with script for downloading and running the official Time MCP server

- [x] **TIME-005**: Create comprehensive tests for Time MCP client

  - Dependencies: TIME-002, TIME-003
  - Reference: [docs/integrations/time_integration.md](../integrations/time_integration.md)
  - Status: Completed with unit tests for Time MCP client functionality

### Google Maps MCP Server

- [x] **GOOGLEMAPS-001**: Integrate Google Maps MCP server

  - Dependencies: MCP-001
  - Reference: [docs/integrations/google_maps_integration.md](../integrations/google_maps_integration.md)
  - Status: Completed with integration of official Google Maps MCP server (Issue #18)

- [x] **GOOGLEMAPS-002**: Create client implementation for Google Maps MCP

  - Dependencies: GOOGLEMAPS-001
  - Reference: [googlemaps-integration-verification.md](../../googlemaps-integration-verification.md)
  - Status: Completed with client implementation for geocoding, routing, and place details

- [x] **GOOGLEMAPS-003**: Integrate Google Maps data with Memory MCP
  - Dependencies: GOOGLEMAPS-002, MEM-001
  - Reference: [docs/integrations/google_maps_integration.md](../integrations/google_maps_integration.md)
  - Status: Completed with integration of location data into Neo4j knowledge graph

### Accommodation MCP Server

- [x] **ACCOM-001**: Create Accommodation MCP Server structure

  - Dependencies: MCP-001
  - Reference: [docs/integrations/accommodations_mcp_implementation.md](../integrations/accommodations_mcp_implementation.md)
  - Status: Completed with FastMCP 2.0 integration, Airbnb providers, and factory pattern (Issue #17)

- [x] **ACCOM-002**: Implement OpenBnB Airbnb MCP integration

  - Dependencies: ACCOM-001
  - Reference: [docs/integrations/airbnb_integration.md](../integrations/airbnb_integration.md)
  - Status: Completed with OpenBnB Airbnb MCP server integration and data transformation

- [x] **ACCOM-003**: Implement dual storage for accommodation data

  - Dependencies: ACCOM-001, DB-001, MEM-001
  - Reference: [docs/integrations/accommodations_mcp_implementation.md](../integrations/accommodations_mcp_implementation.md)
  - Status: Completed with dual storage in both Supabase and Neo4j Knowledge Graph

- [x] **ACCOM-004**: Implement factory pattern for accommodation sources
  - Dependencies: ACCOM-002
  - Reference: [docs/integrations/accommodations_mcp_implementation.md](../integrations/accommodations_mcp_implementation.md)
  - Status: Completed with factory pattern to support future accommodation sources

### Calendar MCP Server

- [x] **CAL-001**: Create Calendar MCP Server structure

  - Dependencies: MCP-001
  - Reference: [docs/integrations/calendar_integration.md](../integrations/calendar_integration.md), [docs/integrations/calendar_mcp_implementation.md](../integrations/calendar_mcp_implementation.md)
  - Status: Completed with FastMCP 2.0 integration and dedicated tool handlers

- [x] **CAL-002**: Set up Google Calendar API integration

  - Dependencies: CAL-001
  - Reference: [docs/integrations/calendar_integration.md](../integrations/calendar_integration.md)
  - Status: Completed with full OAuth implementation and event creation capabilities

- [x] **CAL-003**: Implement OAuth flow for user authorization

  - Dependencies: CAL-002
  - Reference: [docs/integrations/calendar_mcp_implementation.md](../integrations/calendar_mcp_implementation.md)
  - Status: Completed with secure token storage and refresh token management

- [x] **CAL-004**: Create travel itinerary management tools
  - Dependencies: CAL-002, CAL-003
  - Reference: [docs/integrations/calendar_mcp_implementation.md](../integrations/calendar_mcp_implementation.md)
  - Status: Completed with specialized flight, accommodation, and activity handlers

### Memory MCP Server

- [x] **MEM-001**: Integrate Neo4j Memory MCP and client implementation

  - Dependencies: MCP-001, DB-002
  - Reference: [docs/integrations/memory_integration.md](../integrations/memory_integration.md)
  - Status: Completed with integration of official Neo4j Memory MCP (Issue #20)

- [x] **MEM-002**: Implement entity creation and management

  - Dependencies: MEM-001
  - Reference: [docs/integrations/memory_integration.md](../integrations/memory_integration.md)
  - Status: Completed with entity creation, observation, and management tools

- [x] **MEM-003**: Create relationship tracking capabilities

  - Dependencies: MEM-002
  - Reference: [docs/integrations/memory_integration.md](../integrations/memory_integration.md)
  - Status: Completed with relationship creation, query, and deletion capabilities

- [x] **MEM-004**: Implement cross-session memory persistence

  - Dependencies: MEM-002, MEM-003
  - Reference: [docs/integrations/memory_integration.md](../integrations/memory_integration.md)
  - Status: Completed with session start/end tracking and user preference persistence

- [x] **MEM-006**: Implement dual storage strategy

  - Dependencies: MEM-001, DB-001
  - Reference: [docs/integrations/memory_integration.md](../integrations/memory_integration.md)
  - Status: Completed with dual storage for Supabase (structured data) and Neo4j (relationships)
  
- [x] **MEM-007**: Refactor dual storage pattern to service-based architecture

  - Dependencies: MEM-006
  - Reference: [docs/implementation/dual_storage_refactoring.md](../implementation/dual_storage_refactoring.md)
  - Status: Completed with DualStorageService base class, TripStorageService implementation, and backwards compatibility

- [x] **MEM-008**: Create isolated testing pattern for dual storage services

  - Dependencies: MEM-007
  - Reference: [docs/optimization/isolated_testing.md](../optimization/isolated_testing.md)
  - Status: Completed with self-contained test modules, mock clients, and environment independence

## Agent Development

### High Priority

- [x] **AGENT-001**: Create base agent class using OpenAI Agents SDK

  - Dependencies: ENV-001, MCP-001
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Completed with BaseAgent implementation using OpenAI Agents SDK, tool registration and WebSearchTool integration

- [x] **AGENT-002**: Implement tool registration system

  - Dependencies: AGENT-001
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Completed with \_register_tool and \_register_mcp_client_tools methods in BaseAgent class

- [x] **AGENT-003**: Create MCP client integration framework

  - Dependencies: AGENT-001, AGENT-002
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Completed with \_register_mcp_client_tools methods in BaseAgent and specific implementations

- [ ] **TRAVELAGENT-001**: Implement Travel Planning Agent using OpenAI Agents SDK

  - Dependencies: AGENT-003
  - Reference: [docs/implementation/travel_agent_implementation.md](../implementation/travel_agent_implementation.md)
  - Status: Pending - This task is now part of issue #28 (Refactor Agent Orchestration using OpenAI Agents SDK)

- [x] **TRAVELAGENT-002**: Create flight search and booking capabilities

  - Dependencies: TRAVELAGENT-001, FLIGHTS-003
  - Reference: [docs/implementation/flight_search_booking_implementation.md](../implementation/flight_search_booking_implementation.md)
  - Status: Completed with comprehensive flight search and booking capabilities, including enhanced search, multi-city search, price history tracking, and booking management.

- [ ] **TRAVELAGENT-003**: Implement WebSearchTool with travel-specific domain configuration

  - Dependencies: TRAVELAGENT-001
  - Reference: [docs/integrations/hybrid_search_strategy.md](../integrations/hybrid_search_strategy.md)
  - Status: Pending - This task is now part of issue #37 (Integrate OpenAI Agents SDK WebSearchTool)

- [x] **TRAVELAGENT-004**: Create specialized search tools adapters to enhance WebSearchTool

  - Dependencies: TRAVELAGENT-003
  - Reference: [docs/integrations/hybrid_search_strategy.md](../integrations/hybrid_search_strategy.md)
  - Status: Completed with destination search and travel option comparison tools

- [ ] **TRAVELAGENT-007**: Implement advanced caching strategy for search results
  - Dependencies: TRAVELAGENT-003, TRAVELAGENT-004, CACHE-001
  - Reference: [docs/integrations/hybrid_search_strategy.md](../integrations/hybrid_search_strategy.md)
  - Status: Pending - This task is now part of issue #38 (Implement Advanced Redis-based Caching)

### Medium Priority

- [ ] **TRAVELAGENT-005**: Implement accommodation search and comparison

  - Dependencies: TRAVELAGENT-001, ACCOM-004
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)

- [x] **TRAVELAGENT-006**: Create destination research capabilities

  - Dependencies: TRAVELAGENT-001, TRAVELAGENT-004, WEBCRAWL-005
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Completed with comprehensive destination research capabilities including search, event tracking, and blog insights extraction, all with proper caching, knowledge graph integration, and fallbacks

- [ ] **BUDGETAGENT-001**: Implement Budget Planning Agent using OpenAI Agents SDK

  - Dependencies: AGENT-003, FLIGHTS-003, ACCOM-004
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Pending - This task is part of issue #28 (Refactor Agent Orchestration using OpenAI Agents SDK)

- [ ] **BUDGETAGENT-002**: Create budget optimization capabilities

  - Dependencies: BUDGETAGENT-001
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Pending - Dependent on BUDGETAGENT-001

- [ ] **BUDGETAGENT-003**: Implement price tracking and comparison

  - Dependencies: BUDGETAGENT-001, FLIGHTS-004
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Pending - Dependent on BUDGETAGENT-001

- [ ] **ITINAGENT-001**: Implement Itinerary Planning Agent using OpenAI Agents SDK

  - Dependencies: AGENT-003, CAL-001
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Pending - This task is part of issue #28 (Refactor Agent Orchestration using OpenAI Agents SDK)

- [ ] **ITINAGENT-002**: Create itinerary generation capabilities

  - Dependencies: ITINAGENT-001
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Pending - Dependent on ITINAGENT-001

- [ ] **ITINAGENT-003**: Implement calendar integration
  - Dependencies: ITINAGENT-001, CAL-004
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)
  - Status: Pending - Dependent on issue #25 (Integrate Google Calendar MCP)

## API Implementation

### High Priority

- [ ] **API-001**: Set up FastAPI application structure

  - Dependencies: ENV-001
  - Reference: [docs/api/api_integration.md](../api/api_integration.md)
  - Status: Pending - Dependent on issue #28 (OpenAI Agents SDK integration)

- [ ] **API-002**: Create authentication routes and middleware

  - Dependencies: API-001, SEC-001
  - Reference: [docs/api/api_integration.md](../api/api_integration.md)
  - Status: Pending - Dependent on API-001 and SEC-001

- [ ] **API-003**: Implement trip management routes

  - Dependencies: API-001, DB-001
  - Reference: [docs/api/api_integration.md](../api/api_integration.md)
  - Status: Pending - Dependent on issue #23 (Supabase MCP integration)

- [ ] **API-004**: Create user management routes
  - Dependencies: API-001, API-002, DB-001
  - Reference: [docs/api/api_integration.md](../api/api_integration.md)
  - Status: Pending - Dependent on API-002

### Medium Priority

- [ ] **API-005**: Implement agent interaction endpoints

  - Dependencies: API-001, TRAVELAGENT-001, BUDGETAGENT-001, ITINAGENT-001
  - Reference: [docs/api/api_integration.md](../api/api_integration.md)
  - Status: Pending - Dependent on issue #28 (Agent orchestration)

- [ ] **API-006**: Create data visualization endpoints
  - Dependencies: API-001, API-003
  - Reference: [docs/api/api_integration.md](../api/api_integration.md)
  - Status: Pending - Dependent on API-003

## Database Implementation

### High Priority

- [x] **DB-003**: Execute initial schema migrations

  - Dependencies: DB-001
  - Reference: [docs/database_setup.md](../database_setup.md)
  - Status: Completed with multi-provider support for both Supabase and Neon

- [x] **DB-004**: Set up Row Level Security (RLS) policies

  - Dependencies: DB-003
  - Reference: [docs/database/supabase_integration.md](../database/supabase_integration.md)
  - Status: Completed for Supabase with provider-specific abstractions

- [x] **DB-005**: Create knowledge graph schema
  - Dependencies: DB-002
  - Reference: [docs/integrations/memory_integration.md](../integrations/memory_integration.md)
  - Status: Completed with comprehensive Node and Relationship schemas for travel domain and project meta-knowledge

### Medium Priority

- [ ] **DB-006**: Implement data synchronization between Supabase and Neo4j

  - Dependencies: DB-003, DB-005, MEM-001
  - Reference: [docs/database/supabase_integration.md](../database/supabase_integration.md)

- [x] **DB-007**: Create database access layer

  - Dependencies: DB-003, DB-004
  - Reference: [docs/database/supabase_integration.md](../database/supabase_integration.md)
  - Status: Completed with adapter pattern supporting multiple database providers

- [x] **DB-008**: Implement connection pooling and error handling
  - Dependencies: DB-007
  - Reference: [docs/database/supabase_integration.md](../database/supabase_integration.md)
  - Status: Completed with configurable connection pooling for Neon and error handling for all providers

## Testing Implementation

### High Priority

- [x] **TEST-001**: Set up testing framework for MCP servers

  - Dependencies: MCP-001
  - Reference: [CLAUDE.md](../../CLAUDE.md)
  - Status: Completed with pytest fixtures and mock infrastructure

- [x] **TEST-002**: Implement unit tests for Weather and Time MCP services

  - Dependencies: TEST-001, WEATHER-001, TIME-001
  - Reference: [CLAUDE.md](../../CLAUDE.md)
  - Status: Completed with comprehensive tests for API clients and MCP servers

- [x] **TEST-006**: Implement unit tests for database providers

  - Dependencies: TEST-001, DB-007, DB-008
  - Reference: [CLAUDE.md](../../CLAUDE.md)
  - Status: Completed with tests for both Supabase and Neon providers

- [x] **TEST-007**: Standardize MCP client implementations and add comprehensive tests

  - Dependencies: TEST-001, MCP-001
  - Reference: [docs/status/implementation_status.md](../status/implementation_status.md)
  - Status: Completed (PR #53) with standardized Pydantic v2 validation patterns and comprehensive tests for all MCP clients including WebCrawl, Google Maps, Flights, and Memory

- [x] **TEST-008**: Create isolated testing pattern for MCP clients

  - Dependencies: TEST-001, MCP-002
  - Reference: [docs/optimization/isolated_mcp_testing.md](../optimization/isolated_mcp_testing.md)
  - Status: Completed with self-contained test modules, mock HTTP clients, and no external dependencies

- [x] **TEST-009**: Enhance testing coverage with isolated test approach
  - Dependencies: TEST-001, TEST-008
  - Reference: [docs/optimization/isolated_mcp_testing.md](../optimization/isolated_mcp_testing.md), [docs/optimization/isolated_testing.md](../optimization/isolated_testing.md)
  - Status: Completed with implementation of both isolated MCP client testing and isolated dual storage service testing patterns

### Medium Priority

- [ ] **TEST-003**: Create integration tests for agent workflows

  - Dependencies: TEST-001, TRAVELAGENT-001, BUDGETAGENT-001, ITINAGENT-001
  - Reference: [CLAUDE.md](../../CLAUDE.md)

- [ ] **TEST-004**: Implement tests for API endpoints

  - Dependencies: TEST-001, API-001, API-002, API-003, API-004
  - Reference: [CLAUDE.md](../../CLAUDE.md)

- [ ] **TEST-005**: Set up end-to-end testing
  - Dependencies: TEST-001, TEST-003, TEST-004
  - Reference: [CLAUDE.md](../../CLAUDE.md)

## Deployment Implementation

### Medium Priority

- [ ] **DEPLOY-001**: Create Docker configuration for MCP servers

  - Dependencies: WEATHER-001, WEBCRAWL-002, BROWSER-002, FLIGHTS-001, ACCOM-001, CAL-001, MEM-001
  - Reference: [docs/deployment/deployment_strategy.md](../deployment/deployment_strategy.md)

- [ ] **DEPLOY-002**: Set up Docker Compose configuration
  - Dependencies: DEPLOY-001
  - Reference: [docs/deployment/deployment_strategy.md](../deployment/deployment_strategy.md)

### Low Priority

- [ ] **DEPLOY-003**: Create Kubernetes deployment manifests

  - Dependencies: DEPLOY-001
  - Reference: [docs/deployment/deployment_strategy.md](../deployment/deployment_strategy.md)

- [ ] **DEPLOY-004**: Implement CI/CD pipeline for deployment
  - Dependencies: CI-001, TEST-002, TEST-003, TEST-004, TEST-005
  - Reference: [docs/deployment/deployment_strategy.md](../deployment/deployment_strategy.md)

## WebCrawl MCP Enhancements

### Medium Priority

- [ ] **WEBCRAWL-006**: Implement intelligent source selection based on URL characteristics

  - Dependencies: WEBCRAWL-003
  - Reference: [docs/integrations/web_crawling_evaluation.md](../integrations/web_crawling_evaluation.md)
  - Description: Enhance source selection to intelligently choose between Crawl4AI and Playwright based on URL characteristics, including domain-specific rules and dynamic content detection

- [ ] **WEBCRAWL-007**: Enhance WebSearchTool fallback with structured guidance

  - Dependencies: WEBCRAWL-005, TRAVELAGENT-003
  - Reference: [docs/integrations/hybrid_search_strategy.md](../integrations/hybrid_search_strategy.md)
  - Description: Provide more structured guidance when falling back to WebSearchTool, including specific query patterns and expected information structure

- [x] **MEM-005**: Expand knowledge graph with additional entity and relation types

  - Dependencies: MEM-002, MEM-003
  - Reference: [docs/integrations/memory_integration.md](../integrations/memory_integration.md)
  - Description: Create more entity types beyond destinations (attractions, events, etc.) and implement more relation types between entities (located_in, offers, etc.)
  - Status: Completed with full implementation of Activity, Accommodation, Event, and Transportation entity types with repositories, relationship tracking, and comprehensive integration tests

- [ ] **WEBCRAWL-008**: Implement result normalization across sources

  - Dependencies: WEBCRAWL-003, WEBCRAWL-005
  - Reference: [docs/integrations/webcrawl_mcp_implementation.md](../integrations/webcrawl_mcp_implementation.md)
  - Description: Normalize data structures from different sources with consistent format, confidence scores, and source metadata

- [ ] **CACHE-002**: Enhance caching with partial updates and cache warming

  - Dependencies: CACHE-001, WEBCRAWL-003
  - Reference: [docs/optimization/search_and_caching_strategy.md](../optimization/search_and_caching_strategy.md)
  - Description: Implement partial cache updates for time-sensitive data, add cache warming for popular destinations, and implement cache statistics collection

## Post-MVP Enhancements

### Low Priority

- [ ] **VECTOR-001**: Set up Qdrant integration for vector search

  - Dependencies: DB-001, DB-003
  - Reference: [docs/optimization/tripsage_optimization_strategy.md](../optimization/tripsage_optimization_strategy.md)

- [ ] **VECTOR-002**: Implement embedding generation pipeline

  - Dependencies: VECTOR-001
  - Reference: [docs/optimization/tripsage_optimization_strategy.md](../optimization/tripsage_optimization_strategy.md)

- [ ] **VECTOR-003**: Create semantic search capabilities

  - Dependencies: VECTOR-001, VECTOR-002
  - Reference: [docs/optimization/tripsage_optimization_strategy.md](../optimization/tripsage_optimization_strategy.md)

- [ ] **AI-001**: Implement personalized recommendations

  - Dependencies: TRAVELAGENT-001, MEM-004
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)

- [ ] **AI-002**: Create trip optimization algorithms
  - Dependencies: TRAVELAGENT-001, BUDGETAGENT-001
  - Reference: [docs/optimization/agent_optimization.md](../optimization/agent_optimization.md)

## Implementation Timeline

### Weeks 1-2: Foundation

| Week | Day | Tasks                                                                               |
| ---- | --- | ----------------------------------------------------------------------------------- |
| 1    | 1-2 | ✅ ENV-001, ✅ ENV-002, ✅ MCP-001, ✅ UTIL-001                                     |
| 1    | 3-5 | ✅ DB-001, ✅ DB-002, ✅ DB-003, ✅ DB-004, ✅ DB-005, ✅ DB-007, ✅ DB-008         |
| 2    | 1-3 | ✅ WEATHER-001, ✅ WEATHER-002, ✅ WEATHER-003, ✅ WEATHER-004                      |
| 2    | 3-5 | ✅ WEBCRAWL-001, ✅ WEBCRAWL-002, ✅ WEBCRAWL-003, ✅ WEBCRAWL-004, ✅ WEBCRAWL-005 |

### Weeks 3-4: Travel Services

| Week | Day | Tasks                                                                                          |
| ---- | --- | ---------------------------------------------------------------------------------------------- |
| 3    | 1-3 | ✅ BROWSER-001, ✅ BROWSER-002, ✅ BROWSER-003, ✅ BROWSER-004, ✅ BROWSER-005, ✅ BROWSER-006 |
| 3    | 3-5 | ✅ FLIGHTS-001, ✅ FLIGHTS-002, ✅ FLIGHTS-003, ✅ FLIGHTS-004                                 |
| 4    | 1-3 | ✅ ACCOM-001, ✅ ACCOM-002, ✅ ACCOM-003, ✅ ACCOM-004                                         |
| 4    | 3-5 | ✅ AGENT-001, ✅ AGENT-002, ✅ AGENT-003, TRAVELAGENT-001, TRAVELAGENT-002, ✅ TRAVELAGENT-007 |

### Weeks 5-6: Context and Personalization

| Week | Day | Tasks                                                                                                           |
| ---- | --- | --------------------------------------------------------------------------------------------------------------- |
| 5    | 1-3 | ✅ TIME-001, ✅ TIME-002, ✅ TIME-003, ✅ TIME-004, ✅ TIME-005, ✅ CAL-001, ✅ CAL-002, ✅ CAL-003, ✅ CAL-004 |
| 5    | 3-5 | ✅ MEM-001, ✅ MEM-002, ✅ MEM-003, ✅ MEM-004, ✅ MEM-005                                                      |
| 6    | 1-3 | BUDGETAGENT-001, BUDGETAGENT-002, BUDGETAGENT-003                                                               |
| 6    | 3-5 | ITINAGENT-001, ITINAGENT-002, ITINAGENT-003                                                                     |

### Weeks 7-8: Integration and Production

| Week | Day | Tasks                                                                                                 |
| ---- | --- | ----------------------------------------------------------------------------------------------------- |
| 7    | 1-3 | API-001, API-002, API-003, API-004, API-005                                                           |
| 7    | 3-5 | ✅ TEST-001, ✅ TEST-002, ✅ TEST-006, ✅ TEST-007, ✅ TEST-008, ✅ TEST-009, TEST-003, TEST-004       |
| 8    | 1-3 | TEST-005, DEPLOY-001, DEPLOY-002                                                                      |
| 8    | 3-5 | DEPLOY-003, DEPLOY-004, Final Testing and Review                                                      |

### Current Priority Tasks Based on Open Issues

| Priority | Task ID         | Description                                                     | Issue   | Status                                    |
| -------- | --------------- | --------------------------------------------------------------- | ------- | ----------------------------------------- |
| 1        | AGENT-004       | Refactor Agent Orchestration using OpenAI Agents SDK            | #28     | In Progress                               |
| 2        | CACHE-002       | Implement Advanced Redis-based Caching for Web Operations       | #38     | Pending                                   |
| 3        | SEARCH-001      | Integrate OpenAI Agents SDK WebSearchTool for General Queries   | #37     | Pending                                   |
| 4        | TEST-001        | Standardize and Expand Test Suite (Target 90%+ Coverage)        | #35     | In Progress - MCP-003, MEM-008, and comprehensive MCP abstraction tests completed |
| 5        | CI-001          | Implement CI Pipeline with Linting, Type Checking, and Coverage | #36     | Pending                                   |
| 6        | DB-PROD-001     | Integrate Supabase MCP Server for Production Database           | #23     | In Progress - Foundation laid with PR #53 |
| 7        | DB-DEV-001      | Integrate Neon DB MCP Server for Development Environments       | #22     | In Progress - Foundation laid with PR #53 |
| 8        | CAL-001         | Integrate Google Calendar MCP for Itinerary Scheduling          | #25     | Pending                                   |
| 9        | WEBCRAWL-007    | Enhance WebSearchTool fallback with structured guidance         | #37     | Pending                                   |
| 10       | WEBCRAWL-008    | Implement result normalization across sources                   | #38     | Pending                                   |
| 11       | BUDGETAGENT-001 | Implement Budget Planning Agent                                 | #28     | Pending                                   |
| 12       | ITINAGENT-001   | Implement Itinerary Planning Agent                              | #28     | Pending                                   |
| 13       | VECTOR-001      | Integrate Qdrant for semantic search (Post-MVP)                 | #41, #2 | Post-MVP                                  |

### Post-MVP: Enhanced Capabilities

| Priority | Task ID    | Description                                 | Issue   | Status  |
| -------- | ---------- | ------------------------------------------- | ------- | ------- |
| 1        | VECTOR-001 | Set up Qdrant integration for vector search | #41, #2 | Planned |
| 2        | VECTOR-002 | Implement embedding generation pipeline     | #41, #2 | Planned |
| 3        | VECTOR-003 | Create semantic search capabilities         | #41, #2 | Planned |
| 4        | AI-001     | Implement personalized recommendations      | -       | Planned |
| 5        | AI-002     | Create trip optimization algorithms         | -       | Planned |
````

## File: optimization/tripsage_optimization_strategy.md

````markdown
# TripSage Optimization Strategy

Version: 1.0.1 - Last Updated: May 10, 2025

## 1. Executive Summary

TripSage is an AI-powered travel planning system that seamlessly integrates flight, accommodation, and location data from multiple sources while storing search results in a dual-storage architecture (Supabase + knowledge graph memory). This document presents a comprehensive optimization strategy that consolidates architecture decisions, technology selections, and implementation plans.

Key strategic decisions include:

1. **Standardizing on Python FastMCP 2.0** for all custom MCP servers
2. **Using official MCP implementations** for Time MCP and Neo4j integration
3. **Implementing six specialized MCP servers** for weather, web crawling, flights, accommodations, calendar, and memory
4. **Maintaining a dual-storage architecture** with Supabase and Neo4j
5. **Planning for Qdrant vector database** integration as a post-MVP enhancement
6. **Adopting a hybrid database approach** with Supabase for production and Neon for development
7. **Implementing a multi-tiered caching strategy** with Redis

This optimization strategy provides a clear roadmap for implementing the TripSage travel planning system over an 8-week timeline, with a focus on rapid development, maintainability, and scalability.

## 2. System Architecture

### 2.1 High-Level Architecture

```plaintext
┌─────────────────────────────────────────────────────────────────────┐
│                     TripSage Orchestration Layer                     │
├─────────┬─────────┬─────────┬──────────┬──────────┬─────────────────┤
│ Weather │  Web    │ Flights │Accommoda-│ Calendar │    Memory       │
│   MCP   │ Crawl   │   MCP   │tion MCP  │   MCP    │     MCP         │
│ Server  │ MCP     │ Server  │ Server   │  Server  │    Server       │
│         │ Server  │         │          │          │                 │
├─────────┴─────────┴─────────┴──────────┴──────────┼─────────────────┤
│                    Integration & Abstraction Layer │  Vector Search  │
├─────────────────────────────────────────────────────────────────────┤
│                     OpenAI Agents SDK Adapters                       │
├─────────────────────────────────────────────────────────────────────┤
│                       Agent Implementation                           │
├───────────────────┬───────────────────────┬─────────────────────────┤
│  Travel Planning  │   Budget Planning     │  Itinerary Planning     │
│       Agent       │       Agent           │        Agent            │
├───────────────────┴───────────────────────┴─────────────────────────┤
│                        FastAPI Backend                               │
├─────────────────────────────────────────────────────────────────────┤
│                      Supabase Database                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Overview

TripSage's architecture consists of four main layers:

1. **MCP Server Layer**:

   - Six specialized MCP servers built with Python FastMCP 2.0
   - Official MCP implementations for Time and Neo4j Memory
   - Custom implementations for travel-specific services

2. **Integration & Abstraction Layer**:

   - Unified interfaces to all MCP servers
   - Authentication and authorization
   - Error handling and resilience
   - Caching and performance optimization

3. **Agent Layer**:

   - OpenAI Agents SDK integration
   - Specialized agents for travel planning, budget optimization, and itinerary creation
   - Function tools mapping to MCP server capabilities

4. **Storage Layer**:
   - Supabase for relational data (production)
   - Neon for relational data (development)
   - Neo4j for knowledge graph storage
   - Qdrant for vector search (planned post-MVP)

### 2.3 Dual Storage Approach

TripSage implements a dual-storage architecture:

1. **Relational Database (Supabase/Neon)**:

   - Core travel data (flights, accommodations, itineraries)
   - User information and preferences
   - Transaction records and booking details
   - Search results and cached data

2. **Knowledge Graph (Neo4j)**:
   - Travel entity relationships (locations, flights, accommodations)
   - User preferences and history
   - Context preservation across sessions
   - Semantic connections between travel concepts

This dual-storage approach provides both structured data management and rich semantic relationships, enabling powerful queries and recommendations.

### 2.4 Future Vector Search Integration (Qdrant)

After the MVP is complete, Qdrant will be integrated to provide enhanced semantic search capabilities:

- Vector embeddings of destinations, accommodations, and activities
- HNSW algorithm with cosine similarity for efficient searching
- Integration via Python SDK with async support
- Use cases including similar destination search, preference matching, and semantic recommendations

## 3. MCP Technology Stack

### 3.1 Framework Selection: Python FastMCP 2.0

After thorough evaluation, we have selected **Python FastMCP 2.0** as the framework for all custom MCP servers, replacing the previously considered TypeScript/JavaScript implementation.

| Aspect          | FastMCP 2.0 (Python)               | FastMCP (TypeScript)       | Advantage       |
| --------------- | ---------------------------------- | -------------------------- | --------------- |
| Development     | Active, growing ecosystem          | Less active                | Python          |
| Code Simplicity | High (decorator-based API)         | Moderate                   | Python          |
| Features        | Server+client, OpenAPI integration | Basic server functionality | Python          |
| Integration     | Strong with data science ecosystem | Standard web stack         | Depends on team |
| Maintenance     | Simpler code, fewer lines          | More verbose               | Python          |

**Rationale for Python FastMCP 2.0**:

1. **Reduced development time** through decorator-based API and less boilerplate
2. **Better OpenAPI integration** for rapid connection to travel APIs
3. **More active development** than the TypeScript variant
4. **Client and server capabilities** in a single framework
5. **Compatibility** with data science and AI ecosystems

### 3.2 Official MCP Implementations

We will adopt official MCP implementations where available:

| Component    | Current Plan                 | Recommendation              | Rationale                                              |
| ------------ | ---------------------------- | --------------------------- | ------------------------------------------------------ |
| Time MCP     | Custom TypeScript server     | Official Time MCP           | Standardized functionality, reduced development effort |
| Neo4j Memory | Custom Memory MCP with Neo4j | Official `mcp-neo4j-memory` | Standard implementation, better maintained             |

### 3.3 Database Technology Selection

| Database | Purpose                            | Environment         | Rationale                                                     |
| -------- | ---------------------------------- | ------------------- | ------------------------------------------------------------- |
| Supabase | Relational storage, authentication | Production          | Better RLS tools, integrated services, cold start performance |
| Neon     | Development database               | Development/Testing | Superior branching capabilities, unlimited free projects      |
| Neo4j    | Knowledge graph                    | All                 | Mature graph database with official MCP integration           |
| Redis    | Caching, rate limiting             | All                 | High-performance, TTL support, widely adopted                 |
| Qdrant   | Vector search (post-MVP)           | Production          | Production-ready, horizontal scaling, rich filtering          |

**Hybrid database approach benefits**:

1. **Development efficiency**: Neon's unlimited free projects and branching for developers
2. **Production reliability**: Supabase's integrated services and stable cold start performance
3. **Consistent schema**: Common schema definition across both platforms
4. **Streamlined CI/CD**: Database branching tied to git workflow

## 4. MCP Server Implementation

### 4.1 Weather MCP Server

- **Purpose**: Provide weather data for travel destinations
- **API Integration**: OpenWeatherMap (primary), Visual Crossing (secondary), Weather.gov (US locations)
- **Implementation**: Python FastMCP 2.0 with OpenAPI integration
- **Tools**:
  - `mcp__weather__get_current_conditions`: Current weather for a location
  - `mcp__weather__get_forecast`: Multi-day forecast with travel recommendations
  - `mcp__weather__get_historical_data`: Historical weather patterns for planning
  - `mcp__weather__get_travel_recommendation`: Weather-based travel suggestions
  - `mcp__weather__get_extreme_alerts`: Weather alerts for a location and date range

**Implementation Example**:

```python
# Example using Python FastMCP 2.0
from fastmcp import FastMCP, Tool
from typing import List, Optional
from pydantic import BaseModel

# Define data models
class WeatherCondition(BaseModel):
    temperature: float
    feels_like: float
    description: str
    humidity: int
    wind_speed: float

class LocationWeather(BaseModel):
    location: str
    country: str
    current: WeatherCondition
    forecast: List[WeatherCondition]
    travel_advice: List[str]

# Create MCP server
app = FastMCP()

@app.tool()
async def get_current_conditions(location: str, units: str = "metric") -> LocationWeather:
    """Get current weather for a travel destination"""
    # Implementation using OpenWeatherMap API
    # ...

@app.tool()
async def get_travel_recommendation(
    location: str,
    start_date: str,
    end_date: str,
    activities: Optional[List[str]] = None
) -> dict:
    """Get weather-based travel recommendations for a destination"""
    # Implementation logic
    # ...

# Start the server
if __name__ == "__main__":
    app.serve()
```

### 4.2 Web Crawling MCP Server

- **Purpose**: Facilitate destination research and content extraction
- **API Integration**:
  - Primary: Crawl4AI (self-hosted, high performance)
  - Secondary: Firecrawl API (native MCP support)
  - Tertiary: Enhanced Playwright for dynamic content and interactive tasks
- **Implementation**: Python FastMCP 2.0 with extensive source abstractions
- **Tools**:
  - `mcp__webcrawl__extract_page_content`: Extract content from travel websites
  - `mcp__webcrawl__search_destination_info`: Search for destination information
  - `mcp__webcrawl__monitor_price_changes`: Monitor price changes on websites
  - `mcp__webcrawl__get_latest_events`: Discover events at a destination
  - `mcp__webcrawl__crawl_travel_blog`: Extract insights from travel blogs

**Implementation Example**:

```python
# Example using Python FastMCP 2.0
from fastmcp import FastMCP
from typing import List, Optional, Dict
from pydantic import BaseModel

# Define data models
class ExtractContentRequest(BaseModel):
    url: str
    selectors: Optional[Dict[str, str]] = None
    include_images: bool = False
    format: str = "markdown"

class ExtractedContent(BaseModel):
    url: str
    title: str
    content: str
    images: Optional[List[str]] = None
    metadata: Optional[Dict[str, str]] = None
    format: str

# Create MCP server
app = FastMCP()

@app.tool()
async def extract_page_content(params: ExtractContentRequest) -> ExtractedContent:
    """Extract content from a travel webpage"""
    # Select appropriate source based on URL and content type
    if is_dynamic_content_site(params.url):
        # Use Enhanced Playwright for dynamic JavaScript-heavy sites
        return await extract_with_playwright(params.url, params)
    else:
        # Use Crawl4AI as the primary extraction engine
        try:
            return await extract_with_crawl4ai(params.url, params)
        except Exception as e:
            # Fall back to Firecrawl if Crawl4AI fails
            logger.warning(f"Crawl4AI extraction failed, falling back to Firecrawl: {str(e)}")
            return await extract_with_firecrawl(params.url, params)

@app.tool()
async def search_destination_info(
    destination: str,
    topics: Optional[List[str]] = None,
    max_results: int = 5
) -> Dict:
    """Search for specific information about a travel destination"""
    # Implement batch processing with Crawl4AI for efficient parallel searches
    search_topics = topics or ["attractions", "local cuisine", "transportation", "best time to visit"]

    # Create batch search request
    batch_results = await crawl4ai_client.batch_search(
        destination=destination,
        topics=search_topics,
        max_results=max_results
    )

    # Process and normalize results
    return format_destination_search_results(batch_results)

# Start the server
if __name__ == "__main__":
    app.serve()
```

### 4.3 Flights MCP Server

- **Purpose**: Handle flight search, details, tracking, and booking
- **API Integration**: Duffel API via OpenAPI specification
- **Implementation**: Python FastMCP 2.0 with OpenAPI integration
- **Tools**:
  - `search_flights`: Find flights based on origin, destination, and dates
  - `get_flight_details`: Retrieve detailed information about specific flights
  - `track_flight_prices`: Monitor price changes for specific routes
  - `create_flight_booking`: Create reservation with passenger details

**Implementation Example**:

```python
from fastmcp import FastMCP
from fastmcp.openapi import create_mcp_from_openapi

# Create MCP server from OpenAPI spec
app = FastMCP()

# Add tools from Duffel API OpenAPI spec
create_mcp_from_openapi(
    app,
    openapi_url="https://api.duffel.com/openapi/v1.json",
    base_url="https://api.duffel.com/v1",
    headers={"Authorization": "Bearer {{DUFFEL_API_KEY}}"}
)

# Add custom tools
@app.tool()
async def track_flight_prices(
    origin: str, 
    destination: str, 
    departure_date: str, 
    return_date: Optional[str] = None
) -> dict:
    """Track price changes for flights between two locations"""
    # Implementation logic
    # ...

# Start the server
if __name__ == "__main__":
    app.serve()
```

### 4.4 Accommodation MCP Server

- **Purpose**: Manage accommodation search, details, comparison, and reviews
- **API Integration**: OpenBnB, Apify Booking.com Scraper
- **Implementation**: Python FastMCP 2.0 with custom mappings
- **Tools**:
  - `search_accommodations`: Find lodging based on location and dates
  - `get_accommodation_details`: Retrieve detailed property information
  - `compare_accommodations`: Compare multiple properties
  - `get_accommodation_reviews`: Retrieve reviews for specific properties

### 4.5 Calendar MCP Server

- **Purpose**: Facilitate calendar integration for travel planning
- **API Integration**: Google Calendar API
- **Implementation**: Python FastMCP 2.0 with explicit OAuth flow
- **Tools**:
  - `get_auth_url`: Generate authorization URL for Google Calendar access
  - `add_flight_to_calendar`: Add flight information to calendar
  - `create_travel_itinerary`: Create comprehensive itinerary events
  - `export_trip_to_calendar`: Export entire trip to calendar

### 4.6 Memory MCP Server

- **Purpose**: Manage knowledge graph for travel entities and relationships
- **API Integration**: Neo4j via official `mcp-neo4j-memory`
- **Implementation**: Direct integration with existing Neo4j MCP
- **Tools**:
  - `create_entities`: Add travel entities to knowledge graph
  - `create_relations`: Establish relationships between entities
  - `read_graph`: Query the knowledge graph
  - `search_nodes`: Find relevant travel entities
  - `add_observations`: Enhance entities with new information

## 5. Database Strategy

### 5.1 Hybrid Approach

TripSage implements a hybrid database approach:

#### Supabase (Production)

- Production database environment
- Integrated authentication and storage
- Row-Level Security (RLS) for multi-tenant data
- Reliable cold-start behavior for production usage

#### Neon (Development)

- Development, testing, and preview environments
- Unlimited free database branches
- Instant database cloning for developer environments
- Database branching tied to git workflow

#### Key comparison factors

| Feature             | Supabase                 | Neon                    | Best for        |
| ------------------- | ------------------------ | ----------------------- | --------------- |
| Free Tier Projects  | 2 max                    | Unlimited               | Neon (dev)      |
| Branching           | Paid tier only           | Native on free tier     | Neon (dev)      |
| Cold Start          | 7-day inactivity         | 5-minute inactivity     | Supabase (prod) |
| Row Level Security  | Extensive UI tools       | Standard PostgreSQL     | Supabase (prod) |
| Integrated Services | Auth, Storage, Functions | Database only           | Supabase (prod) |
| Database Forks      | Less mature              | Instant copy-on-write   | Neon (dev)      |
| Documentation       | Comprehensive            | Good but less extensive | Supabase (prod) |
| Community           | Larger                   | Growing                 | Supabase (both) |

### 5.2 Integration Strategy

- Common schema definition across both platforms
- Abstraction layer to handle provider-specific features
- Migration scripts compatible with both systems
- CI/CD integration leveraging Neon's branching capabilities

### 5.3 Schema Design

The database schema follows these principles:

- Use snake_case for all tables and columns (PostgreSQL standard)
- Tables in lowercase with underscores separating words
- Foreign keys using singular form of referenced table with _id suffix
- Include created_at and updated_at timestamps on all tables
- Add appropriate comments to tables and complex columns

Core tables include:

- trips
- flights
- accommodations
- transportation
- itinerary_items
- users
- search_parameters
- price_history
- trip_notes
- saved_options
- trip_comparison

## 6. Agent Optimization

### 6.1 Agent Prompt Optimization

#### Key Principles

- **Structured Knowledge** - Provide agent with clear travel domain structure
- **Context Window Management** - Minimize token usage through progressive disclosure
- **Specific Instructions** - Use precise language for expected outputs and reasoning
- **Tool Calling Guidance** - Explicit instructions for when/how to call APIs

#### Recommended Prompt Structure

```plaintext
You are TripSage, an AI travel assistant specializing in comprehensive trip planning.

CAPABILITIES:
- Search and book flights using Duffel API
- Find accommodations through OpenBnB (Airbnb data) and Apify (Booking.com)
- Locate attractions and restaurants via Google Maps Platform
- Access real-time travel information through web search

INTERACTION GUIDELINES:
1. Always gather key trip parameters first (dates, destination, budget, preferences)
2. Use appropriate API calls based on the user's query stage:
   - Initial planning: Use lightweight search APIs first
   - Specific requests: Use specialized booking APIs
3. Present options clearly with price, ratings, and key features
4. Maintain state between interactions to avoid repeating information
5. Offer recommendations based on user preferences and constraints

When calling tools:
- For flights: Always include departure/arrival cities, dates, and class
- For accommodations: Include location, dates, guests, and price range
- For attractions: Include location and search radius
- For restaurants: Include cuisine preferences and dietary restrictions

IMPORTANT: Handle API errors gracefully. If data is unavailable, explain why and suggest alternatives.
```

### 6.2 MCP Server Orchestration

Implement a centralized MCP orchestration layer to abstract API complexity:

```javascript
class MCPOrchestrator {
  constructor(config) {
    this.servers = {};
    this.initializeServers(config);
  }

  async initializeServers(config) {
    // Initialize MCP servers based on configuration
    for (const [name, serverConfig] of Object.entries(config.servers)) {
      this.servers[name] = new MCPServer(serverConfig);
      await this.servers[name].initialize();
    }
  }

  async routeRequest(toolName, params) {
    // Determine appropriate server and route request
    const serverName = this.mapToolToServer(toolName);
    return this.servers[serverName].callTool(toolName, params);
  }

  mapToolToServer(toolName) {
    // Map tool names to server names
    const mapping = {
      search_flights: "duffel",
      search_accommodations: "openbnb",
      search_booking: "apify",
      search_location: "google_maps",
      // Add more mappings as needed
    };
    return mapping[toolName] || "default";
  }
}
```

### 6.3 API Response Normalization

Create unified data models for core travel entities:

```typescript
// Flight data model
interface Flight {
  id: string;
  carrier: {
    code: string;
    name: string;
    logo_url?: string;
  };
  departure: {
    airport: string;
    terminal?: string;
    time: string; // ISO format
  };
  arrival: {
    airport: string;
    terminal?: string;
    time: string; // ISO format
  };
  duration: number; // minutes
  price: {
    amount: number;
    currency: string;
  };
  cabin_class: string;
  stops: number;
  source: string; // API source identifier
}

// Accommodation data model
interface Accommodation {
  id: string;
  name: string;
  type: string; // hotel, apartment, house, etc.
  location: {
    address: string;
    coordinates: {
      lat: number;
      lng: number;
    };
  };
  price: {
    amount: number;
    currency: string;
    per_night: boolean;
  };
  rating?: number;
  amenities: string[];
  images: string[];
  source: string; // API source identifier
}
```

### 6.4 Hybrid Search Approach

Implement a hybrid search that leverages both specialized APIs and web search:

```javascript
async function hybridSearch(query, searchType = "auto") {
  // Analyze query intent to determine search type
  const searchIntent = await analyzeSearchIntent(query);

  // Determine which search to use based on intent and type
  if (
    searchType === "specific" ||
    searchIntent.includes("specific_fact") ||
    searchIntent.includes("location_details")
  ) {
    return await linkupSearch(query, "deep");
  } else {
    // Use built-in search for general queries
    return await openAIBuiltInSearch(query);
  }
}
```

**Decision Matrix for Search Method**:

| Query Type               | Example                                   | Recommended Method |
| ------------------------ | ----------------------------------------- | ------------------ |
| General travel knowledge | "Best time to visit Barcelona"            | OpenAI built-in    |
| Specific details         | "Current entry requirements for Japan"    | Linkup (deep)      |
| Pricing comparisons      | "Average hotel prices in Manhattan"       | Linkup (standard)  |
| Subjective advice        | "Is Barcelona or Madrid better for food?" | OpenAI built-in    |
| Time-sensitive info      | "Current flight delays at JFK"            | Linkup (deep)      |

## 7. Search and Caching Strategy

### 7.1 Multi-Tiered Caching Architecture

TripSage implements a Redis-based multi-tiered caching strategy:

1. **CDN Cache (Edge)**:

   - Caches static assets and public content
   - Geographic distribution for reduced latency
   - Typical TTL: 24 hours for static content

2. **Application Cache (Redis)**:

   - Caches search results, API responses, and computed data
   - Distributed across multiple regions
   - Configurable TTL based on data volatility
   - Supports complex data structures and query patterns

3. **Database Query Cache**:

   - Caches frequent database queries
   - Uses Supabase's built-in caching capabilities
   - Automatically invalidated on data changes

4. **Client-Side Cache (Browser/App)**:
   - Caches user preferences and recent searches
   - Leverages service workers for offline capability
   - Implements stale-while-revalidate pattern for responsiveness

### 7.2 Redis Implementation

Redis serves as the core caching engine with TTL-based expiration:

```typescript
// Redis client configuration
import { createClient } from "redis";

export const redisClient = createClient({
  url: process.env.REDIS_URL,
  // Enable TLS for production
  socket: {
    tls: process.env.NODE_ENV === "production",
    rejectUnauthorized: process.env.NODE_ENV === "production",
  },
  // Default TTL 30 minutes
  defaultTTL: 1800,
});
```

### 7.3 Caching Strategy by Data Type

| Data Type             | TTL Duration   | Caching Pattern          | Invalidation Strategy            |
| --------------------- | -------------- | ------------------------ | -------------------------------- |
| Flight search results | 10-15 minutes  | Query-based key          | TTL + price change events        |
| Hotel search results  | 30-60 minutes  | Query-based key          | TTL + availability change events |
| Location data         | 24+ hours      | Hierarchical keys        | TTL only                         |
| Weather data          | 30 minutes     | Location-based key       | TTL only                         |
| Travel advisories     | 6 hours        | Country-based key        | TTL + manual invalidation        |
| User preferences      | Session/7 days | User-based key           | User action events               |
| Price history         | 30+ days       | Entity + time-based keys | Append-only, no invalidation     |

### 7.4 API Rate Limiting

Implement Redis-based rate limiting for external API management:

```typescript
export class ApiRateLimiter {
  constructor(
    private redisClient: ReturnType<typeof createClient>,
    private config: {
      defaultLimit: number;
      defaultWindow: number; // seconds
      endpointLimits?: Record<string, { limit: number; window: number }>;
    }
  ) {}

  public async checkLimit(
    apiKey: string,
    endpoint: string
  ): Promise<{ allowed: boolean; remaining: number; reset: number }> {
    const { limit, window } = this.getLimitConfig(endpoint);
    const key = `ratelimit:${apiKey}:${endpoint}`;
    const now = Math.floor(Date.now() / 1000);
    const windowStart = now - window;

    // Remove expired tokens
    await this.redisClient.zRemRangeByScore(key, 0, windowStart);

    // Count remaining tokens
    const tokenCount = await this.redisClient.zCard(key);
    const remaining = Math.max(0, limit - tokenCount);
    const allowed = remaining > 0;

    // Add current request if allowed
    if (allowed) {
      await this.redisClient.zAdd(key, [{ score: now, value: now.toString() }]);
      await this.redisClient.expire(key, window * 2); // Set expiry
    }

    // Calculate reset time
    const oldestToken =
      tokenCount > 0
        ? (await this.redisClient.zRange(key, 0, 0, { WITHSCORES: true }))[0]
            .score
        : now;
    const reset = Math.max(now, Number(oldestToken) + window);

    return { allowed, remaining: allowed ? remaining - 1 : remaining, reset };
  }

  private getLimitConfig(endpoint: string): { limit: number; window: number } {
    return (
      this.config.endpointLimits?.[endpoint] || {
        limit: this.config.defaultLimit,
        window: this.config.defaultWindow,
      }
    );
  }
}
```

## 8. Implementation Plan

### 8.1 Phased Approach

| Phase                      | Timeline  | Focus                                  | Key Deliverables                                                     |
| -------------------------- | --------- | -------------------------------------- | -------------------------------------------------------------------- |
| 1: Foundation              | Weeks 1-2 | Infrastructure & Weather/Crawling MCPs | Python FastMCP 2.0 setup, Weather & Web Crawling MCPs                |
| 2: Travel Services         | Weeks 3-4 | Flight & Accommodation MCPs            | Flight search/booking, Accommodation search with vector capabilities |
| 3: Personal Data           | Weeks 5-6 | Calendar & Neo4j Integration           | Calendar integration, Knowledge graph implementation                 |
| 4: Finalization            | Weeks 7-8 | Testing & Production Readiness         | Performance optimization, Documentation, Deployment pipeline         |
| Future: Vector Enhancement | Post-MVP  | Qdrant Implementation                  | Semantic search capabilities, Vector-based recommendations           |

### 8.2 Detailed Timeline

#### Week 1: Core Infrastructure

- Set up Neo4j Memory MCP Server
- Configure Time MCP Server
- Establish database abstraction layer for Supabase/Neon
- Implement authentication integration
- Create MCP client foundation

#### Week 2: Knowledge Graph & Weather

- Complete Neo4j Memory integration
- Implement Weather MCP server with FastMCP 2.0
- Define core travel entity types in knowledge graph
- Create data synchronization between SQL and graph databases
- Implement basic agent integration

#### Week 3: Flight Service Implementation

- Implement Flights MCP server with Duffel API
- Create flight search and comparison tools
- Develop price tracking system
- Integrate with knowledge graph for flight relationships
- Build agent tools for flight search

#### Week 4: Accommodation Service Implementation

- Integrate Official AirBnB MCP Server
- Implement custom Booking.com adapter
- Create unified accommodation search interface
- Develop accommodation comparison tools
- Build agent tools for accommodation search

#### Week 5: Calendar Integration

- Implement Calendar MCP server (custom wrapper)
- Set up OAuth flow for calendar authorization
- Create itinerary export capabilities
- Develop trip visualization tools
- Implement travel event management

#### Week 6: Web Crawling Integration

- Deploy self-hosted Crawl4AI environment
- Implement Web Crawling MCP Server with Crawl4AI as primary engine
- Configure Enhanced Playwright for dynamic content
- Develop source selection strategy and fallback mechanisms
- Create batch processing for efficient parallel extractions
- Implement destination research and content extraction capabilities

#### Week 7: Integration & Optimization

- Develop orchestration layer for coordinating MCP services
- Implement unified query planning
- Create caching strategy for performance
- Optimize database queries and access patterns
- Implement error handling and failover mechanisms

#### Week 8: Testing & Deployment

- Comprehensive end-to-end testing
- Performance optimization
- Security review and hardening
- Documentation finalization
- Production deployment preparation

### 8.3 Resource Requirements

- **Development Resources**:

  - 2-3 developers with Python experience
  - 1 developer with Neo4j expertise
  - 1 developer familiar with OpenAI Assistants SDK

- **Infrastructure**:

  - Neo4j instance (Aura or self-hosted)
  - Supabase production project
  - Neon development projects
  - API keys for all integrated services

- **Testing Resources**:
  - Test accounts for all integrated services
  - Test data for various scenarios
  - Automated testing framework

### 8.4 Risk Assessment

| Risk                   | Probability | Impact | Mitigation                                                             |
| ---------------------- | ----------- | ------ | ---------------------------------------------------------------------- |
| MCP server API changes | Medium      | High   | Version locking, abstraction layers, regular compatibility testing     |
| API rate limiting      | High        | Medium | Implement caching, rate limiting, and retry mechanisms                 |
| Integration complexity | Medium      | High   | Follow phased approach, create comprehensive tests                     |
| Performance issues     | Medium      | High   | Monitor performance, optimize critical paths                           |
| Security concerns      | Low         | High   | Follow security best practices, implement proper authentication        |
| Data consistency       | Medium      | Medium | Implement validation and synchronization mechanisms                    |
| Neo4j licensing costs  | Medium      | Medium | Carefully plan usage tiers, consider community edition for development |

## 9. Testing and Monitoring

### 9.1 Performance Metrics

TripSage tracks these key performance metrics:

1. **Response Times**:

   - API endpoint response times
   - End-to-end request processing times
   - MCP server response times

2. **Cache Effectiveness**:

   - Cache hit/miss ratios
   - Cache invalidation frequency
   - Memory utilization

3. **API Usage**:

   - Rate limit utilization
   - Request counts by endpoint
   - Error rates and types

4. **User Experience**:
   - Time to first result
   - Total planning session time
   - User satisfaction scores

### 9.2 Monitoring Implementation

TripSage implements comprehensive monitoring:

1. **Real-time Dashboards**:

   - API performance metrics
   - Cache health and utilization
   - MCP server status
   - Database performance

2. **Alerting**:

   - Response time thresholds
   - Error rate spikes
   - API rate limit warnings
   - Cache performance degradation

3. **Logging**:
   - Structured logging across all components
   - Correlation IDs for request tracing
   - Error context preservation
   - Performance timing events

### 9.3 Testing Methodology

Testing is implemented at multiple levels:

1. **Unit Tests**:

   - Core functionality of all MCP servers
   - Data model validation
   - Utility function verification

2. **Integration Tests**:

   - MCP server communication
   - Data flow between components
   - Authentication and authorization

3. **End-to-End Tests**:

   - Complete travel planning scenarios
   - Cross-component interactions
   - User flow simulations

4. **Performance Tests**:
   - Load testing under various conditions
   - Concurrency testing
   - Latency measurements
   - Cache effectiveness validation

### 9.4 Continuous Improvement

TripSage implements a continuous improvement cycle:

1. **Metrics Analysis**:

   - Regular review of performance metrics
   - Identification of bottlenecks
   - Trend analysis over time

2. **User Feedback**:

   - Collection of user satisfaction data
   - Analysis of user behavior patterns
   - Identification of pain points

3. **System Enhancements**:

   - Prioritized backlog of improvements
   - Regular enhancement sprints
   - A/B testing of optimizations

4. **Knowledge Sharing**:
   - Documentation updates
   - Team knowledge sharing sessions
   - Best practices refinement

## 10. Conclusion

The TripSage optimization strategy provides a comprehensive roadmap for implementing a high-performance, maintainable travel planning system. By standardizing on Python FastMCP 2.0, adopting official MCP implementations where available, and implementing a dual-storage architecture with Supabase and Neo4j, we achieve a balance of development speed, maintainability, and feature richness.

The phased implementation approach ensures that we can gradually build the full system while maintaining stability and providing continuous service to users. The addition of Qdrant for vector search capabilities post-MVP will further enhance the system's ability to provide personalized, semantic search capabilities.

This consolidated strategy document provides a single source of truth for the TripSage optimization approach, bringing together architecture decisions, technology selections, implementation plans, and monitoring strategies into a cohesive whole.
````

## File: reference/openai_agents_sdk.md

````markdown
# OpenAI Agents SDK Integration Guide

This document provides detailed implementation examples for using the OpenAI Agents SDK in the TripSage project.

## Installation and Setup

```bash
# Install using uv
uv pip install openai-agents

# Set environment variable (never store API keys in code)
export OPENAI_API_KEY=sk-...
```

## Agent Architecture

### Hierarchical Structure

```python
from agents import Agent, handoff

# Main orchestrator agent
travel_agent = Agent(
    name="Travel Planning Agent",
    instructions="You are a comprehensive travel planning assistant...",
    handoffs=[flight_agent, accommodation_agent, activity_agent, budget_agent]
)

# Specialized sub-agents
flight_agent = Agent(
    name="Flight Agent",
    instructions="You specialize in finding optimal flights...",
    tools=[search_flights, compare_prices, check_availability]
)
```

### Agent Responsibilities

- **Travel Planning Agent**: Main orchestrator, manages overall planning
- **Flight Agent**: Flight search and booking recommendations
- **Accommodation Agent**: Hotel and rental searches and recommendations
- **Activity Agent**: Local activities and attractions
- **Budget Agent**: Budget optimization and allocation

### Model Selection Guidelines

- Use `gpt-4` for complex reasoning tasks (main agent, budget optimization)
- Use `gpt-3.5-turbo` for simpler, well-defined tasks (data extraction, formatting)
- Set temperature to `0.2` for predictable, accurate responses
- Set temperature to `0.7-0.9` for creative suggestions (activity ideas)

## Function Tool Design

```python
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Dict, Any, Annotated
from agents import function_tool
from datetime import date, datetime

class FlightSearchParams(BaseModel):
    """Model for validating flight search parameters."""

    # Use ConfigDict for model configuration (Pydantic v2)
    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        frozen=True      # Make instances immutable
    )

    # Required parameters with validation
    origin: str = Field(..., min_length=3, max_length=3,
                       description="Origin airport IATA code (e.g., 'SFO')")
    destination: str = Field(..., min_length=3, max_length=3,
                            description="Destination airport IATA code (e.g., 'JFK')")
    departure_date: date = Field(..., description="Departure date (YYYY-MM-DD)")

    # Optional parameters with defaults and validation
    return_date: Optional[date] = Field(None, description="Return date for round trips")
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price in USD")
    passengers: int = Field(1, ge=1, le=9, description="Number of passengers")
    cabin_class: str = Field("economy", description="Cabin class for flight")

    # Field-level validators
    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate airport code format."""
        return v.upper()  # Ensure IATA codes are uppercase

@function_tool
async def search_flights(params: FlightSearchParams) -> Dict[str, Any]:
    """Search for available flights based on user criteria.

    Args:
        params: The flight search parameters including origin, destination,
               dates, price constraints, and number of passengers.

    Returns:
        A dictionary containing flight options with prices and details.
    """
    try:
        # Implementation that accesses flight APIs
        # Store results in Supabase and knowledge graph

        return {
            "search_id": str(uuid.uuid4()),
            "search_params": params.model_dump(),
            "results": [
                # Flight results would be populated here
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.exception(f"Flight search error: {e}")
        return {
            "error": "SEARCH_ERROR",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

## Handoff Implementation

### Basic Handoffs

```python
from agents import Agent, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

flight_agent = Agent(
    name="Flight Agent",
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nYou specialize in flight search..."
)

budget_agent = Agent(
    name="Budget Agent",
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nYou specialize in budget optimization..."
)

travel_agent = Agent(
    name="Travel Planning Agent",
    instructions="You orchestrate the travel planning process...",
    handoffs=[flight_agent, budget_agent]
)
```

### Handoff with Input Data

```python
from pydantic import BaseModel
from agents import handoff, RunContextWrapper

class BudgetOptimizationData(BaseModel):
    total_budget: float
    allocation_request: str
    priorities: list[str]

async def on_budget_handoff(ctx: RunContextWrapper[None], input_data: BudgetOptimizationData):
    # Log the budget request
    # Preload relevant data
    pass

budget_handoff = handoff(
    agent=budget_agent,
    on_handoff=on_budget_handoff,
    input_type=BudgetOptimizationData
)

travel_agent = Agent(
    name="Travel Planning Agent",
    handoffs=[flight_agent, budget_handoff]
)
```

## Guardrail Implementation

### Input Guardrails

```python
from pydantic import BaseModel
from agents import Agent, GuardrailFunctionOutput, input_guardrail, RunContextWrapper

class BudgetCheckOutput(BaseModel):
    is_within_reasonable_range: bool
    reasoning: str

budget_check_agent = Agent(
    name="Budget Check",
    instructions="Check if the budget request is reasonable for the trip",
    output_type=BudgetCheckOutput
)

@input_guardrail
async def budget_check_guardrail(
    ctx: RunContextWrapper[None],
    agent: Agent,
    input: str | list
) -> GuardrailFunctionOutput:
    result = await Runner.run(budget_check_agent, input, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_within_reasonable_range
    )

travel_agent = Agent(
    name="Travel Planning Agent",
    input_guardrails=[budget_check_guardrail]
)
```

### Output Guardrails

```python
from pydantic import BaseModel
from agents import output_guardrail, GuardrailFunctionOutput

class TravelPlanOutput(BaseModel):
    itinerary: str
    budget_allocation: dict

@output_guardrail
async def budget_constraint_guardrail(
    ctx: RunContextWrapper,
    agent: Agent,
    output: TravelPlanOutput
) -> GuardrailFunctionOutput:
    # Check if budget allocation exceeds total budget
    total = sum(output.budget_allocation.values())
    is_within_budget = total <= ctx.context.get("total_budget", float("inf"))

    return GuardrailFunctionOutput(
        output_info={"is_within_budget": is_within_budget},
        tripwire_triggered=not is_within_budget
    )
```

## Tracing and Debugging

### Basic Tracing Configuration

```python
from agents import Agent, Runner, trace

# Named trace for the entire workflow
with trace("TripSage Planning Workflow"):
    initial_result = await Runner.run(travel_agent, user_query)
    refinement_result = await Runner.run(travel_agent, f"Refine this plan: {initial_result.final_output}")
```

### Custom Spans

```python
from agents.tracing import custom_span

async def search_and_book():
    with custom_span("flight_search", {"query": flight_query}):
        # Flight search logic
        pass
```

### Sensitive Data Protection

```python
from agents import Agent, Runner, RunConfig

# Don't include sensitive data in traces
config = RunConfig(trace_include_sensitive_data=False)
result = await Runner.run(agent, input, run_config=config)
```

## Testing Strategy

```python
import pytest
from unittest.mock import AsyncMock, patch
from agents import Agent, Runner

@pytest.fixture
def mock_flight_api():
    with patch("travel.apis.flight_api") as mock:
        mock.search = AsyncMock(return_value=[{"flight_id": "123", "price": 299.99}])
        yield mock

async def test_flight_agent(mock_flight_api):
    agent = Agent(
        name="Flight Agent",
        tools=[search_flights]
    )

    result = await Runner.run(agent, "Find flights from SFO to NYC next week")
    assert "123" in result.final_output
    mock_flight_api.search.assert_called_once()
```
````

## File: status/implementation_status.md

````markdown
# TripSage Implementation Status

**Date**: May 16, 2025  
**Project**: TripSage AI Travel Planning System  
**Status**: Planning and Initial Implementation Phase

## Overview

This document tracks the current implementation status of the TripSage travel planning system, with a focus on MCP server integration, architecture decisions, and implementation progress.

## Completed Items

### Documentation & Planning

- ✅ Created comprehensive architecture and optimization strategy (`/docs/optimization/tripsage_optimization_strategy.md`)
- ✅ Standardized on Python FastMCP 2.0 for MCP server implementation
- ✅ Decision to use official MCP implementations where available
- ✅ Successfully integrated official Time MCP server with client implementation
- ✅ Completed integration of Neo4j Memory MCP
- ✅ Standardized all MCP clients with Pydantic v2 validation patterns
- ✅ Implemented comprehensive tests for all MCP clients
- ✅ Consolidated all optimization and implementation plans into a single source of truth
- ✅ Selected core technology stack:
  - Python FastMCP 2.0 for MCP servers
  - Neo4j with official `mcp-neo4j-memory` for knowledge graph
  - Redis for multi-level caching
  - Supabase for relational data storage (production)
  - Neon for relational data storage (development)
  - OpenAPI integration for external travel APIs
- ✅ Deferred Qdrant vector database integration to post-MVP phase
- ✅ Created GitHub issue (#2) for post-MVP Qdrant integration with detailed implementation plan
- ✅ Finalized API integrations for Weather MCP Server (OpenWeatherMap, Visual Crossing, Weather.gov)
- ✅ Finalized API integrations for Web Crawling MCP Server (Crawl4AI, Firecrawl, Enhanced Playwright)
- ✅ Completed architectural evaluation of web crawling solutions, selecting Crawl4AI as primary engine
- ✅ Completed evaluation of browser automation frameworks, selecting Playwright with Python as primary solution
- ✅ Deprecated Browser-use in favor of Playwright with Python for browser automation
- ✅ Updated browser automation documentation with Playwright MCP server implementation details

### Repository Organization

- ✅ Archived duplicate/outdated optimization and integration documents
- ✅ Set up project directory structure for MCP server implementation
- ✅ Organized documentation in logical sections (optimization, integration, status)
- ✅ Created detailed implementation specifications for MCP servers

### MCP Server Implementation

- ✅ Created shared base MCP classes using FastMCP 2.0 framework for consistency
- ✅ Integrated with official Time MCP server
- ✅ Implemented Time MCP client for accessing official Time MCP server
- ✅ Created deployment script for official Time MCP server
- ✅ Implemented Weather MCP Server with FastMCP 2.0
- ✅ Created TimeZoneDatabase API client for timezone and time management operations
- ✅ Created OpenWeatherMapClient API client for weather data retrieval
- ✅ Implemented Pydantic models throughout for data validation and schema definition
- ✅ Standardized all MCP clients with Pydantic v2 validation patterns
- ✅ Unified \_call_validate_tool method across all MCP clients
- ✅ Added proper error handling, parameter validation, and caching strategies
- ✅ Created high-level service classes that provide domain-specific functionality
- ✅ Added AI agent integration with tool schemas for both OpenAI and Claude
- ✅ Created test scripts for manual testing of Time and Weather MCP clients
- ✅ Implemented comprehensive unit tests with pytest for all MCP clients
- ✅ Added MockMCPClient pattern for reliable testing without external dependencies
- ✅ Implemented test coverage for parameter validation, response validation, and error handling
- ✅ Implemented OpenBnB Airbnb MCP server integration with start/stop scripts

## Completed Implementation Tasks

- ✅ Set up development environment for Python FastMCP 2.0
- ✅ Neo4j Memory MCP server configuration and integration (Issue #20)
- ✅ Initial MCP tool definitions for Web Crawling MCP server
- ✅ Developing Crawl4AI self-hosted environment for Web Crawling MCP server (Issue #19)
- ✅ Setting up Playwright MCP server development environment
- ✅ Implementing browser context management for Playwright MCP
- ✅ Implemented comprehensive browser automation tools
- ✅ Implemented destination research capabilities
- ✅ Implemented flight search capabilities with Duffel API via ravinahp/flights-mcp server (Issue #16)
- ✅ Implemented Google Maps MCP integration for location services (Issue #18)
- ✅ Integrated OpenBnB Airbnb MCP for accommodation search (Issue #17 & #24)
- ✅ Integrated official Time MCP for timezone and clock operations (PR #51)
- ✅ Centralized configuration with Pydantic Settings (Issue #15)
- ✅ Implemented basic WebSearchTool caching with Redis

## Current Development Focus

- 🔄 Refactoring agent orchestration using OpenAI Agents SDK (#28)
- 🔄 Implementing advanced Redis-based caching for web operations (#38)
- 🔄 Integrating OpenAI WebSearchTool with travel-specific configuration (#37)
- 🔄 Standardizing and expanding test suite to 90% coverage (#35)
- 🔄 Setting up CI pipeline with linting and type checking (#36)
- 🔄 Implementing Supabase MCP and Neon DB MCP for database operations (#23, #22)

## Next Steps

### Immediate Focus (1-2 Weeks)

1. Initialize Python FastMCP 2.0 development environment

   - Install dependencies and setup tooling
   - Create project scaffolding for MCP servers
   - Set up testing framework

2. ~~Implement Weather MCP Server~~ ✅ COMPLETED

   - ~~Develop OpenWeatherMap API integration~~ ✅
   - ~~Create MCP tools for current conditions, forecasts, and recommendations~~ ✅
   - ~~Implement caching strategy with Redis~~ ✅
   - ~~Add error handling and fallback mechanisms~~ ✅

3. ~~Implement Time MCP Integration~~ ✅ COMPLETED

   - ~~Integrate with official Time MCP server~~ ✅
   - ~~Create client implementation for Time MCP tools~~ ✅
   - ~~Develop agent function tools for time operations~~ ✅
   - ~~Implement deployment script for Time MCP server~~ ✅
   - ~~Create comprehensive tests for Time MCP client~~ ✅

4. ~~Implement Web Crawling MCP Server~~ ✅ COMPLETED

   - ~~Set up Crawl4AI self-hosted environment~~ ✅
   - ~~Create adapter layer for Crawl4AI, Firecrawl, and Enhanced Playwright~~ ✅
   - ~~Develop source selection strategy based on content type and website characteristics~~ ✅
   - ~~Implement batch processing for efficient parallel extractions~~ ✅
   - ~~Create tools for destination research and content extraction~~ ✅
   - ~~Develop structured data processing~~ ✅

5. ~~Implement Browser Automation MCP Server~~ ✅ COMPLETED
   - ~~Create Playwright MCP server with Python FastMCP 2.0~~ ✅
   - ~~Implement browser context management and resource pooling~~ ✅
   - ~~Develop travel-specific automation functions (flight status, booking verification)~~ ✅
   - ~~Create OpenAI Agents SDK integration layer~~ ✅
   - ~~Implement caching and performance optimization~~ ✅

### Short-Term (3-4 Weeks)

1. ~~Implement Flight MCP Server~~ ✅ COMPLETED

   - ~~Integrate with Duffel API via ravinahp/flights-mcp server~~ ✅
   - ~~Develop flight search capabilities~~ ✅
   - ~~Set up price tracking and history~~ ✅

2. ~~Implement Accommodation MCP Server~~ ✅ COMPLETED
   - ~~Create integration with OpenBnB Airbnb MCP~~ ✅
   - ~~Develop accommodation search and factory pattern for multiple sources~~ ✅
   - ~~Implement dual storage in Supabase and Memory MCP~~ ✅

### Medium-Term (5-6 Weeks)

1. Implement Calendar MCP Server

   - Set up Google Calendar API integration
   - Develop OAuth flow for user authorization
   - Create tools for travel itinerary management

2. ~~Implement Memory MCP Server~~ ✅ COMPLETED
   - ~~Integrate with Neo4j via official MCP implementation~~ ✅
   - ~~Develop knowledge graph for travel entities and relationships~~ ✅
   - ~~Create tools for knowledge storage and retrieval~~ ✅
   - ~~Implement dual storage strategy (Supabase + Neo4j)~~ ✅

### Long-Term (7-8 Weeks)

1. Finalize MVP Implementation

   - Complete end-to-end testing
   - Optimize performance
   - Document API and usage patterns

2. Prepare for Qdrant Integration (Post-MVP)
   - Research embedding models for travel data
   - Design vector storage schema
   - Prepare integration architecture

## Risk Assessment

| Risk                                       | Impact | Likelihood | Mitigation                                  |
| ------------------------------------------ | ------ | ---------- | ------------------------------------------- |
| Python FastMCP 2.0 is still evolving       | Medium | Medium     | Pin to stable version, monitor for changes  |
| External API rate limitations              | High   | High       | Implement robust caching and rate limiting  |
| Integration complexity between MCP servers | Medium | Medium     | Clear interfaces, comprehensive testing     |
| Neo4j knowledge graph scaling              | Medium | Low        | Design for scalability, monitor performance |
| Environment variable management for APIs   | Medium | Low        | Implement secure credential storage         |
| Crawl4AI self-hosting complexity           | Medium | Medium     | Create detailed deployment documentation    |
| Playwright browser context management      | Medium | Low        | Implement resource pooling and monitoring   |

## Resource Requirements

- **Development Environment**: Python 3.10+, Node.js 18+
- **External Services**:
  - Weather: OpenWeatherMap API, Visual Crossing, Weather.gov
  - Web Crawling: Crawl4AI (self-hosted), Firecrawl API, Enhanced Playwright
  - Browser Automation: Playwright with Python
  - Flights: Duffel API
  - Accommodations: OpenBnB API, Apify Booking.com
  - Calendar: Google Calendar API
- **Infrastructure**: Redis instance, Neo4j database, Supabase project, Neon development databases
- **Post-MVP**: Qdrant instance (for vector search)

## Specialized MCP Server Status

| MCP Server             | Status    | Primary APIs/Services                             | Implementation Priority |
| ---------------------- | --------- | ------------------------------------------------- | ----------------------- |
| Time MCP               | Completed | Official Time MCP Server                          | Completed               |
| Weather MCP            | Completed | OpenWeatherMap, Visual Crossing, Weather.gov      | Completed               |
| Web Crawling MCP       | Completed | Crawl4AI (self-hosted), Firecrawl API, Playwright | Completed               |
| Browser Automation MCP | Completed | Playwright with Python                            | Completed               |
| Flights MCP            | Completed | ravinahp/flights-mcp using Duffel API             | Completed               |
| Accommodation MCP      | Completed | OpenBnB Airbnb MCP                                | Completed               |
| Calendar MCP           | Planned   | Google Calendar API                               | Medium-Term (Weeks 5-6) |
| Memory MCP             | Completed | Neo4j Official Memory MCP                         | Completed               |
| Google Maps MCP        | Completed | Google Maps API                                   | Completed               |

## Agent Implementation Status

| Agent Component          | Status  | Description                                        |
| ------------------------ | ------- | -------------------------------------------------- |
| Travel Planning Agent    | Planned | Main agent for flight and accommodation search     |
| Budget Planning Agent    | Planned | Specialized agent for budget optimization          |
| Itinerary Planning Agent | Planned | Agent for creating and managing travel itineraries |

## Web Crawling Architecture

The Web Crawling MCP Server will utilize a tiered architecture with three key components:

1. **Crawl4AI (Primary)**: Self-hosted web crawling engine providing 10× throughput improvements

   - Batch processing for parallel extractions
   - Travel-specific content extraction templates
   - Advanced caching with content-aware TTL

2. **Firecrawl API (Secondary)**: Existing MCP for specialized AI-optimized extractions

   - Deep research capabilities
   - Semantic extraction features

3. **Enhanced Playwright with Python (Tertiary)**: Custom automation framework for dynamic content
   - Interactive site navigation using native Python bindings
   - Authentication handling with browser context management
   - Form submission and event extraction
   - Superior performance (35% faster than alternatives)
   - Cross-browser support (Chrome, Firefox, WebKit)

This architecture represents an upgrade from the previous Firecrawl-first approach, based on comprehensive evaluation showing Crawl4AI's superior performance for travel-specific content extraction.

## Browser Automation Architecture

The Browser Automation is now implemented using external MCP servers (Playwright MCP and Stagehand MCP) via agent tools, replacing the custom Browser MCP implementation:

1. **External MCP Integration**: Two specialized MCP servers

   - **Playwright MCP**: For precise browser automation
     - 35% faster than alternatives
     - Cross-browser support (Chrome, Firefox, WebKit)
     - Fine-grained control over browser behavior

   - **Stagehand MCP**: For AI-driven automation
     - Natural language instructions for browser operations
     - Fallback capabilities when precise selectors aren't available
     - Self-healing automation workflows

2. **Browser Tools Architecture**: Clean separation of concerns

   - **Tool Interface**: Function tools compatible with OpenAI Agents SDK
   - **MCP Clients**: Dedicated clients for Playwright MCP and Stagehand MCP
   - **BrowserService**: Service layer handling business logic and caching
   - **Redis Caching**: Results caching for improved performance

3. **Travel-Specific Function Tools**: Purpose-built for travel needs

   - **check_flight_status**: Flight status checking with airline websites
   - **verify_booking**: Booking verification across various providers
   - **monitor_price**: Price monitoring for flights, hotels, and activities

4. **Data Validation**: Comprehensive Pydantic v2 implementation
   - Field validators with @field_validator
   - Model validators with @model_validator
   - Request/response validation
   - Strong typing with Annotated and custom validators

This architecture represents a significant upgrade from the custom Browser MCP implementation, leveraging specialized external MCPs for improved reliability, maintainability, and performance. The new approach also eliminates any usage limitations and provides better integration with the Python-based agent tools.

## Recent Completions (May 13-16, 2025)

The following issues and PRs have been completed in the latest development cycle:

| Issue | Title                                                          | PR  | Status       |
| ----- | -------------------------------------------------------------- | --- | ------------ |
| #15   | Centralize configuration and secrets with Pydantic Settings    | -   | ✅ Completed |
| #16   | Integrate Flights MCP or Duffel API via Custom FastMCP Tool    | #42 | ✅ Completed |
| #17   | Integrate Airbnb MCP and Plan for Other Accommodation Sources  | #44 | ✅ Completed |
| #18   | Adopt Google Maps MCP for Location Data and Routing            | #43 | ✅ Completed |
| #19   | Integrate Crawl4AI MCP and Firecrawl for Advanced Web Crawling | #45 | ✅ Completed |
| #20   | Integrate Neo4j Memory MCP and Remove Custom Memory Logic      | #49 | ✅ Completed |
| #24   | Integrate Official Airbnb MCP (OpenBnB) for Vacation Rentals   | -   | ✅ Completed |
| #26   | Replace Custom Browser MCP with External Playwright & Stagehand MCPs | -   | ✅ Completed |
| #69   | Implement Dual Storage Service Pattern with Service-Based Architecture | #78 | ✅ Completed |
| -     | Integrate Official Time MCP for Timezone and Clock Operations  | #51 | ✅ Completed |
| -     | Implement MCP client tests and update Pydantic v2 validation   | #53 | ✅ Completed |
| -     | Create comprehensive MCP abstraction layer tests               | -   | ✅ Completed |

## MCP Abstraction Testing Infrastructure (May 16, 2025)

The following comprehensive testing infrastructure has been implemented for the MCP abstraction layer:

### Test Coverage

- ✅ Base wrapper class tests with proper dependency mocking
- ✅ MCPManager singleton pattern tests
- ✅ MCPClientRegistry tests with mock clients
- ✅ All MCP wrapper implementations covered:
  - Duffel Flights Wrapper
  - Firecrawl Wrapper  
  - Crawl4AI Wrapper
  - Neo4j Memory Wrapper
  - Google Calendar Wrapper
  - Airbnb Wrapper

### Key Features

- Isolated testing with proper mocking of Redis and environment variables
- Comprehensive fixtures for all MCP clients
- Import circular dependency resolution
- Pytest-based test infrastructure
- Test coverage utilities with 90%+ requirement
- End-to-end integration tests for travel planning flows
- Test documentation and contributor guidelines

### Test Organization

- Moved test scripts to `scripts/` directory for better organization
- Created comprehensive test README with guidelines
- Fixed all linting issues (E501, E402)
- Ensured all tests properly mock external dependencies

This work establishes a robust foundation for maintaining code quality and enabling safe refactoring as the project evolves.

## Current Open Issues

The following key issues remain open and are the focus of upcoming work:

| Issue | Title                                                              | Priority | Status                                                                       |
| ----- | ------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------- |
| #41   | Implement Vector Search with Qdrant MCP for TripSage               | Post-MVP | Not Started                                                                  |
| #38   | Implement Advanced Redis-based Caching for TripSage Web Operations | High     | Not Started                                                                  |
| #37   | Integrate OpenAI Agents SDK WebSearchTool for General Web Queries  | High     | Not Started                                                                  |
| #36   | Implement CI Pipeline with Linting, Type Checking, and Coverage    | Medium   | Not Started                                                                  |
| #35   | Standardize and Expand TripSage Test Suite (Target 90%+ Coverage)  | High     | In Progress - MCP abstraction tests completed with comprehensive coverage    |
| #28   | Refactor Agent Orchestration using OpenAI Agents SDK               | Critical | Not Started                                                                  |
| #25   | Integrate Google Calendar MCP for Itinerary Scheduling             | Medium   | Not Started                                                                  |
| #23   | Integrate Supabase MCP Server for Production Database Operations   | High     | In Progress - Foundation laid with Pydantic v2 validation patterns in PR #53 |
| #22   | Integrate Neon DB MCP Server for Development Environments          | Medium   | In Progress - Foundation laid with Pydantic v2 validation patterns in PR #53 |
| #7    | Create structured prompts directory hierarchy                      | Low      | Not Started                                                                  |
| #2    | Integrate Qdrant for semantic search capabilities                  | Post-MVP | Not Started                                                                  |

## Conclusion

The TripSage implementation has made significant progress with all key MCP server components now complete. We've successfully integrated with multiple official MCP servers (Time MCP, Neo4j Memory MCP, Google Maps MCP, Airbnb MCP, Playwright MCP, Stagehand MCP) and created robust client implementations with proper error handling and caching strategies.

Recent completions include:

1. Integrating the official Time MCP server for time and timezone operations
2. Implementing the ravinahp/flights-mcp server for flight search via Duffel API
3. Setting up the OpenBnB Airbnb MCP for accommodation search
4. Implementing a dual storage strategy with Supabase and Neo4j Memory MCP
5. Integrating Crawl4AI and Firecrawl for advanced web crawling
6. Adopting the Google Maps MCP for location data and routing
7. Centralizing configuration with Pydantic Settings
8. Creating deployment scripts for MCP servers including start/stop functionality
9. Standardizing all MCP clients with Pydantic v2 validation patterns
10. Implementing comprehensive test suite for all MCP clients
11. Creating MockMCPClient pattern for reliable testing without external dependencies
12. Replacing custom Browser MCP with external Playwright MCP and Stagehand MCP integration
13. Refactoring dual storage pattern into service-based architecture with abstract base class

The system follows a hybrid database approach with Supabase for production and Neon for development, complemented by Neo4j for knowledge graph capabilities. Vector search functionality via Qdrant is scheduled for post-MVP implementation.

The immediate focus is now on implementing the OpenAI Agents SDK integration (#28), improving the caching strategy (#38), and enhancing web search capabilities (#37). These will be followed by database operations via MCP servers (#22, #23) and calendar integration (#25).

The MCP client refactoring and test implementation (PR #53) adds significant reliability and maintainability to the codebase with standardized Pydantic v2 validation patterns across all MCP clients. This work has established a unified pattern for implementing future MCP clients (like Neon and Supabase) with proper validation and error handling.

The Browser MCP refactoring (Issue #26) represents another significant architectural improvement, replacing the custom Browser MCP implementation with integration of specialized external MCPs (Playwright MCP and Stagehand MCP). This approach provides both precise browser control and AI-driven automation capabilities, while following modern best practices with clean separation of concerns, Pydantic v2 validation, and Redis caching.

Progress continues to be tracked in GitHub issues, with detailed implementation plans and timelines as outlined in the optimization strategy document.
````
