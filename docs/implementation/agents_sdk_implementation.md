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
