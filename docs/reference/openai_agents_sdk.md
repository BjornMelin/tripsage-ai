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
