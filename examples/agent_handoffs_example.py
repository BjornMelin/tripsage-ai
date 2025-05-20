"""
Example script demonstrating agent handoffs in TripSage.

This script shows how to use the handoff capabilities in TripSage,
including both full handoffs and delegations between specialized agents.
"""

import asyncio
import logging
from typing import Any, Dict, List

from tripsage.agents.travel import TravelAgent
from tripsage.utils.logging import setup_logging

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)


async def simulate_conversation(
    agent: TravelAgent, messages: List[str], context: Dict[str, Any] = None
) -> None:
    """Simulate a conversation with an agent.

    Args:
        agent: Agent to converse with
        messages: List of user messages
        context: Optional context data
    """
    # Initialize context
    run_context = context or {"user_id": "example_user"}

    # Track the current active agent
    current_agent = agent

    # Process each message
    for i, message in enumerate(messages):
        print(f"\n[USER Message {i + 1}]: {message}")

        # Run the current agent
        response = await current_agent.run(message, context=run_context)

        # Check if this is a handoff
        if response.get("status") == "handoff":
            print(f"\n[AGENT {current_agent.name}]: {response.get('content', '')}")
            print(
                f"\n--- Detected handoff to {response.get('handoff_target')} "
                f"via {response.get('handoff_tool')} ---"
            )

            # Process the handoff
            handoff_response = await current_agent.process_handoff_result(
                response, context=run_context
            )

            # Print the response from the handoff
            if handoff_response.get("status") == "success":
                # For successful handoffs, print the content
                print(
                    f"\n[AGENT {handoff_response.get('handoff_to', 'Specialist')}]: "
                    f"{handoff_response.get('content', '')}"
                )
            else:
                # For failed handoffs, print the error
                print(
                    f"\n[HANDOFF ERROR]: "
                    f"{handoff_response.get('content', 'Unknown error')}"
                )

        else:
            # Normal response (no handoff)
            print(f"\n[AGENT {current_agent.name}]: {response.get('content', '')}")

            # Print tool calls for transparency
            if "tool_calls" in response and response["tool_calls"]:
                print("\nTool Calls:")
                for tool_call in response["tool_calls"]:
                    print(f"  - {tool_call.get('name', 'unknown')}")


async def simulate_delegation(
    agent: TravelAgent, message: str, context: Dict[str, Any] = None
) -> None:
    """Simulate a delegation to a specialized agent without losing control.

    Args:
        agent: Main agent that will delegate
        message: User message triggering the delegation
        context: Optional context data
    """
    # Initialize context
    run_context = context or {"user_id": "example_user"}

    print(f"\n[USER]: {message}")

    # Run the agent with the message
    response = await agent.run(message, context=run_context)

    # Print the response
    print(f"\n[AGENT {agent.name}]: {response.get('content', '')}")

    # Check if delegation tools were used
    if "tool_calls" in response and response["tool_calls"]:
        for tool_call in response["tool_calls"]:
            tool_name = tool_call.get("name", "")

            # Check if this is a delegation tool
            if tool_name in agent._delegation_tools:
                target_agent = agent._delegation_tools[tool_name]["target_agent"]
                print(
                    f"\n--- Detected delegation to {target_agent} via {tool_name} ---"
                )
                print(f"[DELEGATION RESULT]: Tool returned result from {target_agent}")


async def run_handoff_example():
    """Run an example of agent handoffs."""
    # Create the main travel agent
    travel_agent = TravelAgent()

    # Example conversation with handoffs
    flight_conversation = [
        "I'm planning a trip from New York to Los Angeles",
        "I need to find the cheapest flights for next week",
        "Are there any direct flights available?",
    ]

    print("\n=== Example 1: Handoff to Flight Agent ===")
    await simulate_conversation(travel_agent, flight_conversation)

    # Example conversation with accommodation handoff
    accommodation_conversation = [
        "I'm traveling to San Francisco next month",
        "I need a hotel near Fisherman's Wharf",
        "What are the best-rated hotels in that area?",
    ]

    print("\n\n=== Example 2: Handoff to Accommodation Agent ===")
    await simulate_conversation(travel_agent, accommodation_conversation)

    # Example of delegation without handoff
    print("\n\n=== Example 3: Delegation Without Handoff ===")
    await simulate_delegation(
        travel_agent,
        "Can you give me a quick budget estimate for a 3-day trip to Miami?",
    )


if __name__ == "__main__":
    asyncio.run(run_handoff_example())
