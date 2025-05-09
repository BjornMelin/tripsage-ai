# TripSage Agents

This directory contains the implementation of the OpenAI Agents SDK integration for the TripSage travel planning system.

## Overview

The agents module provides a set of AI-powered agents that help users plan their travel. The system uses the OpenAI Assistants API to create agents with specialized functions for different aspects of travel planning.

## Components

- `config.py` - Configuration settings for the agents
- `base_agent.py` - Base class for all agents with core functionality
- `travel_agent.py` - Primary agent for travel planning

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

## Agent Architecture

TripSage uses a primary Travel Agent that coordinates the overall planning process and delegates to specialized agents:

1. **Travel Agent**: The primary agent that handles user interaction and coordinates the planning process.

   - Understands user preferences and constraints
   - Creates personalized travel itineraries
   - Makes high-level recommendations

2. **Flight Agent** (to be implemented): Specialized agent for flight search and booking.

   - Searches for flight options based on user criteria
   - Compares prices and schedules
   - Tracks price history and suggests optimal booking times

3. **Accommodation Agent** (to be implemented): Specialized agent for finding hotels and other accommodations.

   - Searches for accommodation options based on user preferences
   - Filters results by amenities, location, and price
   - Provides detailed information about properties

4. **Activities Agent** (to be implemented): Specialized agent for finding activities and attractions.

   - Recommends activities based on user interests
   - Optimizes scheduling of activities
   - Provides details about attractions and tours

5. **Budget Agent** (to be implemented): Specialized agent for budget optimization.
   - Tracks expenses across all travel components
   - Suggests budget-friendly alternatives
   - Helps users optimize their spending

## Agent Tools

The agents use function tools to interact with external services and the TripSage database:

- `search_flights` - Search for flight options
- `search_accommodations` - Search for accommodation options
- `search_activities` - Search for activities and attractions
- `create_trip` - Create a new trip in the database

## Usage

```python
from travel_agent import TravelAgent

# Create a travel agent
agent = TravelAgent()

# Create a new thread
agent.create_thread()

# Add a user message
agent.add_message("I want to plan a trip to New York for a week in June 2025 with a budget of $2000.")

# Run the agent
agent.run_thread()

# Get the agent's response
response = agent.get_last_response()
print(response)
```
