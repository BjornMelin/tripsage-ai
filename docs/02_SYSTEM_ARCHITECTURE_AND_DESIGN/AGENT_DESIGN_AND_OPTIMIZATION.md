# TripSage Agent Design and Optimization

This document details the architecture, design principles, and optimization strategies for AI agents within the TripSage system. It focuses on leveraging the OpenAI Agents SDK and integrating with TripSage's Model Context Protocol (MCP) servers.

## 1. Agent Architecture Philosophy

TripSage employs a hierarchical agent architecture. This design allows for:

- **Specialization**: Each agent focuses on a specific domain (e.g., flights, accommodations, budget).
- **Orchestration**: A primary agent (Travel Planning Agent) coordinates tasks and delegates to specialized agents.
- **Modularity**: Easier development, testing, and maintenance of individual agent capabilities.
- **Efficiency**: Use of smaller, more focused models for specialized tasks where appropriate.

## 2. Core Framework: OpenAI Agents SDK

TripSage utilizes the OpenAI Agents SDK as the foundational framework for building its AI agents.

### Key Advantages of OpenAI Agents SDK

- **Python-first Approach**: Aligns with TripSage's backend language, using standard Python patterns.
- **Lightweight Architecture**: Minimal core abstractions (Agents, Tools, Handoffs, Guardrails) simplify development.
- **Flexible Model Support**: Works with various LLM providers through LiteLLM integration, though TripSage primarily targets OpenAI models like GPT-4o and GPT-3.5-turbo.
- **MCP Support**: Native or straightforward integration with MCP servers is a key design consideration.
- **Tracing and Observability**: Built-in tracing capabilities aid in debugging and monitoring agent behavior.

### Basic Agent Implementation Structure

A typical agent in TripSage is defined as follows:

```python
from agents import Agent, Runner, function_tool
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# Example Pydantic model for tool input validation
class SearchParams(BaseModel):
    query: str = Field(..., description="The search query")
    limit: Optional[int] = Field(5, description="Number of results to return")

class SpecializedAgent(Agent):
    def __init__(self, name: str, instructions: str, model: str = "gpt-4o", tools: Optional[List[Any]] = None):
        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            tools=tools or []
        )

    @function_tool
    async def example_tool(self, params: SearchParams) -> Dict[str, Any]:
        """
        An example tool that this agent can use.
        It takes search parameters and returns a dictionary.
        """
        # Tool implementation logic
        # This would typically involve calling an MCP client or another service
        return {"status": "success", "query_received": params.query, "results_found": params.limit}

# Usage:
# specialized_agent = SpecializedAgent(name="MySpecialAgent", instructions="...", tools=[SpecializedAgent.example_tool])
# result = await Runner.run(specialized_agent, "User input for this agent")
# print(result.final_output)
```

## 3. Hierarchical Agent Structure in TripSage

- **Triage Agent / Main Travel Planning Agent (`TripSageTravelAgent`)**:

  - **Responsibilities**: Acts as the primary orchestrator and user interface. Understands the overall user query, breaks it down into sub-tasks, and delegates to specialized agents or directly uses tools for simpler requests. Manages the overall planning context.
  - **Model**: Typically `gpt-4o` for robust understanding and planning.
  - **Tools**: Broad access to high-level tools, including handoff capabilities to specialized agents and core MCP tools for trip creation, destination info, etc.

- **Specialized Agents**:
  - **Flight Agent**:
    - **Responsibilities**: Handles all flight-related queries, including search, comparison, price tracking, and providing booking recommendations.
    - **Model**: Can be `gpt-4o` or `gpt-3.5-turbo` depending on the complexity of the flight task.
    - **Tools**: Primarily interacts with the Flights MCP.
  - **Accommodation Agent**:
    - **Responsibilities**: Focuses on finding and comparing hotels, vacation rentals, and other lodging.
    - **Model**: `gpt-4o`.
    - **Tools**: Interacts with the Accommodations MCP (which wraps Airbnb, Booking.com, etc.).
  - **Activity/Destination Research Agent**:
    - **Responsibilities**: Gathers detailed information about destinations, points of interest, local customs, and activities.
    - **Model**: `gpt-4o`.
    - **Tools**: Heavily utilizes the WebCrawl MCP and Google Maps MCP.
  - **Budget Agent**:
    - **Responsibilities**: Helps users manage their travel budget, optimize expenses, and compare costs.
    - **Model**: `gpt-4o` for financial reasoning.
    - **Tools**: May use tools that aggregate pricing data from other MCPs, and potentially financial calculation tools.
  - **Itinerary Agent**:
    - **Responsibilities**: Constructs detailed day-by-day itineraries, schedules activities, and integrates with calendar services.
    - **Model**: `gpt-4o`.
    - **Tools**: Interacts with Calendar MCP, Time MCP, and Google Maps MCP.

### Handoff Mechanism

TripSage implements a robust handoff mechanism that enables agents to seamlessly transfer control or delegate tasks to specialized agents. For detailed implementation and usage, see the dedicated [Agent Handoffs](AGENT_HANDOFFS.md) documentation.

#### Two Handoff Patterns

TripSage supports two primary handoff patterns:

1. **Full Handoffs**: Transfer complete control to a specialist agent (conversation handoff)
2. **Delegations**: Use a specialist agent as a tool without transferring conversation control

The implementation in TripSage extends the OpenAI Agents SDK with custom handoff infrastructure that allows for flexible agent interactions while maintaining context and session data across handoffs.

#### Example Implementation

Here's a simplified example of how handoffs are registered in TripSage:

```python
from tripsage.agents.base import BaseAgent
from tripsage.agents.handoffs import register_handoff_tools, register_delegation_tools

class MainAgent(BaseAgent):
    def __init__(self, name="Main Agent", model=None, temperature=None):
        super().__init__(name=name, instructions="...", model=model, temperature=temperature)

        # Register handoff tools
        handoff_configs = {
            "hand_off_to_flight_agent": {
                "agent_class": FlightAgent,
                "description": "Hand off to flight specialist for flight search and booking",
                "context_filter": ["user_id", "session_id", "session_data"],
            },
            "hand_off_to_accommodation_agent": {
                "agent_class": AccommodationAgent,
                "description": "Hand off to accommodation specialist for lodging search",
                "context_filter": ["user_id", "session_id", "session_data"],
            }
        }

        # Register delegation tools
        delegation_configs = {
            "get_flight_options": {
                "agent_class": FlightAgent,
                "description": "Get flight options without transferring the conversation",
                "return_key": "content",
                "context_filter": ["user_id", "session_id"],
            }
        }

        # Register both types of tools
        self.register_multiple_handoffs(handoff_configs)
        self.register_multiple_delegations(delegation_configs)
```

To process handoffs in your code:

```python
# Run the agent
response = await main_agent.run(user_input, context=context)

# Check if this is a handoff
if response.get("status") == "handoff":
    # Process the handoff
    handoff_response = await main_agent.process_handoff_result(response, context=context)

    # Handle the response from the specialist agent
    print(f"Specialist agent response: {handoff_response.get('content')}")
else:
    # Handle normal response
    print(f"Main agent response: {response.get('content')}")
```

#### Handoff Context Management

The TripSage handoff system preserves important context across handoffs:

- **Session data**: User preferences, interaction history, etc.
- **Memory data**: Data from the knowledge graph
- **Handoff metadata**: Information about the source agent, handoff reason, etc.

This ensures that specialized agents have the context they need to provide seamless user experiences.

See [Agent Handoffs](AGENT_HANDOFFS.md) for detailed documentation on TripSage's handoff capabilities.

## 4. Agent Prompt Optimization

Effective prompting is crucial for agent performance.

### Key Principles

- **Clear Role Definition**: Explicitly state the agent's name, purpose, and areas of expertise/limitations.
- **Structured Capabilities**: List what the agent _can_ do, especially regarding tool usage.
- **Interaction Guidelines**: Provide step-by-step instructions for common workflows (e.g., "1. Gather key parameters. 2. Use tool X. 3. Present options.").
- **Tool Calling Guidance**:
  - Specify _when_ to use a particular tool.
  - Detail the _required parameters_ for each tool.
  - Explain how to interpret tool output if necessary.
- **Context Window Management**:
  - Instruct agents to be concise.
  - Encourage summarizing previous interactions if context grows large.
  - Utilize session memory (via Memory MCP) to offload long-term context.
- **Error Handling Instructions**: Guide the agent on how to react to tool errors or unavailable information (e.g., "If a flight search fails, inform the user and ask if they want to try different dates.").
- **Output Formatting**: If a specific output format is desired (e.g., JSON, Markdown table), specify this in the prompt. Pydantic `output_type` in the Agent definition is preferred for structured output.

### Recommended Prompt Structure (General Template)

```text
You are {AgentName}, an AI assistant for TripSage, specializing in {AgentSpecialization}.

CAPABILITIES:
- {Capability 1, e.g., Search for flights using the 'search_flights' tool}
- {Capability 2, e.g., Find accommodations using the 'find_accommodations' tool}
- {Capability N}

INTERACTION GUIDELINES:
1.  Always clarify: {Key parameters to gather first, e.g., destination, dates, budget, preferences}.
2.  Tool Usage:
    - For {task_type_1}: Use the '{tool_name_1}' tool. Always provide {required_params_for_tool_1}.
    - For {task_type_2}: Use the '{tool_name_2}' tool. Ensure {param_x} is in YYYY-MM-DD format.
3.  Presentation: Present options clearly, including {key_details_to_include, e.g., price, ratings, duration}.
4.  State Management: Remember key details from the current conversation. For long-term memory, use the 'store_preference' or 'update_trip_notes' tools.
5.  Error Handling: If a tool call fails or returns no results, inform the user, explain briefly, and suggest alternatives or ask for refined criteria.

USER PREFERENCES:
(This section can be dynamically populated by the system with known user preferences from the Memory MCP)
- Preferred Airlines: {user_preferred_airlines}
- Accommodation Style: {user_accommodation_style}
- Budget Tier: {user_budget_tier}

IMPORTANT:
- Be polite and helpful.
- If you cannot fulfill a request, clearly state why.
- Prioritize information from your tools over general knowledge.
```

### Token Optimization Techniques

- **Progressive Disclosure**: Agents should request and present information in stages, rather than all at once.
- **Selective Detail**: Initial responses should be summaries; agents can offer to provide more details if the user requests them.
- **User-Directed Exploration**: Empower users to ask for drill-downs on specific options.
- **Memory MCP for Long-Term Context**: Store user profiles, detailed preferences, and past trip summaries in the Neo4j knowledge graph via the Memory MCP to reduce the amount of information needed in the active prompt context.
- **Concise Tool Outputs**: Design MCP tools to return only essential information. Agents can be prompted to request more details if needed.
- **Model Selection**: Use more capable (but potentially more token-hungry) models like GPT-4o for complex reasoning and cheaper models like GPT-3.5-turbo for simpler, specific tasks or initial triage.

## 5. MCP Integration with Agents

Agents interact with MCP servers via dedicated Python client wrappers, which are then exposed as tools to the agent.

### Simplified Integration using `create_agent_with_mcp_servers`

The `mcp_servers.openai_agents_integration` module (from original docs) provides helpers.

```python
# From docs/implementation/agents_sdk_implementation.md
import asyncio
from mcp_servers.openai_agents_integration import create_agent_with_mcp_servers
from agents import Runner

async def main():
    # Create an agent with specific MCP servers
    # This helper function would internally manage starting/stopping MCPs if they are process-based
    # and then register their tools with the agent.
    agent = await create_agent_with_mcp_servers(
        name="Travel Agent with MCPs",
        instructions="You are a travel planning assistant...",
        server_names=["airbnb", "google-maps"], # Names defined in openai_agents_config.js
        model="gpt-4o"
    )

    result = await Runner.run(agent, "Help me find a place to stay in Paris and get directions.")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
```

### Manual MCP Client Tool Registration

For more fine-grained control or when using custom MCP clients not managed by `MCPServerManager`:

```python
# Assuming FlightsMCPClient is your Python client for the Flights MCP
from src.mcp.flights.client import FlightsMCPClient # Example path
from agents import Agent, function_tool

flights_mcp_client = FlightsMCPClient() # Properly configured

# Expose a specific method of the MCP client as an agent tool
@function_tool
async def search_flights_via_mcp(params: FlightSearchParams) -> Dict[str, Any]: # FlightSearchParams from Pydantic
    """Searches for flights using the Flights MCP."""
    return await flights_mcp_client.search_flights(
        origin=params.origin,
        destination=params.destination,
        # ... other parameters
    )

flight_specialist_agent = Agent(
    name="Flight Specialist",
    instructions="I find the best flights using our advanced flight search system.",
    tools=[search_flights_via_mcp]
)
```

## 6. Function Tool Design (Best Practices)

- **Pydantic for Validation**: Always use Pydantic models for input parameter validation in tools. This ensures data integrity and provides clear schemas for the LLM.

  ```python
  from pydantic import BaseModel, Field, field_validator
  from datetime import date
  from typing import Optional

  class FlightSearchParams(BaseModel):
      origin: str = Field(..., min_length=3, max_length=3, description="Origin airport IATA code (e.g., 'SFO')")
      destination: str = Field(..., min_length=3, max_length=3, description="Destination airport IATA code (e.g., 'JFK')")
      departure_date: date = Field(..., description="Departure date (YYYY-MM-DD)")
      return_date: Optional[date] = Field(None, description="Return date for round trips")
      passengers: int = Field(1, ge=1, description="Number of passengers")

      @field_validator("origin", "destination")
      def validate_airport_code(cls, v: str) -> str:
          return v.upper()

      @field_validator('return_date')
      def return_date_after_departure_date(cls, v, values):
          if v and 'departure_date' in values.data and v < values.data['departure_date']:
              raise ValueError('Return date must be after departure date.')
          return v
  ```

- **Clear Docstrings**: Tool docstrings are critical as they are part of what the LLM "sees". Make them descriptive, explain what the tool does, its parameters, and what it returns.
- **Atomic Operations**: Tools should ideally perform a single, well-defined task.
- **Error Handling within Tools**: Tools should catch exceptions from underlying services (like MCP client calls) and return structured error information that the agent can understand and potentially act upon.

  ```python
  @function_tool
  async def get_weather_forecast_tool(params: WeatherParams) -> Dict[str, Any]:
      """Fetches the weather forecast for a given location and number of days."""
      try:
          # result = await weather_mcp_client.get_forecast(...)
          # Mocked for example
          if params.location == "unknown":
              raise ValueError("Location not found")
          return {"location": params.location, "forecast": "Sunny", "temp_c": 25}
      except Exception as e:
          # Log the full error for debugging
          # logger.error(f"Error in get_weather_forecast_tool: {e}", exc_info=True)
          return {"error": True, "message": str(e), "details": "Could not retrieve weather data."}
  ```

- **Idempotency**: Where possible, design tools to be idempotent, especially for operations that modify state.

## 7. Guardrails

Guardrails are used to validate inputs to agents or outputs from agents, ensuring safety, compliance, or adherence to specific rules.

### Input Guardrails

Validate or modify user input before the agent processes it.

```python
from agents import Agent, GuardrailFunctionOutput, input_guardrail, RunContextWrapper, Runner

async def check_for_pii(ctx: RunContextWrapper[None], agent: Agent, user_input: str | list) -> GuardrailFunctionOutput:
    if isinstance(user_input, str) and "credit card" in user_input.lower(): # Simplified PII check
        return GuardrailFunctionOutput(
            output_info={"pii_detected": True, "action": "blocked"},
            tripwire_triggered=True, # Stops further processing by the agent
            final_output_override="I cannot process requests containing sensitive personal information like credit card numbers."
        )
    return GuardrailFunctionOutput(output_info={"pii_detected": False}, tripwire_triggered=False)

secure_travel_agent = Agent(
    name="Secure Travel Agent",
    instructions="I plan trips securely.",
    input_guardrails=[check_for_pii]
)

# Example run:
# result = await Runner.run(secure_travel_agent, "Book a flight with credit card 1234...")
# print(result.final_output) # Would print the final_output_override
```

### Output Guardrails

Validate or modify the agent's final response before it's sent to the user.

```python
from agents import Agent, GuardrailFunctionOutput, output_guardrail, RunContextWrapper
from pydantic import BaseModel

class TravelPlanOutput(BaseModel): # Assuming agent is configured to output this Pydantic model
    destination: str
    total_cost: float
    currency: str

@output_guardrail
async def budget_compliance_check(ctx: RunContextWrapper, agent: Agent, output: TravelPlanOutput) -> GuardrailFunctionOutput:
    user_max_budget = ctx.context.get("user_max_budget", 10000) # Get budget from context
    if output.total_cost > user_max_budget:
        return GuardrailFunctionOutput(
            output_info={"budget_exceeded": True, "original_cost": output.total_cost},
            tripwire_triggered=True,
            final_output_override=f"The planned trip to {output.destination} costs {output.total_cost} {output.currency}, which exceeds your budget of {user_max_budget} {output.currency}. Please adjust your preferences or budget."
        )
    return GuardrailFunctionOutput(output_info={"budget_exceeded": False}, tripwire_triggered=False)

budget_conscious_agent = Agent(
    name="Budget Conscious Agent",
    instructions="I plan trips within budget.",
    output_type=TravelPlanOutput,
    output_guardrails=[budget_compliance_check]
    # ... tools to generate TravelPlanOutput
)
```

## 8. Tracing and Debugging

The OpenAI Agents SDK includes tracing to monitor agent execution.

```python
from agents import Agent, Runner, trace
from agents.tracing import custom_span

# Example agent
my_agent = Agent(name="MyAgent", instructions="Perform a task.")

async def my_complex_task_function():
    with custom_span("sub_task_1", {"info": "details about sub_task_1"}):
        # ... some operations ...
        await asyncio.sleep(0.1) # Simulate work
    with custom_span("sub_task_2"):
        # ... other operations ...
        await asyncio.sleep(0.2) # Simulate work

async def main_workflow(user_query: str):
    # Named trace for the entire workflow
    with trace("TripSageUserRequestWorkflow"):
        # Agent run is automatically traced
        result = await Runner.run(my_agent, user_query)

        # Custom spans for non-agent parts of the workflow
        with custom_span("PostProcessingAgentResponse"):
            # ... logic to process agent's result ...
            processed_output = result.final_output.upper() if result.final_output else "NO OUTPUT"

        await my_complex_task_function()
        return processed_output

# To view traces, you'd typically integrate with an observability platform
# or use the SDK's built-in mechanisms if available for local inspection.
# For example, if LangSmith or a similar tool is configured:
# os.environ["LANGCHAIN_API_KEY"] = "your_langsmith_key"
# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_PROJECT"] = "TripSage_Agent_Traces"
```

**Sensitive Data Protection in Traces**:
Use `RunConfig(trace_include_sensitive_data=False)` when running an agent if inputs/outputs might contain PII that shouldn't be logged.

## 9. Testing Agents

Testing agents involves mocking their tools and verifying their reasoning or final output.

```python
import pytest
from unittest.mock import AsyncMock, patch
from agents import Agent, Runner, function_tool
from pydantic import BaseModel

# Define a simple tool and its params for testing
class MockToolParams(BaseModel):
    data: str

@function_tool
async def mock_tool(params: MockToolParams) -> Dict[str, Any]:
    if params.data == "success_case":
        return {"status": "Tool executed successfully", "processed_data": params.data.upper()}
    elif params.data == "error_case":
        return {"error": True, "message": "Tool failed as expected for error case"}
    return {"status": "Unknown tool input"}

@pytest.fixture
def test_agent():
    agent = Agent(
        name="TestAgent",
        instructions="Use mock_tool to process data. If data is 'success_case', confirm success. If 'error_case', report the error.",
        tools=[mock_tool],
        model="gpt-3.5-turbo" # Use a fast model for testing
    )
    return agent

@pytest.mark.asyncio
# Patch the actual tool execution if it makes external calls or has complex logic
# For this example, our mock_tool is simple, so we might not need to patch its internals,
# but rather test the agent's interaction with its defined schema and output.
async def test_agent_handles_tool_success(test_agent):
    # We are testing the agent's ability to correctly call the tool and interpret its success.
    # The tool itself is simple, but in a real scenario, the tool's *internal logic*
    # would be unit-tested separately. Here, we test the *agent's usage* of the tool.

    # If mock_tool made external calls, we'd patch `mock_tool` itself or its dependencies.
    # For instance, if mock_tool used an MCP client:
    # with patch('path.to.mcp_client.actual_mcp_method', new_callable=AsyncMock) as patched_mcp_call:
    #     patched_mcp_call.return_value = {"status": "Tool executed successfully", "processed_data": "SUCCESS_CASE"}

    result = await Runner.run(test_agent, "Process data: success_case")

    assert result.final_output is not None
    assert "successfully" in result.final_output.lower()
    assert "SUCCESS_CASE" in result.final_output # Check if agent used processed data

@pytest.mark.asyncio
async def test_agent_handles_tool_error(test_agent):
    result = await Runner.run(test_agent, "Process data: error_case")

    assert result.final_output is not None
    assert "error" in result.final_output.lower() or "failed" in result.final_output.lower()
    assert "Tool failed as expected" in result.final_output
```

This comprehensive guide should provide a solid foundation for designing, implementing, and optimizing AI agents within the TripSage system. Remember to keep prompts clear, tools well-defined, and to leverage the SDK's features for handoffs, guardrails, and tracing.
