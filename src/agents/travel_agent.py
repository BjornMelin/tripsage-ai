from base_agent import BaseAgent
from typing import Dict, List, Any, Optional
import json
from supabase import create_client
from config import config
import time

class TravelAgent(BaseAgent):
    """
    Primary travel planning agent that coordinates the planning process
    and manages interactions with specialized sub-agents.
    """
    
    def __init__(self):
        instructions = """
        You are a travel planning assistant for TripSage. Your role is to help users plan their travels by:
        
        1. Understanding their travel preferences, constraints, and goals
        2. Creating personalized travel itineraries based on their needs
        3. Making recommendations for flights, accommodations, and activities
        4. Considering budget constraints in all recommendations
        5. Maintaining a conversational and helpful tone
        
        When interacting with users:
        - Ask clarifying questions to get a complete picture of their travel needs
        - Suggest alternatives when their initial requests might be problematic
        - Explain the reasoning behind your recommendations
        - Organize information clearly with appropriate formatting
        - When using the search_flights or search_accommodations tools, be specific about the criteria
        
        When creating travel plans:
        - Balance the itinerary between tourist attractions and local experiences
        - Consider transportation logistics between activities
        - Factor in realistic travel times and potential delays
        - Allow for downtime and flexibility in the schedule
        - Adapt recommendations based on weather and seasonal factors
        """
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_flights",
                    "description": "Search for flights based on specified criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "departure_airport": {
                                "type": "string",
                                "description": "Departure airport code (e.g., LAX, JFK)"
                            },
                            "arrival_airport": {
                                "type": "string",
                                "description": "Arrival airport code (e.g., LAX, JFK)"
                            },
                            "departure_date": {
                                "type": "string",
                                "description": "Departure date in YYYY-MM-DD format"
                            },
                            "return_date": {
                                "type": "string",
                                "description": "Return date in YYYY-MM-DD format for round trip flights"
                            },
                            "adults": {
                                "type": "integer",
                                "description": "Number of adult passengers"
                            },
                            "seat_class": {
                                "type": "string",
                                "enum": ["economy", "premium_economy", "business", "first"],
                                "description": "Desired seat class"
                            },
                            "max_stops": {
                                "type": "integer",
                                "description": "Maximum number of stops (0 for direct flights)"
                            }
                        },
                        "required": [
                            "departure_airport",
                            "arrival_airport",
                            "departure_date",
                            "adults"
                        ]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_accommodations",
                    "description": "Search for accommodations based on specified criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City or specific location for accommodation"
                            },
                            "check_in_date": {
                                "type": "string",
                                "description": "Check-in date in YYYY-MM-DD format"
                            },
                            "check_out_date": {
                                "type": "string",
                                "description": "Check-out date in YYYY-MM-DD format"
                            },
                            "adults": {
                                "type": "integer",
                                "description": "Number of adult guests"
                            },
                            "children": {
                                "type": "integer",
                                "description": "Number of children (if any)"
                            },
                            "rooms": {
                                "type": "integer",
                                "description": "Number of rooms required"
                            },
                            "property_type": {
                                "type": "string",
                                "enum": ["hotel", "apartment", "hostel", "resort", "guesthouse", "any"],
                                "description": "Type of accommodation preferred"
                            },
                            "min_rating": {
                                "type": "number",
                                "description": "Minimum star rating (1-5)"
                            },
                            "max_price_per_night": {
                                "type": "number",
                                "description": "Maximum price per night in USD"
                            },
                            "amenities": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Desired amenities (e.g., wifi, pool, breakfast)"
                            }
                        },
                        "required": [
                            "location",
                            "check_in_date",
                            "check_out_date",
                            "adults"
                        ]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_activities",
                    "description": "Search for activities and attractions at a destination",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City or specific location to search for activities"
                            },
                            "date": {
                                "type": "string",
                                "description": "Date in YYYY-MM-DD format"
                            },
                            "category": {
                                "type": "string",
                                "enum": [
                                    "sightseeing",
                                    "outdoor",
                                    "cultural",
                                    "entertainment",
                                    "food",
                                    "shopping",
                                    "any"
                                ],
                                "description": "Category of activity"
                            },
                            "max_price": {
                                "type": "number",
                                "description": "Maximum price per person in USD"
                            },
                            "duration": {
                                "type": "string",
                                "description": "Preferred duration (e.g., '2 hours', 'half-day', 'full-day')"
                            }
                        },
                        "required": [
                            "location"
                        ]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_trip",
                    "description": "Create a new trip in the system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "ID of the user creating the trip"
                            },
                            "title": {
                                "type": "string",
                                "description": "Title of the trip"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the trip"
                            },
                            "destination": {
                                "type": "string",
                                "description": "Primary destination for the trip"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date in YYYY-MM-DD format"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date in YYYY-MM-DD format"
                            },
                            "budget": {
                                "type": "number",
                                "description": "Total budget for the trip in USD"
                            },
                            "preferences": {
                                "type": "object",
                                "description": "User preferences for this trip"
                            }
                        },
                        "required": [
                            "user_id",
                            "title",
                            "destination"
                        ]
                    }
                }
            }
        ]
        
        metadata = {
            "agent_type": "travel_planner",
            "version": "1.0.0"
        }
        
        super().__init__(
            name="TripSage Travel Planner",
            instructions=instructions,
            tools=tools,
            metadata=metadata
        )
        
        # Initialize Supabase client for database operations
        self.supabase = create_client(config.supabase_url, config.supabase_key)
    
    def _handle_tool_calls(self) -> None:
        """Handle tool calls from the assistant"""
        tool_outputs = []
        
        for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            try:
                if function_name == "search_flights":
                    output = self._search_flights(function_args)
                elif function_name == "search_accommodations":
                    output = self._search_accommodations(function_args)
                elif function_name == "search_activities":
                    output = self._search_activities(function_args)
                elif function_name == "create_trip":
                    output = self._create_trip(function_args)
                else:
                    output = {"error": f"Unknown function: {function_name}"}
            except Exception as e:
                output = {"error": f"Error executing {function_name}: {str(e)}"}
            
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": json.dumps(output)
            })
        
        # Submit tool outputs
        self.run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.id,
            run_id=self.run.id,
            tool_outputs=tool_outputs
        )
    
    def _search_flights(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for flights based on specified criteria.
        In a real implementation, this would connect to a flight API.
        This is a mock implementation for demonstration.
        """
        # Mock flight data
        mock_flights = [
            {
                "id": "f1",
                "airline": "United Airlines",
                "flight_number": "UA123",
                "departure_airport": args["departure_airport"],
                "arrival_airport": args["arrival_airport"],
                "departure_time": f"{args['departure_date']}T08:00:00",
                "arrival_time": f"{args['departure_date']}T11:30:00",
                "duration_minutes": 210,
                "stops": 0,
                "price": 350.00,
                "seat_class": args.get("seat_class", "economy"),
                "available_seats": 12
            },
            {
                "id": "f2",
                "airline": "Delta Air Lines",
                "flight_number": "DL456",
                "departure_airport": args["departure_airport"],
                "arrival_airport": args["arrival_airport"],
                "departure_time": f"{args['departure_date']}T10:15:00",
                "arrival_time": f"{args['departure_date']}T14:45:00",
                "duration_minutes": 270,
                "stops": 1,
                "price": 280.00,
                "seat_class": args.get("seat_class", "economy"),
                "available_seats": 8
            },
            {
                "id": "f3",
                "airline": "American Airlines",
                "flight_number": "AA789",
                "departure_airport": args["departure_airport"],
                "arrival_airport": args["arrival_airport"],
                "departure_time": f"{args['departure_date']}T14:30:00",
                "arrival_time": f"{args['departure_date']}T17:45:00",
                "duration_minutes": 195,
                "stops": 0,
                "price": 420.00,
                "seat_class": args.get("seat_class", "economy"),
                "available_seats": 5
            }
        ]
        
        # Filter based on max_stops if provided
        if "max_stops" in args:
            mock_flights = [f for f in mock_flights if f["stops"] <= args["max_stops"]]
        
        # Add to price history in database (in real implementation)
        for flight in mock_flights:
            try:
                self.supabase.from_("price_history").insert({
                    "item_type": "flight",
                    "source_id": flight["id"],
                    "price": flight["price"],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "details": {
                        "airline": flight["airline"],
                        "flight_number": flight["flight_number"],
                        "seat_class": flight["seat_class"]
                    }
                }).execute()
            except Exception as e:
                print(f"Error storing price history: {e}")
        
        return {
            "flights": mock_flights,
            "search_criteria": args,
            "results_count": len(mock_flights)
        }
    
    def _search_accommodations(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for accommodations based on specified criteria.
        In a real implementation, this would connect to a hotel API.
        This is a mock implementation for demonstration.
        """
        # Mock accommodation data
        mock_accommodations = [
            {
                "id": "h1",
                "name": "Grand Hotel",
                "type": "hotel",
                "location": args["location"],
                "address": "123 Main St",
                "coordinates": {"lat": 40.7128, "lng": -74.0060},
                "rating": 4.5,
                "price_per_night": 200.00,
                "amenities": ["wifi", "pool", "breakfast", "gym"],
                "available_rooms": 3,
                "images": ["https://example.com/hotel1.jpg"]
            },
            {
                "id": "h2",
                "name": "Budget Inn",
                "type": "hotel",
                "location": args["location"],
                "address": "456 Elm St",
                "coordinates": {"lat": 40.7200, "lng": -74.0100},
                "rating": 3.5,
                "price_per_night": 120.00,
                "amenities": ["wifi", "breakfast"],
                "available_rooms": 8,
                "images": ["https://example.com/hotel2.jpg"]
            },
            {
                "id": "h3",
                "name": "Luxury Suites",
                "type": "apartment",
                "location": args["location"],
                "address": "789 Oak St",
                "coordinates": {"lat": 40.7150, "lng": -74.0080},
                "rating": 4.8,
                "price_per_night": 350.00,
                "amenities": ["wifi", "pool", "gym", "kitchen", "parking"],
                "available_rooms": 2,
                "images": ["https://example.com/hotel3.jpg"]
            }
        ]
        
        # Filter by property_type if provided
        if "property_type" in args and args["property_type"] != "any":
            mock_accommodations = [
                a for a in mock_accommodations 
                if a["type"] == args["property_type"]
            ]
        
        # Filter by min_rating if provided
        if "min_rating" in args:
            mock_accommodations = [
                a for a in mock_accommodations 
                if a["rating"] >= args["min_rating"]
            ]
        
        # Filter by max_price_per_night if provided
        if "max_price_per_night" in args:
            mock_accommodations = [
                a for a in mock_accommodations 
                if a["price_per_night"] <= args["max_price_per_night"]
            ]
        
        # Filter by amenities if provided
        if "amenities" in args and args["amenities"]:
            mock_accommodations = [
                a for a in mock_accommodations 
                if all(amenity in a["amenities"] for amenity in args["amenities"])
            ]
        
        # Add to price history in database (in real implementation)
        for accommodation in mock_accommodations:
            try:
                self.supabase.from_("price_history").insert({
                    "item_type": "accommodation",
                    "source_id": accommodation["id"],
                    "price": accommodation["price_per_night"],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "details": {
                        "name": accommodation["name"],
                        "type": accommodation["type"],
                        "rating": accommodation["rating"]
                    }
                }).execute()
            except Exception as e:
                print(f"Error storing price history: {e}")
        
        return {
            "accommodations": mock_accommodations,
            "search_criteria": args,
            "results_count": len(mock_accommodations)
        }
    
    def _search_activities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for activities based on specified criteria.
        In a real implementation, this would connect to an activities API.
        This is a mock implementation for demonstration.
        """
        # Mock activity data
        mock_activities = [
            {
                "id": "a1",
                "name": "City Tour",
                "category": "sightseeing",
                "location": args["location"],
                "price_per_person": 45.00,
                "duration": "3 hours",
                "rating": 4.6,
                "description": "Explore the city's main attractions with a knowledgeable guide.",
                "available_slots": 10,
                "images": ["https://example.com/activity1.jpg"]
            },
            {
                "id": "a2",
                "name": "Museum Visit",
                "category": "cultural",
                "location": args["location"],
                "price_per_person": 25.00,
                "duration": "2 hours",
                "rating": 4.3,
                "description": "Visit the city's renowned art museum.",
                "available_slots": 20,
                "images": ["https://example.com/activity2.jpg"]
            },
            {
                "id": "a3",
                "name": "Food Tour",
                "category": "food",
                "location": args["location"],
                "price_per_person": 65.00,
                "duration": "4 hours",
                "rating": 4.8,
                "description": "Sample local cuisine at various restaurants and food markets.",
                "available_slots": 8,
                "images": ["https://example.com/activity3.jpg"]
            },
            {
                "id": "a4",
                "name": "Hiking Adventure",
                "category": "outdoor",
                "location": args["location"],
                "price_per_person": 35.00,
                "duration": "half-day",
                "rating": 4.2,
                "description": "Explore scenic trails around the city with a guide.",
                "available_slots": 12,
                "images": ["https://example.com/activity4.jpg"]
            }
        ]
        
        # Filter by category if provided
        if "category" in args and args["category"] != "any":
            mock_activities = [
                a for a in mock_activities 
                if a["category"] == args["category"]
            ]
        
        # Filter by max_price if provided
        if "max_price" in args:
            mock_activities = [
                a for a in mock_activities 
                if a["price_per_person"] <= args["max_price"]
            ]
        
        # Filter by duration if provided
        if "duration" in args:
            mock_activities = [
                a for a in mock_activities 
                if a["duration"] == args["duration"]
            ]
        
        return {
            "activities": mock_activities,
            "search_criteria": args,
            "results_count": len(mock_activities)
        }
    
    def _create_trip(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new trip in the database"""
        try:
            # Insert trip into database
            response = self.supabase.from_("trips").insert({
                "user_id": args["user_id"],
                "title": args["title"],
                "description": args.get("description", ""),
                "destination": args["destination"],
                "start_date": args.get("start_date"),
                "end_date": args.get("end_date"),
                "budget": args.get("budget"),
                "preferences": args.get("preferences", {})
            }).execute()
            
            if response.data:
                return {
                    "success": True,
                    "trip_id": response.data[0]["id"],
                    "message": "Trip created successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create trip"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }