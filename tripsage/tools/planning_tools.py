"""
Planning tools for TripSage travel planning agent.

This module provides function tools for travel planning operations used by the
TravelPlanningAgent, including plan creation, updates, and persistence.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from tripsage_core.services.business import MemoryService
from tripsage_core.utils.cache_utils import redis_cache
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.error_handling_utils import log_exception
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class TravelPlanInput(BaseModel):
    """Input model for travel plan creation and updates."""

    user_id: str = Field(..., description="User ID")
    title: str = Field(..., description="Plan title")
    destinations: list[str] = Field(..., description="List of destinations")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    travelers: int = Field(1, description="Number of travelers")
    budget: float | None = Field(None, description="Total budget")
    preferences: dict[str, Any] | None = Field(None, description="User preferences")


class TravelPlanUpdate(BaseModel):
    """Input model for travel plan updates."""

    plan_id: str = Field(..., description="Travel plan ID")
    user_id: str = Field(..., description="User ID")
    updates: dict[str, Any] = Field(..., description="Fields to update")


class SearchResultInput(BaseModel):
    """Input model for combining search results."""

    flight_results: dict[str, Any] | None = Field(
        None, description="Flight search results"
    )
    accommodation_results: dict[str, Any] | None = Field(
        None, description="Accommodation search results"
    )
    activity_results: dict[str, Any] | None = Field(
        None, description="Activity search results"
    )
    destination_info: dict[str, Any] | None = Field(
        None, description="Destination information"
    )
    user_preferences: dict[str, Any] | None = Field(
        None, description="User preferences"
    )


@with_error_handling()
async def create_travel_plan(params: dict[str, Any]) -> dict[str, Any]:
    """Create a new travel plan with basic information.

    Creates an initial travel plan with core details like destinations, dates,
    and budget.

    Args:
        params: Travel plan parameters:
            user_id: User ID
            title: Plan title
            destinations: List of destinations
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            travelers: Number of travelers
            budget: Total budget (optional)
            preferences: User preferences (optional)

    Returns:
        Dictionary with created plan details
    """
    try:
        # Validate input
        plan_input = TravelPlanInput(**params)

        # Generate plan ID
        plan_id = f"plan_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Create travel plan object
        travel_plan = {
            "plan_id": plan_id,
            "user_id": plan_input.user_id,
            "title": plan_input.title,
            "destinations": plan_input.destinations,
            "start_date": plan_input.start_date,
            "end_date": plan_input.end_date,
            "travelers": plan_input.travelers,
            "budget": plan_input.budget,
            "preferences": plan_input.preferences or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "components": {
                "flights": [],
                "accommodations": [],
                "activities": [],
                "transportation": [],
                "notes": [],
            },
        }

        # Cache the travel plan
        cache_key = f"travel_plan:{plan_id}"
        await redis_cache.set(cache_key, travel_plan, ttl=86400 * 7)  # 7 days

        # Create memory entities for the plan
        # Using Mem0 direct SDK integration for memory management
        try:
            # Initialize direct Mem0 service
            memory_service = MemoryService()
            await memory_service.connect()

            # Create memory for the travel plan
            plan_memory = (
                f"Travel plan '{plan_input.title}' created for user "
                f"{plan_input.user_id}"
            )
            plan_memory += f" with destinations: {', '.join(plan_input.destinations)}"
            plan_memory += f" from {plan_input.start_date} to {plan_input.end_date}"
            plan_memory += f" for {plan_input.travelers} travelers"

            if plan_input.budget:
                plan_memory += f" with budget ${plan_input.budget}"

            # Add the memory using Mem0
            await memory_service.add_conversation_memory(
                messages=[
                    {"role": "system", "content": "Travel plan created"},
                    {"role": "user", "content": plan_memory},
                ],
                user_id=plan_input.user_id,
                metadata={
                    "plan_id": plan_id,
                    "type": "travel_plan",
                    "destinations": plan_input.destinations,
                    "start_date": plan_input.start_date,
                    "end_date": plan_input.end_date,
                    "travelers": plan_input.travelers,
                    "budget": plan_input.budget,
                },
            )

        except Exception as e:
            logger.warning(f"Error creating memory entities: {str(e)}")
            # Continue even if memory creation fails

        return {
            "success": True,
            "plan_id": plan_id,
            "message": "Travel plan created successfully",
            "plan": travel_plan,
        }

    except Exception as e:
        logger.error(f"Error creating travel plan: {str(e)}")
        log_exception(e)
        return {"success": False, "error": f"Travel plan creation error: {str(e)}"}


@with_error_handling()
async def update_travel_plan(params: dict[str, Any]) -> dict[str, Any]:
    """Update an existing travel plan with new information.

    Updates specific fields in a travel plan, such as adding components or
    modifying dates.

    Args:
        params: Update parameters:
            plan_id: Travel plan ID
            user_id: User ID
            updates: Dictionary of fields to update

    Returns:
        Dictionary with updated plan details
    """
    try:
        # Validate input
        update_input = TravelPlanUpdate(**params)

        # Get the existing plan
        cache_key = f"travel_plan:{update_input.plan_id}"
        travel_plan = await redis_cache.get(cache_key)

        if not travel_plan:
            return {
                "success": False,
                "error": f"Travel plan {update_input.plan_id} not found",
            }

        # Check user authorization
        if travel_plan.get("user_id") != update_input.user_id:
            return {"success": False, "error": "Unauthorized to update this plan"}

        # Update fields
        for key, value in update_input.updates.items():
            if key in travel_plan:
                travel_plan[key] = value

        # Update the modification timestamp
        travel_plan["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Save the updated plan
        await redis_cache.set(cache_key, travel_plan, ttl=86400 * 7)  # 7 days

        # Update memory entity
        # Using Mem0 direct SDK integration for memory management
        try:
            # Initialize direct Mem0 service
            memory_service = MemoryService()
            await memory_service.connect()

            # Create update memory
            update_memory = (
                f"Travel plan '{travel_plan.get('title', 'Untitled')}' updated"
            )
            update_details = []

            for key, value in update_input.updates.items():
                if key == "destinations":
                    update_details.append(f"destinations changed to {', '.join(value)}")
                elif key == "start_date" or key == "end_date":
                    update_details.append(f"{key} changed to {value}")
                elif key == "budget":
                    update_details.append(f"budget changed to ${value}")
                elif key == "title":
                    update_details.append(f"title changed to {value}")

            if update_details:
                update_memory += f" with changes: {', '.join(update_details)}"

                # Add the memory update using Mem0
                await memory_service.add_conversation_memory(
                    messages=[
                        {"role": "system", "content": "Travel plan updated"},
                        {"role": "user", "content": update_memory},
                    ],
                    user_id=update_input.user_id,
                    metadata={
                        "plan_id": update_input.plan_id,
                        "type": "travel_plan_update",
                        "changes": update_input.updates,
                    },
                )

        except Exception as e:
            logger.warning(f"Error updating memory entity: {str(e)}")
            # Continue even if memory update fails

        return {
            "success": True,
            "plan_id": update_input.plan_id,
            "message": "Travel plan updated successfully",
            "plan": travel_plan,
        }

    except Exception as e:
        logger.error(f"Error updating travel plan: {str(e)}")
        log_exception(e)
        return {"success": False, "error": f"Travel plan update error: {str(e)}"}


@with_error_handling()
async def combine_search_results(params: dict[str, Any]) -> dict[str, Any]:
    """Combine results from multiple search operations into a unified recommendation.

    Analyzes and combines flight, accommodation, and activity search results based on
    user preferences to create a comprehensive travel recommendation.

    Args:
        params: Search results to combine:
            flight_results: Flight search results
            accommodation_results: Accommodation search results
            activity_results: Activity search results
            destination_info: Destination information
            user_preferences: User preferences

    Returns:
        Dictionary with combined recommendations
    """
    try:
        # Validate input
        search_input = SearchResultInput(**params)

        # Combine results
        combined_results = {
            "recommendations": {
                "flights": [],
                "accommodations": [],
                "activities": [],
            },
            "total_estimated_cost": 0.0,
            "destination_highlights": [],
            "travel_tips": [],
        }

        # Process flight results
        if search_input.flight_results:
            flight_offers = search_input.flight_results.get("offers", [])
            if flight_offers:
                # Sort by price (assuming flight offers have total_amount field)
                sorted_flights = sorted(
                    flight_offers, key=lambda x: x.get("total_amount", float("inf"))
                )
                # Take top 3 flights
                combined_results["recommendations"]["flights"] = sorted_flights[:3]
                # Add to total cost estimate (using lowest price)
                if sorted_flights:
                    combined_results["total_estimated_cost"] += sorted_flights[0].get(
                        "total_amount", 0
                    )

        # Process accommodation results
        if search_input.accommodation_results:
            accommodations = search_input.accommodation_results.get(
                "accommodations", []
            )
            if accommodations:
                # Sort by a combination of price and rating
                for accommodation in accommodations:
                    # Normalize price by nights
                    accommodation["_score"] = (
                        accommodation.get("price_per_night", 0)
                        * -0.7  # Lower price is better
                        + accommodation.get("rating", 0)
                        * 0.3  # Higher rating is better
                    )
                sorted_accommodations = sorted(
                    accommodations,
                    key=lambda x: x.get("_score", float("-inf")),
                    reverse=True,
                )
                # Take top 3 accommodations
                combined_results["recommendations"]["accommodations"] = (
                    sorted_accommodations[:3]
                )
                # Add to total cost estimate (using first accommodation's
                # nightly rate * 3 nights)
                if sorted_accommodations:
                    combined_results["total_estimated_cost"] += (
                        sorted_accommodations[0].get("price_per_night", 0) * 3
                    )

        # Process activity results
        if search_input.activity_results:
            activities = search_input.activity_results.get("activities", [])
            if activities:
                # Sort by rating
                sorted_activities = sorted(
                    activities,
                    key=lambda x: x.get("rating", 0),
                    reverse=True,
                )
                # Take top 5 activities
                combined_results["recommendations"]["activities"] = sorted_activities[
                    :5
                ]
                # Add to total cost estimate (using top 3 activities)
                for _, activity in enumerate(sorted_activities[:3]):
                    combined_results["total_estimated_cost"] += activity.get(
                        "price_per_person", 0
                    )

        # Process destination information
        if search_input.destination_info:
            # Extract highlights
            highlights = search_input.destination_info.get("highlights", [])
            if highlights:
                combined_results["destination_highlights"] = highlights[:5]

            # Extract travel tips
            tips = search_input.destination_info.get("tips", [])
            if tips:
                combined_results["travel_tips"] = tips[:3]

        return {
            "success": True,
            "combined_results": combined_results,
            "message": "Search results combined successfully",
        }

    except Exception as e:
        logger.error(f"Error combining search results: {str(e)}")
        log_exception(e)
        return {"success": False, "error": f"Result combination error: {str(e)}"}


@with_error_handling()
async def generate_travel_summary(params: dict[str, Any]) -> dict[str, Any]:
    """Generate a comprehensive summary of a travel plan.

    Creates a user-friendly summary of a travel plan with key information
    and recommendations.

    Args:
        params: Summary generation parameters:
            plan_id: Travel plan ID
            user_id: User ID
            format: Summary format (text, markdown, html)

    Returns:
        Dictionary with generated summary
    """
    try:
        # Extract parameters
        plan_id = params.get("plan_id")
        user_id = params.get("user_id")
        format_type = params.get("format", "markdown")

        if not plan_id or not user_id:
            return {"success": False, "error": "Plan ID and user ID are required"}

        # Get the travel plan
        cache_key = f"travel_plan:{plan_id}"
        travel_plan = await redis_cache.get(cache_key)

        if not travel_plan:
            return {"success": False, "error": f"Travel plan {plan_id} not found"}

        # Check user authorization
        if travel_plan.get("user_id") != user_id:
            return {"success": False, "error": "Unauthorized to access this plan"}

        # Generate summary based on format
        summary = ""
        if format_type == "markdown":
            summary = _generate_markdown_summary(travel_plan)
        elif format_type == "text":
            summary = _generate_text_summary(travel_plan)
        elif format_type == "html":
            summary = _generate_html_summary(travel_plan)
        else:
            return {"success": False, "error": "Unsupported format type"}

        return {
            "success": True,
            "summary": summary,
            "format": format_type,
            "plan_id": plan_id,
        }

    except Exception as e:
        logger.error(f"Error generating travel summary: {str(e)}")
        log_exception(e)
        return {"success": False, "error": f"Summary generation error: {str(e)}"}


def _generate_markdown_summary(travel_plan: dict[str, Any]) -> str:
    """Generate a markdown summary of a travel plan.

    Args:
        travel_plan: Travel plan data

    Returns:
        Markdown-formatted summary
    """
    # Extract plan details
    title = travel_plan.get("title", "Travel Plan")
    destinations = travel_plan.get("destinations", [])
    start_date = travel_plan.get("start_date", "")
    end_date = travel_plan.get("end_date", "")
    travelers = travel_plan.get("travelers", 1)
    budget = travel_plan.get("budget")
    components = travel_plan.get("components", {})

    # Build the summary
    summary = f"# {title}\n\n"
    summary += "## Trip Overview\n\n"
    summary += f"**Destinations**: {', '.join(destinations)}\n\n"
    summary += f"**Dates**: {start_date} to {end_date}\n\n"
    summary += f"**Travelers**: {travelers}\n\n"

    if budget:
        summary += f"**Budget**: ${budget}\n\n"

    # Add flights if available
    flights = components.get("flights", [])
    if flights:
        summary += "## Flights\n\n"
        for i, flight in enumerate(flights, 1):
            summary += f"### Flight {i}\n\n"
            summary += f"* **From**: {flight.get('origin', 'N/A')}\n"
            summary += f"* **To**: {flight.get('destination', 'N/A')}\n"
            summary += f"* **Date**: {flight.get('departure_date', 'N/A')}\n"
            summary += f"* **Airline**: {flight.get('airline', 'N/A')}\n"
            summary += f"* **Price**: ${flight.get('price', 'N/A')}\n\n"

    # Add accommodations if available
    accommodations = components.get("accommodations", [])
    if accommodations:
        summary += "## Accommodations\n\n"
        for i, accommodation in enumerate(accommodations, 1):
            summary += f"### {accommodation.get('name', f'Accommodation {i}')}\n\n"
            summary += f"* **Location**: {accommodation.get('location', 'N/A')}\n"
            summary += f"* **Check-in**: {accommodation.get('check_in_date', 'N/A')}\n"
            summary += (
                f"* **Check-out**: {accommodation.get('check_out_date', 'N/A')}\n"
            )
            summary += (
                f"* **Price**: ${accommodation.get('price_per_night', 'N/A')} "
                f"per night\n\n"
            )

    # Add activities if available
    activities = components.get("activities", [])
    if activities:
        summary += "## Activities\n\n"
        for i, activity in enumerate(activities, 1):
            summary += f"### {activity.get('name', f'Activity {i}')}\n\n"
            summary += f"* **Location**: {activity.get('location', 'N/A')}\n"
            summary += f"* **Date**: {activity.get('date', 'N/A')}\n"
            summary += (
                f"* **Price**: ${activity.get('price_per_person', 'N/A')} "
                f"per person\n\n"
            )

    # Add notes if available
    notes = components.get("notes", [])
    if notes:
        summary += "## Notes\n\n"
        for note in notes:
            summary += f"* {note}\n"

    return summary


def _generate_text_summary(travel_plan: dict[str, Any]) -> str:
    """Generate a plain text summary of a travel plan.

    Args:
        travel_plan: Travel plan data

    Returns:
        Plain text-formatted summary
    """
    # This would convert the markdown summary to plain text
    # For simplicity, we're just using a basic implementation
    markdown = _generate_markdown_summary(travel_plan)
    text = markdown.replace("# ", "").replace("## ", "").replace("### ", "")
    text = text.replace("**", "").replace("*", "").replace("\n\n", "\n")
    return text


def _generate_html_summary(travel_plan: dict[str, Any]) -> str:
    """Generate an HTML summary of a travel plan.

    Args:
        travel_plan: Travel plan data

    Returns:
        HTML-formatted summary
    """
    # This would convert the markdown summary to HTML
    # For simplicity, we're just using a basic implementation
    markdown = _generate_markdown_summary(travel_plan)
    html = markdown.replace("# ", "<h1>").replace("## ", "<h2>").replace("### ", "<h3>")
    html = (
        html.replace("\n\n", "</p><p>").replace("**", "<strong>").replace("*", "<em>")
    )
    return f"<html><body><p>{html}</p></body></html>"


@with_error_handling()
async def save_travel_plan(params: dict[str, Any]) -> dict[str, Any]:
    """Save a travel plan to persistent storage.

    Stores the travel plan in the database and updates related knowledge graph entities.

    Args:
        params: Save parameters:
            plan_id: Travel plan ID
            user_id: User ID
            finalize: Whether to mark the plan as finalized

    Returns:
        Dictionary with save confirmation
    """
    try:
        # Extract parameters
        plan_id = params.get("plan_id")
        user_id = params.get("user_id")
        finalize = params.get("finalize", False)

        if not plan_id or not user_id:
            return {"success": False, "error": "Plan ID and user ID are required"}

        # Get the travel plan from cache
        cache_key = f"travel_plan:{plan_id}"
        travel_plan = await redis_cache.get(cache_key)

        if not travel_plan:
            return {"success": False, "error": f"Travel plan {plan_id} not found"}

        # Check user authorization
        if travel_plan.get("user_id") != user_id:
            return {"success": False, "error": "Unauthorized to save this plan"}

        # Mark as finalized if requested
        if finalize:
            travel_plan["status"] = "finalized"
            travel_plan["finalized_at"] = datetime.now(timezone.utc).isoformat()

        # Update the modification timestamp
        travel_plan["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Save to persistent storage (database)
        # This would interface with the database in a real implementation
        # For now, we just update the cache with a longer TTL
        await redis_cache.set(cache_key, travel_plan, ttl=86400 * 30)  # 30 days

        # Update knowledge graph
        # Using Mem0 direct SDK integration for memory management
        try:
            # Initialize direct Mem0 service
            memory_service = MemoryService()
            await memory_service.connect()

            # Add finalization memory if finalized
            if finalize:
                finalization_time = datetime.now(timezone.utc).isoformat()
                finalize_memory = (
                    f"Travel plan '{travel_plan.get('title', 'Untitled')}' "
                    f"finalized on {finalization_time}"
                )

                await memory_service.add_conversation_memory(
                    messages=[
                        {"role": "system", "content": "Travel plan finalized"},
                        {"role": "user", "content": finalize_memory},
                    ],
                    user_id=user_id,
                    metadata={
                        "plan_id": plan_id,
                        "type": "travel_plan_finalization",
                        "finalized_at": finalization_time,
                    },
                )

            # Create memory for plan components
            components = travel_plan.get("components", {})
            if components:
                component_memories = []

                for component_type, items in components.items():
                    if not items:
                        continue

                    component_count = len(items)
                    component_memories.append(f"{component_count} {component_type}")

                if component_memories:
                    components_memory = (
                        f"Travel plan includes: {', '.join(component_memories)}"
                    )

                    await memory_service.add_conversation_memory(
                        messages=[
                            {
                                "role": "system",
                                "content": "Travel plan components saved",
                            },
                            {"role": "user", "content": components_memory},
                        ],
                        user_id=user_id,
                        metadata={
                            "plan_id": plan_id,
                            "type": "travel_plan_components",
                            "components": components,
                        },
                    )

        except Exception as e:
            logger.warning(f"Error updating memory entity: {str(e)}")
            # Continue even if memory update fails

        return {
            "success": True,
            "plan_id": plan_id,
            "message": (
                f"Travel plan "
                f"{'' if not finalize else 'finalized and '}saved successfully"
            ),
            "status": travel_plan.get("status", "draft"),
        }

    except Exception as e:
        logger.error(f"Error saving travel plan: {str(e)}")
        log_exception(e)
        return {"success": False, "error": f"Travel plan save error: {str(e)}"}
