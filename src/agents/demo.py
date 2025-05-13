#!/usr/bin/env python3
"""
Demo script to test the TripSage Travel Planning Agent.

This module provides an interactive demo of the TripSage Travel Planning Agent
using the hierarchical agent structure implemented with the OpenAI Agents SDK.
"""

import argparse
import asyncio
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

from .travel_planning_agent import create_agent


async def run_interactive_demo():
    """Run an interactive demo of the TripSage Travel Planning Agent."""
    # Load environment variables
    load_dotenv()

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it in your .env file or environment.")
        sys.exit(1)

    # Display demo options
    print("\nTripSage Travel Planning Agent Demo")
    print("-----------------------------------")
    print("This demo allows you to interact with the TripSage Travel Planning Agent.")
    print("The agent coordinates specialized sub-agents for different travel domains:")
    print("- Flight search and booking")
    print("- Accommodation search and booking")
    print("- Destination research")
    print("- Budget optimization")
    print("- Detailed itinerary planning")
    print("\nYou can ask about trip planning, search for flights/accommodations, etc.")
    print("Type 'exit', 'quit', or 'bye' to end the conversation.\n")

    # Create the agent
    print("Initializing TripSage Travel Planning Agent...")
    agent = create_agent()

    # Interactive session
    while True:
        # Get user input
        user_message = input("You: ")

        # Check for exit command
        if user_message.lower() in ["exit", "quit", "bye"]:
            print("Ending conversation. Goodbye!")
            break

        if not user_message.strip():
            continue

        # Create context for the agent run (would include user_id in a real app)
        context = {
            "session_id": agent.session_id,
        }

        # Run the agent
        try:
            print("Processing your request...")
            response = await agent.run(user_message, context=context)

            # Print the response
            if response.get("status") == "success":
                print("\nAgent:", response.get("content", "No response"))
            else:
                print("\nError:", response.get("error_message", "Unknown error"))

        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")

        print()


async def run_batch_queries(queries: List[str]) -> List[Dict[str, Any]]:
    """Run a batch of queries through the TripSage Travel Planning Agent.

    Args:
        queries: List of queries to process

    Returns:
        List of responses
    """
    print("TripSage Travel Planning Agent Batch Demo")
    print("=======================================")

    # Create the agent
    agent = create_agent()

    responses = []
    context = {
        "session_id": agent.session_id,
    }

    # Process each query
    for i, query in enumerate(queries, 1):
        print(f"\nProcessing query {i}/{len(queries)}: {query}")

        try:
            # Run the agent
            response = await agent.run(query, context=context)
            responses.append(response)

            # Print the response
            if response.get("status") == "success":
                print("\nAgent Response:")
                print(response.get("content", "No response"))
            else:
                print("\nError:", response.get("error_message", "Unknown error"))

        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            responses.append({"status": "error", "error_message": str(e)})

        # Small delay between queries
        if i < len(queries):
            await asyncio.sleep(1)

    return responses


def main():
    """Main entry point for the demo script."""
    # Load environment variables
    load_dotenv()

    parser = argparse.ArgumentParser(description="TripSage Travel Planning Agent Demo")
    parser.add_argument(
        "--queries",
        "-q",
        nargs="+",
        help="Run with specific queries instead of interactive mode",
    )

    args = parser.parse_args()

    if args.queries:
        asyncio.run(run_batch_queries(args.queries))
    else:
        asyncio.run(run_interactive_demo())


if __name__ == "__main__":
    main()
