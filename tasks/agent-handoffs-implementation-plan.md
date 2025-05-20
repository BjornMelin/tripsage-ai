# TripSage Agent Handoffs Implementation Plan

## Overview

This document outlines the optimized implementation strategy for agent handoffs in the TripSage system. Agent handoffs are a critical mechanism for creating a modular, extensible agent system that allows specialized agents (flight, accommodation, budget, etc.) to collaborate effectively on complex travel planning tasks.

## Current Architecture

TripSage's agent architecture consists of:
- **TravelAgent** - Main orchestrator agent
- **FlightAgent** - Specialized flight search and booking
- **AccommodationAgent** - Hotel and rental search and booking 
- **BudgetAgent** - Budget planning and optimization
- **DestinationResearchAgent** - Destination information and research
- **ItineraryAgent** - Itinerary creation and management

## Implementation Strategy

We will implement handoffs using the built-in capabilities of the OpenAI Agents SDK with minimal custom code, following the recommended "decentralized pattern" where agents transfer control directly to specialists:

1. **Direct Agent Handoffs**: Using the `handoffs` parameter for simple handoffs
2. **Customized Handoffs**: Using the `handoff()` function for enhanced handoffs
3. **Helper Functions**: Implementing minimal helper functions for TripSage-specific needs

### Implementation Plan

The implementation will be divided into three phases:

## Phase 1: Core Implementation (2 days)

- [ ] **Create core handoff helper module `tripsage/agents/handoffs/helper.py`**:
  - [ ] Implement `create_travel_handoff()` function for creating customized handoffs
  - [ ] Implement `register_travel_handoffs()` for registering multiple handoffs
  - [ ] Implement `create_user_announcement()` for user-friendly messages
  - [ ] Add `handle_handoff_error()` helper for standardized error handling
  - [ ] Update `__init__.py` to expose the helper functions

- [ ] **Add unit tests for the helper module**:
  - [ ] Test handoff creation
  - [ ] Test handoff registration
  - [ ] Test announcement generation
  - [ ] Test error handling mechanisms

## Phase 2: Agent Integration (2 days)

- [ ] **Update TravelAgent in `travel.py`**:
  - [ ] Create specialized agents
  - [ ] Define handoff configurations with appropriate settings
  - [ ] Register handoffs using the helper functions
  - [ ] Implement fallback mechanisms for handoff failures
  - [ ] Update agent instructions to properly utilize handoffs

- [ ] **Define structured input models**:
  - [ ] Create `FlightInput` for flight handoffs
  - [ ] Create `AccommodationInput` for accommodation handoffs
  - [ ] Create other domain-specific input models as needed

- [ ] **Implement announcement callbacks**:
  - [ ] Create callback for flight handoffs
  - [ ] Create callback for accommodation handoffs
  - [ ] Create callbacks for other agent types

## Phase 3: Testing and Refinement (2 days)

- [ ] **Add integration tests**:
  - [ ] Test handoff flows between agents
  - [ ] Test context preservation in handoffs
  - [ ] Test error handling scenarios and fallback mechanisms
  - [ ] Test tracing capabilities for debugging
  - [ ] Add the tests to `tests/agents/test_handoffs.py`

- [ ] **Add documentation**:
  - [ ] Update `CONSOLIDATED_AGENT_HANDOFFS.md` with implementation details
  - [ ] Add usage examples and best practices
  - [ ] Document error handling and fallback strategies
  - [ ] Include debugging and tracing guidance

## Implementation Details

### Handoff Configuration

```python
from agents import Agent, handoff, trace
from agents.extensions import handoff_filters
from pydantic import BaseModel
from tripsage.agents.handoffs import create_travel_handoff, register_travel_handoffs, handle_handoff_error

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

# Register all handoffs with the travel agent
register_travel_handoffs(travel_agent, handoff_configs)
```

### Error Handling and Fallbacks

```python
# In helper.py
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

# Usage in travel.py when processing handoff results
result = await travel_agent.process_handoff()
if result.get("status") == "error":
    # Use fallback handling
    await handle_fallback(result, ctx)
```

## Best Practices for Implementation

1. **Context Preservation**
   - Use the built-in `handoff_filters.preserve_user_messages` for context filtering
   - Only preserve essential context to minimize overhead
   - Add structured inputs for complex parameters

2. **User Experience**
   - Create clear, friendly handoff announcements via callbacks
   - Notify users about the handoff purpose and expert capabilities
   - Set appropriate expectations for handoffs
   - Provide graceful error handling with helpful messages

3. **Performance Considerations**
   - Only preserve essential conversation history
   - Use structured inputs for complex handoffs instead of large contexts
   - Optimize handoff prompt instructions

4. **Handoff Pattern Considerations**
   - Design for sequential handoffs (avoid circular patterns)
   - Implement one-way transfers with clear responsibilities
   - Ensure handoffs are well-defined and deterministic
   - Use tracing for debugging complex handoff flows

5. **Error Handling and Debugging**
   - Implement fallback mechanisms for handoff failures
   - Use the SDK's tracing capabilities for debugging
   - Log all handoff events for auditing and troubleshooting
   - Create comprehensive test suite covering failure scenarios

## Timeline

- **Total Estimated Time**: 6 developer days
- **Phase 1**: 2 days
- **Phase 2**: 2 days
- **Phase 3**: 2 days

## Resources Required

- 1 Backend Developer (Python/OpenAI Agents SDK)
- Access to test environment with sample user data

## Expected Outcomes

1. Lightweight, maintainable agent handoff implementation
2. Seamless transitions between specialized agents
3. Excellent user experience during handoffs
4. Robust error handling and fallback mechanisms
5. Comprehensive test coverage
6. Clear documentation including debugging guidance