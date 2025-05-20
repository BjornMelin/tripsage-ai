# TripSage Agent Handoffs Architecture

This document outlines the simplified and optimized architecture for agent handoffs in the TripSage travel planning platform, leveraging the built-in capabilities of the OpenAI Agents SDK.

## Table of Contents

- [Introduction](#introduction)
- [Agent Handoff Patterns](#agent-handoff-patterns)
- [Core Architecture](#core-architecture)
- [Implementation Best Practices](#implementation-best-practices)
- [Error Handling and Fallbacks](#error-handling-and-fallbacks)
- [Debugging and Tracing](#debugging-and-tracing)
- [Usage Examples](#usage-examples)
- [Testing and Validation](#testing-and-validation)
- [Performance Considerations](#performance-considerations)

## Introduction

Agent handoffs are a critical capability in multi-agent systems that allow for specialization, modularity, and improved user experiences. In TripSage, we implement two primary handoff patterns using the OpenAI Agents SDK:

1. **Full Handoffs**: Complete transfer of conversation control to a specialist agent
2. **Delegations**: Using specialist agents as tools without transferring control

Our implementation prioritizes simplicity and maintainability while preserving essential functionality.

## Agent Handoff Patterns

### Pattern 1: Triage with Specialized Agents (Recommended)

The most effective pattern for travel applications involves a main triage agent that orchestrates handoffs to domain-specific agents. This follows OpenAI's recommended "decentralized pattern" for agent handoffs:

```plaintext
User → TravelAgent (Triage) → Specialized Agents (Flight, Accommodation, Itinerary, etc.)
```

This pattern enables:

- Clear separation of responsibilities
- Focused expertise in specialized domains
- Simplified maintenance and updates
- Dynamic scaling of capabilities

### Pattern 2: Dynamic Routing Based on Intent

Advanced handoffs can use intent detection to dynamically determine the appropriate specialist:

```plaintext
User → Intent Analyzer → Appropriate Specialist → Further Sub-specialists if needed
```

### Pattern 3: Hierarchical Agent Organizations

For complex travel planning, a hierarchical approach works well:

```plaintext
User → Executive Agent → Department Heads → Specialist Agents
```

## Core Architecture

Our architecture leverages the built-in handoff capabilities of the OpenAI Agents SDK with minimal customization:

1. **Direct Agent Registration**:

   ```python
   travel_agent = Agent(
       name="Travel Agent",
       handoffs=[flight_agent, accommodation_agent]
   )
   ```

2. **Customized Handoffs**:

   ```python
   from agents import handoff
   
   travel_agent = Agent(
       name="Travel Agent",
       handoffs=[
           handoff(
               agent=flight_agent,
               tool_name_override="flight_specialist",
               tool_description_override="Transfer to flight specialist for booking assistance",
               input_filter=handoff_filters.preserve_user_messages,
               on_handoff=flight_announcement_callback
           ),
           # Additional handoffs...
       ]
   )
   ```

3. **TripSage Helper Functions**:
   - `create_travel_handoff()`: Creates handoffs with travel-specific defaults
   - `register_travel_handoffs()`: Registers multiple handoffs with consistent configuration
   - `create_user_announcement()`: Creates user-friendly handoff messages
   - `handle_handoff_error()`: Provides standardized error handling for handoff failures

## Implementation Best Practices

### 1. Clearly Defined Agent Roles

Each agent should have:

- Specific, non-overlapping domain of expertise
- Clear instructions on when to handle vs. when to delegate
- Well-defined input and output expectations

### 2. Context Preservation

The OpenAI Agents SDK provides built-in input filters for preserving context:

```python
from agents.extensions import handoff_filters

handoff(
    agent=specialist_agent,
    input_filter=handoff_filters.preserve_user_messages
)
```

### 3. User Experience

Implement user-friendly handoff announcements with the `on_handoff` callback:

```python
async def flight_announcement(ctx, input_data=None):
    announcement = f"👋 I'm connecting you with our Flight Specialist to help with your request."
    # Send announcement to user
    print(announcement)

handoff(
    agent=flight_agent,
    on_handoff=flight_announcement
)
```

### 4. Structured Inputs

Use Pydantic models for structured handoff inputs when additional data is needed:

```python
from pydantic import BaseModel

class FlightSearch(BaseModel):
    departure: str
    destination: str
    date: str
    budget: Optional[str] = None

handoff(
    agent=flight_agent,
    input_type=FlightSearch
)
```

### 5. Handoff Patterns

- **Sequential vs Cyclical**: Design for sequential, one-way handoffs rather than cyclical patterns
- **Clear Boundaries**: Establish clear boundaries of responsibility between agents
- **Deterministic Routing**: Make handoff decisions deterministic and explainable
- **Tool Composition**: Prefer tool composition over excessive handoffs for simple operations

## Error Handling and Fallbacks

Implementing robust error handling is essential for reliable handoffs:

```python
from agents import trace

async def handle_handoff_error(ctx, error, handoff_details):
    """Handle handoff errors with appropriate fallback responses"""
    # Log the error with tracing information
    with trace("HandoffErrorHandling"):
        # Create user-friendly error message
        error_message = f"I apologize, but I'm having trouble connecting to our {handoff_details['name']} specialist. Let me help you directly instead."
        
        # Return to main agent with context preserved
        return {
            "status": "error",
            "message": error_message,
            "error": str(error),
            "fallback": "main_agent"
        }

# In handoff configuration
handoff_configs = {
    "flight_specialist": {
        "agent": flight_agent,
        "description": "Transfer to a flight specialist for detailed flight search and booking",
        "input_model": FlightInput,
        "preserve_context": True,
        "announcement_callback": flight_announcement,
        "fallback_handler": handle_handoff_error
    }
}

# In agent implementation when processing handoffs
try:
    result = await travel_agent.process_handoff()
    if result.get("status") == "error":
        # Use fallback handling
        await handle_fallback(result, ctx)
except Exception as e:
    # Handle unexpected errors
    await handle_handoff_error(ctx, e, {"name": "specialist"})
```

### Common Fallback Strategies

1. **Main Agent Resolution**: Return to the main agent to handle the task directly
2. **Alternative Specialist**: Try an alternative specialist agent for the same task
3. **Degraded Capability**: Continue with limited functionality, clearly communicating limitations
4. **Graceful Termination**: If a critical handoff fails, gracefully end the interaction with clear explanation

## Debugging and Tracing

The OpenAI Agents SDK provides built-in tracing capabilities that are invaluable for debugging handoff issues:

```python
from agents import trace, custom_span

async def process_travel_handoff(travel_agent, user_query, context):
    # Create a named trace for the entire handoff workflow
    with trace("TravelHandoffWorkflow"):
        # Agent run is automatically traced
        result = await Runner.run(travel_agent, user_query, context)
        
        # Check if this is a handoff
        if result.handoff_attempted:
            # Add custom span for handoff result processing
            with custom_span("ProcessHandoffResult", {"handoff_to": result.handoff_target}):
                # Process handoff result logic
                pass
        
        return result
```

### Debugging Best Practices

1. **Use Named Traces**: Create named traces for specific workflows
2. **Custom Spans**: Add custom spans for non-agent operations
3. **Context Attributes**: Include relevant context attributes in spans
4. **Structured Logging**: Log handoff events with structured data
5. **Error Categorization**: Categorize errors for better debugging

The traces provide visibility into:
- Agent thought processes
- Tool calls and parameters
- Handoff events and targets
- Error states and exceptions

## Usage Examples

### Basic Handoff Registration

```python
from agents import Agent

# Create specialized agents
flight_agent = Agent(name="Flight Agent", instructions="You are a flight specialist...")
accommodation_agent = Agent(name="Accommodation Agent", instructions="You are an accommodation specialist...")

# Create main travel agent with handoffs
travel_agent = Agent(
    name="Travel Agent",
    instructions="""You are a travel planning assistant.
    When users ask about flights, use the transfer_to_flight_agent tool.
    When users ask about accommodations, use the transfer_to_accommodation_agent tool.
    """,
    handoffs=[flight_agent, accommodation_agent]
)
```

### Enhanced Handoffs with TripSage Helpers

```python
from tripsage.agents.handoffs import create_travel_handoff, register_travel_handoffs, handle_handoff_error
from pydantic import BaseModel

# Define structured input model
class FlightInput(BaseModel):
    departure: str
    destination: str
    date: str

# Create announcement callback
async def flight_announcement(ctx, input_data: FlightInput):
    announcement = f"👋 I'm connecting you with our Flight Specialist to help with your {input_data.departure} to {input_data.destination} trip."
    # Send announcement to user
    print(announcement)

# Create handoff configurations
handoff_configs = {
    "flight_specialist": {
        "agent": flight_agent,
        "description": "Transfer to a flight specialist for detailed flight search and booking",
        "input_model": FlightInput,
        "preserve_context": True,
        "announcement_callback": flight_announcement,
        "fallback_handler": handle_handoff_error
    },
    "accommodation_specialist": {
        "agent": accommodation_agent,
        "description": "Transfer to an accommodation specialist for hotel and rental search",
        "preserve_context": True,
        "fallback_handler": handle_handoff_error
    },
    # Additional handoffs...
}

# Register all handoffs with trace for debugging
with trace("RegisterTravelHandoffs"):
    register_travel_handoffs(travel_agent, handoff_configs)
```

## Testing and Validation

To ensure reliable handoffs, implement comprehensive testing:

1. **Unit Tests**: Test the handoff configuration and registration
2. **Integration Tests**: Test handoff flows between agents
3. **Error Handling Tests**: Verify fallback mechanisms for handoff failures
4. **User Experience Tests**: Verify handoff announcements and context preservation
5. **Trace Testing**: Verify tracing functionality captures expected events

### Test Case Example

```python
@pytest.mark.asyncio
async def test_handoff_error_handling():
    # Create mock agents with controlled failure
    main_agent = MockAgent(name="Main")
    failing_agent = MockAgent(name="Failing", simulate_error=True)
    
    # Configure handoff with error handler
    main_agent.register_handoff(
        create_travel_handoff(
            failing_agent, 
            "failing_specialist",
            "Test failing handoff",
            fallback_handler=handle_handoff_error
        )
    )
    
    # Execute handoff that will fail
    result = await Runner.run(main_agent, "I need help from the failing specialist")
    
    # Verify error handling
    assert "I apologize, but I'm having trouble connecting" in result.final_output
    assert result.handoff_attempted
    assert not result.handoff_succeeded
```

## Performance Considerations

1. **Minimize Context Size**: Only preserve essential conversation history
2. **Structured Inputs**: Use structured inputs for complex handoffs instead of passing large context
3. **Handoff Prompt Optimization**: Include clear handoff instructions in agent prompts
4. **Sequential Design**: Prefer sequential, deterministic handoff patterns
5. **Timeout Management**: Implement appropriate timeouts for handoff operations

By implementing this optimized architecture, TripSage achieves efficient, reliable agent handoffs with minimal complexity and maximum maintainability.
