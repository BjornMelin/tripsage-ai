import asyncio
import sys
from typing import Any, Dict

from src.agents.travel_planning_agent import create_agent
from src.utils.logging import get_module_logger
from src.utils.settings_init import init_settings

logger = get_module_logger(__name__)


async def run_agent(query: str) -> Dict[str, Any]:
    """Run the TripSage Travel Planning Agent with the given query.

    Args:
        query: User query to process

    Returns:
        Agent response
    """
    # Create the agent
    agent = create_agent()

    # Run the agent with the query
    response = await agent.run(query)

    return response


def main():
    """Main entry point for the TripSage Travel Planning Agent CLI."""
    try:
        print("TripSage Travel Planning Agent")
        print("============================")

        # Initialize settings
        logger.info("Initializing TripSage application")
        settings = init_settings()
        logger.info(f"TripSage initialized in {settings.environment} environment")

        # Get query from command line arguments or prompt
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
        else:
            query = input("Enter your travel query: ")

        if not query.strip():
            print("Please provide a travel query")
            return

        # Run the agent
        response = asyncio.run(run_agent(query))

        # Print the response
        if response.get("status") == "success":
            print("\nTravel Planning Agent Response:")
            print(response.get("content", "No response"))
        else:
            print("\nError:", response.get("error_message", "Unknown error"))

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        logger.exception("Unexpected error in main: %s", str(e))
        print(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    main()
