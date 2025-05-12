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
