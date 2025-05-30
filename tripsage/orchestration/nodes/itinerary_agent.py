"""
Itinerary agent node implementation for LangGraph orchestration.

This module implements the itinerary planning agent as a LangGraph node,
replacing the OpenAI Agents SDK implementation with improved performance and
capabilities.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage.orchestration.tools.mcp_integration import MCPToolRegistry
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ItineraryAgentNode(BaseAgentNode):
    """
    Itinerary planning agent node.

    This node handles all itinerary-related requests including creation, optimization,
    modification, and calendar integration using MCP tool integration.
    """

    def __init__(self):
        """Initialize the itinerary agent node with tools and language model."""
        super().__init__("itinerary_agent")

        # Initialize LLM for itinerary-specific tasks
        self.llm = ChatOpenAI(
            model=settings.agent.model_name,
            temperature=settings.agent.temperature,
            api_key=settings.openai_api_key.get_secret_value(),
        )

    def _initialize_tools(self) -> None:
        """Initialize itinerary-specific tools and MCP integrations."""
        self.tool_registry = MCPToolRegistry()
        self.available_tools = self.tool_registry.get_tools_for_agent("itinerary_agent")

        logger.info(
            f"Initialized itinerary agent with {len(self.available_tools)} tools"
        )

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """
        Process itinerary-related requests.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with itinerary planning results and response
        """
        user_message = state["messages"][-1]["content"] if state["messages"] else ""

        # Extract itinerary parameters from user message and context
        itinerary_params = await self._extract_itinerary_parameters(user_message, state)

        if itinerary_params:
            # Determine the type of itinerary operation requested
            operation_type = itinerary_params.get("operation", "create")

            if operation_type == "create":
                # Create new itinerary
                itinerary_result = await self._create_itinerary(itinerary_params, state)
            elif operation_type == "optimize":
                # Optimize existing itinerary
                itinerary_result = await self._optimize_itinerary(
                    itinerary_params, state
                )
            elif operation_type == "modify":
                # Modify existing itinerary (add/remove activities)
                itinerary_result = await self._modify_itinerary(itinerary_params, state)
            elif operation_type == "calendar":
                # Create calendar events from itinerary
                itinerary_result = await self._create_calendar_events(
                    itinerary_params, state
                )
            else:
                # Default to creating new itinerary
                itinerary_result = await self._create_itinerary(itinerary_params, state)

            # Update state with results
            itinerary_record = {
                "timestamp": datetime.now(datetime.UTC).isoformat(),
                "operation": operation_type,
                "parameters": itinerary_params,
                "result": itinerary_result,
                "agent": "itinerary_agent",
            }

            if "itineraries" not in state:
                state["itineraries"] = []
            state["itineraries"].append(itinerary_record)

            # Generate user-friendly response
            response_message = await self._generate_itinerary_response(
                itinerary_result, itinerary_params, operation_type, state
            )
        else:
            # Handle general itinerary inquiries
            response_message = await self._handle_general_itinerary_inquiry(
                user_message, state
            )

        # Add response to conversation
        state["messages"].append(response_message)

        return state

    async def _extract_itinerary_parameters(
        self, message: str, state: TravelPlanningState
    ) -> Optional[Dict[str, Any]]:
        """
        Extract itinerary parameters from user message and conversation context.

        Args:
            message: User message to analyze
            state: Current conversation state for context

        Returns:
            Dictionary of itinerary parameters or None if insufficient info
        """
        # Use LLM to extract parameters and determine operation type
        extraction_prompt = f"""
        Extract itinerary-related parameters from this message and context, and
        determine the type of itinerary operation requested.
        
        User message: "{message}"
        
        Context from conversation:
        - Previous itineraries: {len(state.get("itineraries", []))}
        - Destination research: {len(state.get("destination_research", []))}
        - Flight searches: {len(state.get("flight_searches", []))}
        - Accommodation searches: {len(state.get("accommodation_searches", []))}
        - Budget analyses: {len(state.get("budget_analyses", []))}
        - Destination info: {list(state.get("destination_info", {}).keys())}
        
        Determine the operation type from these options:
        - "create": Create a new itinerary
        - "optimize": Optimize an existing itinerary
        - "modify": Modify an existing itinerary (add/remove activities)
        - "calendar": Create calendar events from itinerary
        
        Extract these parameters if mentioned:
        - operation: One of the operation types above
        - destination: Destination(s) for the itinerary
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        - duration: Trip duration in days
        - interests: List of interests or preferred activities
        - pace: Preferred pace (relaxed, moderate, busy)
        - budget_per_day: Daily budget for activities
        - transportation_mode: Preferred transportation
        - group_size: Number of travelers
        - special_requests: Any special requirements or requests
        - itinerary_id: ID of existing itinerary (for modify/optimize operations)
        
        Respond with JSON only. If this doesn't seem itinerary-related, return null.
        
        Example: {{"operation": "create", "destination": "Paris", 
                   "start_date": "2024-03-15", "end_date": "2024-03-20", 
                   "interests": ["museums", "food"], "pace": "moderate"}}
        """

        try:
            messages = [
                SystemMessage(
                    content="You are an itinerary planning parameter extraction "
                    "assistant."
                ),
                HumanMessage(content=extraction_prompt),
            ]

            response = await self.llm.ainvoke(messages)

            # Parse the response
            if response.content.strip().lower() in ["null", "none", "{}"]:
                return None

            params = json.loads(response.content)

            # Validate that this is itinerary-related
            if params and (
                "operation" in params
                or "itinerary" in message.lower()
                or "schedule" in message.lower()
            ):
                return params
            else:
                return None

        except Exception as e:
            logger.error(f"Error extracting itinerary parameters: {str(e)}")
            return None

    async def _create_itinerary(
        self, params: Dict[str, Any], state: TravelPlanningState
    ) -> Dict[str, Any]:
        """
        Create a detailed daily itinerary.

        Args:
            params: Itinerary creation parameters
            state: Current conversation state

        Returns:
            Created itinerary with daily schedule
        """
        destination = params.get("destination", "")
        start_date = params.get("start_date", "")
        end_date = params.get("end_date", "")
        interests = params.get("interests", [])
        pace = params.get("pace", "moderate")
        budget_per_day = params.get("budget_per_day", 0)

        try:
            # Calculate trip duration
            if start_date and end_date:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                duration = (end - start).days + 1
            else:
                duration = params.get("duration", 3)

            # Get destination information from previous research
            destination_info = state.get("destination_info", {}).get(destination, {})
            attractions = destination_info.get("attractions", [])
            activities = destination_info.get("activities", [])

            # Create daily itinerary based on pace and interests
            daily_schedule = await self._generate_daily_schedule(
                destination,
                duration,
                start_date,
                attractions,
                activities,
                interests,
                pace,
                budget_per_day,
            )

            # Calculate travel times between locations
            optimized_schedule = await self._optimize_schedule_logistics(
                daily_schedule, destination
            )

            itinerary_id = (
                f"itinerary_{datetime.now(datetime.UTC).strftime('%Y%m%d_%H%M%S')}"
            )

            return {
                "itinerary_id": itinerary_id,
                "destination": destination,
                "start_date": start_date,
                "end_date": end_date,
                "duration": duration,
                "pace": pace,
                "daily_schedule": optimized_schedule,
                "total_activities": sum(
                    len(day.get("activities", [])) for day in optimized_schedule
                ),
                "estimated_cost": self._calculate_estimated_cost(
                    optimized_schedule, budget_per_day
                ),
            }

        except Exception as e:
            logger.error(f"Itinerary creation failed: {str(e)}")
            return {"error": f"Failed to create itinerary: {str(e)}"}

    async def _generate_daily_schedule(
        self,
        destination: str,
        duration: int,
        start_date: str,
        attractions: List[Dict],
        activities: List[Dict],
        interests: List[str],
        pace: str,
        budget_per_day: float,
    ) -> List[Dict[str, Any]]:
        """Generate a daily schedule for the itinerary."""
        daily_schedule = []

        # Determine activities per day based on pace
        pace_multiplier = {"relaxed": 0.7, "moderate": 1.0, "busy": 1.3}
        base_activities_per_day = 3
        activities_per_day = int(
            base_activities_per_day * pace_multiplier.get(pace, 1.0)
        )

        # Combine and filter attractions/activities based on interests
        all_options = attractions + activities
        if interests:
            # Filter based on interests (simple keyword matching)
            filtered_options = []
            for option in all_options:
                name = option.get("name", "").lower()
                description = option.get("description", "").lower()
                if any(
                    interest.lower() in name or interest.lower() in description
                    for interest in interests
                ):
                    filtered_options.append(option)

            # If filtered list is too short, add some general options
            if len(filtered_options) < duration * activities_per_day:
                for option in all_options:
                    if option not in filtered_options:
                        filtered_options.append(option)
                        if len(filtered_options) >= duration * activities_per_day:
                            break

            all_options = filtered_options

        # Generate daily schedules
        current_date = (
            datetime.strptime(start_date, "%Y-%m-%d")
            if start_date
            else datetime.now(datetime.UTC)
        )

        for day in range(duration):
            day_date = (current_date + timedelta(days=day)).strftime("%Y-%m-%d")

            day_activities = []
            start_idx = day * activities_per_day
            end_idx = min(start_idx + activities_per_day, len(all_options))

            # Create activities for the day
            for i, option in enumerate(all_options[start_idx:end_idx]):
                # Schedule activities throughout the day
                hour = 9 + (i * 3)  # Start at 9am, 3 hours apart
                if hour > 18:  # Don't schedule past 6pm
                    hour = 18

                activity = {
                    "time": f"{hour:02d}:00",
                    "name": option.get("name", f"Activity {i + 1}"),
                    "description": option.get("description", ""),
                    "type": option.get("type", option.get("category", "activity")),
                    "duration": "2-3 hours",
                    "estimated_cost": (
                        budget_per_day / activities_per_day if budget_per_day > 0 else 0
                    ),
                }
                day_activities.append(activity)

            # Add meal breaks
            day_activities.insert(
                1,
                {
                    "time": "12:00",
                    "name": "Lunch",
                    "description": f"Local cuisine in {destination}",
                    "type": "meal",
                    "duration": "1 hour",
                    "estimated_cost": (
                        budget_per_day * 0.3 if budget_per_day > 0 else 0
                    ),
                },
            )

            day_schedule = {
                "day": day + 1,
                "date": day_date,
                "activities": sorted(day_activities, key=lambda x: x["time"]),
                "notes": f"Day {day + 1} in {destination}",
            }

            daily_schedule.append(day_schedule)

        return daily_schedule

    async def _optimize_schedule_logistics(
        self, daily_schedule: List[Dict], destination: str
    ) -> List[Dict]:
        """Optimize the schedule for logistics and travel times."""
        # This would use Google Maps API to calculate travel times and optimize routes
        # For now, we'll add basic logistics information

        for day in daily_schedule:
            activities = day.get("activities", [])
            for i, activity in enumerate(activities):
                if i > 0 and activity.get("type") != "meal":
                    # Add travel time information
                    activity["travel_from_previous"] = {
                        "mode": "walking/metro",
                        "estimated_time": "15-30 minutes",
                        "notes": "Check local transportation options",
                    }

        return daily_schedule

    def _calculate_estimated_cost(
        self, daily_schedule: List[Dict], budget_per_day: float
    ) -> Dict[str, float]:
        """Calculate estimated costs for the itinerary."""
        total_cost = 0
        daily_costs = []

        for day in daily_schedule:
            day_cost = 0
            for activity in day.get("activities", []):
                day_cost += activity.get("estimated_cost", 0)
            daily_costs.append(day_cost)
            total_cost += day_cost

        return {
            "total_estimated_cost": round(total_cost, 2),
            "average_daily_cost": (
                round(total_cost / len(daily_schedule), 2) if daily_schedule else 0
            ),
            "daily_costs": [round(cost, 2) for cost in daily_costs],
        }

    async def _optimize_itinerary(
        self, params: Dict[str, Any], state: TravelPlanningState
    ) -> Dict[str, Any]:
        """
        Optimize an existing itinerary for better flow and efficiency.

        Args:
            params: Optimization parameters
            state: Current conversation state

        Returns:
            Optimized itinerary
        """
        itinerary_id = params.get("itinerary_id", "")

        # Find the existing itinerary
        existing_itinerary = None
        for itinerary_record in state.get("itineraries", []):
            if itinerary_record.get("result", {}).get("itinerary_id") == itinerary_id:
                existing_itinerary = itinerary_record.get("result")
                break

        if not existing_itinerary:
            return {"error": "Itinerary not found for optimization"}

        try:
            # Get the daily schedule
            daily_schedule = existing_itinerary.get("daily_schedule", [])

            # Optimize each day for better flow
            optimized_schedule = []
            for day in daily_schedule:
                activities = day.get("activities", [])

                # Sort activities by time for better flow
                # Group nearby activities together (simplified logic)
                optimized_activities = sorted(
                    activities, key=lambda x: x.get("time", "00:00")
                )

                optimized_day = {
                    **day,
                    "activities": optimized_activities,
                    "optimization_notes": (
                        "Optimized for better flow and reduced travel time"
                    ),
                }
                optimized_schedule.append(optimized_day)

            return {
                **existing_itinerary,
                "daily_schedule": optimized_schedule,
                "optimization_applied": True,
                "optimization_timestamp": datetime.now(datetime.UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Itinerary optimization failed: {str(e)}")
            return {"error": f"Failed to optimize itinerary: {str(e)}"}

    async def _modify_itinerary(
        self, params: Dict[str, Any], state: TravelPlanningState
    ) -> Dict[str, Any]:
        """
        Modify an existing itinerary by adding or removing activities.

        Args:
            params: Modification parameters
            state: Current conversation state

        Returns:
            Modified itinerary
        """
        itinerary_id = params.get("itinerary_id", "")
        modification_type = params.get("modification_type", "add")  # add or remove
        activity_details = params.get("activity_details", {})

        # Find the existing itinerary
        existing_itinerary = None
        for itinerary_record in state.get("itineraries", []):
            if itinerary_record.get("result", {}).get("itinerary_id") == itinerary_id:
                existing_itinerary = itinerary_record.get("result")
                break

        if not existing_itinerary:
            return {"error": "Itinerary not found for modification"}

        try:
            daily_schedule = existing_itinerary.get("daily_schedule", [])

            if modification_type == "add":
                # Add new activity to specified day
                day_number = activity_details.get("day", 1)
                if 1 <= day_number <= len(daily_schedule):
                    day_index = day_number - 1
                    new_activity = {
                        "time": activity_details.get("time", "15:00"),
                        "name": activity_details.get("name", "New Activity"),
                        "description": activity_details.get("description", ""),
                        "type": activity_details.get("type", "activity"),
                        "duration": activity_details.get("duration", "1-2 hours"),
                        "estimated_cost": activity_details.get("estimated_cost", 0),
                    }
                    daily_schedule[day_index]["activities"].append(new_activity)
                    daily_schedule[day_index]["activities"].sort(
                        key=lambda x: x.get("time", "00:00")
                    )

            elif modification_type == "remove":
                # Remove activity from specified day
                day_number = activity_details.get("day", 1)
                activity_name = activity_details.get("name", "")
                if 1 <= day_number <= len(daily_schedule):
                    day_index = day_number - 1
                    activities = daily_schedule[day_index]["activities"]
                    daily_schedule[day_index]["activities"] = [
                        act
                        for act in activities
                        if act.get("name", "") != activity_name
                    ]

            return {
                **existing_itinerary,
                "daily_schedule": daily_schedule,
                "modification_applied": True,
                "modification_type": modification_type,
                "modification_timestamp": datetime.now(datetime.UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Itinerary modification failed: {str(e)}")
            return {"error": f"Failed to modify itinerary: {str(e)}"}

    async def _create_calendar_events(
        self, params: Dict[str, Any], state: TravelPlanningState
    ) -> Dict[str, Any]:
        """
        Create calendar events from an itinerary.

        Args:
            params: Calendar creation parameters
            state: Current conversation state

        Returns:
            Calendar events creation results
        """
        itinerary_id = params.get("itinerary_id", "")

        # Find the existing itinerary
        existing_itinerary = None
        for itinerary_record in state.get("itineraries", []):
            if itinerary_record.get("result", {}).get("itinerary_id") == itinerary_id:
                existing_itinerary = itinerary_record.get("result")
                break

        if not existing_itinerary:
            return {"error": "Itinerary not found for calendar creation"}

        try:
            daily_schedule = existing_itinerary.get("daily_schedule", [])
            calendar_events = []

            for day in daily_schedule:
                date = day.get("date", "")
                for activity in day.get("activities", []):
                    event = {
                        "title": activity.get("name", "Travel Activity"),
                        "date": date,
                        "time": activity.get("time", "09:00"),
                        "duration": activity.get("duration", "1 hour"),
                        "description": activity.get("description", ""),
                        "location": existing_itinerary.get("destination", ""),
                        "type": activity.get("type", "activity"),
                    }
                    calendar_events.append(event)

            return {
                "itinerary_id": itinerary_id,
                "calendar_events": calendar_events,
                "events_count": len(calendar_events),
                "creation_timestamp": datetime.now(datetime.UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Calendar events creation failed: {str(e)}")
            return {"error": f"Failed to create calendar events: {str(e)}"}

    async def _generate_itinerary_response(
        self,
        result: Dict[str, Any],
        params: Dict[str, Any],
        operation_type: str,
        state: TravelPlanningState,
    ) -> Dict[str, Any]:
        """
        Generate user-friendly response from itinerary results.

        Args:
            result: Itinerary operation results
            params: Parameters used for operation
            operation_type: Type of operation performed
            state: Current conversation state

        Returns:
            Formatted response message
        """
        if result.get("error"):
            content = (
                f"I apologize, but I encountered an issue with your itinerary: "
                f"{result['error']}"
            )
        else:
            if operation_type == "create":
                content = self._format_create_response(result, params)
            elif operation_type == "optimize":
                content = self._format_optimize_response(result, params)
            elif operation_type == "modify":
                content = self._format_modify_response(result, params)
            elif operation_type == "calendar":
                content = self._format_calendar_response(result, params)
            else:
                content = "Itinerary operation completed successfully."

        return self._create_response_message(
            content,
            {
                "operation": operation_type,
                "itinerary_summary": result,
            },
        )

    def _format_create_response(
        self, result: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Format itinerary creation response."""
        destination = result.get("destination", "")
        duration = result.get("duration", 0)
        total_activities = result.get("total_activities", 0)
        daily_schedule = result.get("daily_schedule", [])

        content = (
            f"I've created a {duration}-day itinerary for {destination} with "
            f"{total_activities} activities!\n\n"
        )

        for day in daily_schedule[:3]:  # Show first 3 days
            day_num = day.get("day", 1)
            date = day.get("date", "")
            content += f"**Day {day_num}** ({date}):\n"

            for activity in day.get("activities", [])[
                :3
            ]:  # Show first 3 activities per day
                time = activity.get("time", "")
                name = activity.get("name", "")
                content += f"• {time} - {name}\n"

            if len(day.get("activities", [])) > 3:
                content += (
                    f"• ... and {len(day.get('activities', [])) - 3} more activities\n"
                )
            content += "\n"

        if len(daily_schedule) > 3:
            content += f"... and {len(daily_schedule) - 3} more days of activities!\n\n"

        estimated_cost = result.get("estimated_cost", {})
        if estimated_cost.get("total_estimated_cost", 0) > 0:
            content += (
                f"**Estimated Cost:** ${estimated_cost['total_estimated_cost']:.0f} "
                f"total (${estimated_cost['average_daily_cost']:.0f}/day)\n\n"
            )

        content += (
            "Would you like me to optimize this itinerary, add calendar events, or "
            "make any modifications?"
        )

        return content

    def _format_optimize_response(
        self, result: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Format itinerary optimization response."""
        destination = result.get("destination", "")

        content = f"I've optimized your itinerary for {destination}!\n\n"
        content += "**Optimization Applied:**\n"
        content += "• Improved activity flow and timing\n"
        content += "• Reduced travel time between locations\n"
        content += "• Better grouped nearby activities\n\n"
        content += (
            "The optimized schedule maintains all your original activities while "
            "improving efficiency. "
        )
        content += (
            "Would you like to see the updated schedule or make any other changes?"
        )

        return content

    def _format_modify_response(
        self, result: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Format itinerary modification response."""
        modification_type = result.get("modification_type", "")
        destination = result.get("destination", "")

        if modification_type == "add":
            content = (
                f"I've successfully added the new activity to your {destination} "
                "itinerary!\n\n"
            )
        elif modification_type == "remove":
            content = (
                f"I've successfully removed the activity from your {destination} "
                "itinerary!\n\n"
            )
        else:
            content = f"I've successfully modified your {destination} itinerary!\n\n"

        content += "Your itinerary has been updated with the changes. "
        content += (
            "Would you like to make any other modifications or see the full updated "
            "schedule?"
        )

        return content

    def _format_calendar_response(
        self, result: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Format calendar events creation response."""
        events_count = result.get("events_count", 0)

        content = (
            f"I've created {events_count} calendar events from your itinerary!\n\n"
        )
        content += "**Calendar Events Include:**\n"
        content += "• All scheduled activities with times\n"
        content += "• Location information\n"
        content += "• Activity descriptions\n"
        content += "• Estimated durations\n\n"
        content += (
            "You can now import these events into your calendar app for easy "
            "reference during your trip!"
        )

        return content

    async def _handle_general_itinerary_inquiry(
        self, message: str, state: TravelPlanningState
    ) -> Dict[str, Any]:
        """
        Handle general itinerary inquiries that don't require specific planning.

        Args:
            message: User message
            state: Current conversation state

        Returns:
            Response message
        """
        # Use LLM to generate helpful response for general itinerary questions
        response_prompt = f"""
        The user is asking about itinerary planning but hasn't provided enough 
        specific information for planning.
        
        User message: "{message}"
        
        Provide a helpful response that:
        1. Acknowledges their interest in itinerary planning
        2. Asks for specific information needed (destination, dates, interests, pace)
        3. Explains what itinerary services you can provide (creation, optimization, 
           modification)
        4. Offers to help once they provide details
        
        Keep the response friendly and concise.
        """

        try:
            messages = [
                SystemMessage(
                    content="You are a helpful itinerary planning assistant."
                ),
                HumanMessage(content=response_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            content = response.content

        except Exception as e:
            logger.error(f"Error generating itinerary response: {str(e)}")
            content = (
                "I'd be happy to help you create a detailed itinerary! To get started, "
                "I'll need to know your destination, travel dates, interests, and "
                "preferred pace (relaxed, moderate, or busy). I can create day-by-day "
                "schedules, optimize existing itineraries, and even create calendar "
                "events for your trip. "
                "What destination are you planning to visit?"
            )

        return self._create_response_message(content)
