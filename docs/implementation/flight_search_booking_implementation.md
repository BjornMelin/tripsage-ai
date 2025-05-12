# Flight Search and Booking Implementation Guide

This document provides a comprehensive implementation guide for the Flight Search and Booking capabilities (TRAVELAGENT-002) in the TripSage system.

## Overview

The Flight Search and Booking module enables the TripSage Travel Planning Agent to search for flight options across multiple providers, compare prices, track historical pricing data, and facilitate the booking process. It leverages the Flights MCP Server's integration with the Duffel API while adding agent-specific capabilities for enhanced user experience and decision support.

## Architecture

The Flight Search and Booking functionality follows a layered architecture:

1. **User Interface Layer**: Handled by the Travel Planning Agent
2. **Business Logic Layer**: Implemented in the TripSageTravelAgent class
3. **Service Layer**: Flights MCP Server with Duffel API integration
4. **Data Layer**: Dual storage architecture (Supabase + Knowledge Graph)

## MCP Tools Exposed

The following tools are exposed by the Flights MCP and utilized by the Travel Planning Agent:

| Tool Name                   | Description                                          | Parameters                                                                        |
| --------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------- |
| `search_flights`            | Search for one-way or round-trip flights             | `origin`, `destination`, `departure_date`, `return_date`, `adults`, `cabin_class` |
| `search_multi_city`         | Search for multi-city flight itineraries             | `segments`, `adults`, `cabin_class`                                               |
| `get_airports`              | Get airport information by IATA code or search       | `code` or `search_term`                                                           |
| `check_flight_availability` | Check detailed availability for a specific flight    | `flight_id`                                                                       |
| `get_flight_prices`         | Get current and historical prices for a flight route | `origin`, `destination`, `departure_date`                                         |
| `track_flight_price`        | Start price tracking for a specific flight route     | `origin`, `destination`, `departure_date`, `return_date`, `notification_email`    |

## API Integrations

### Duffel API

The implementation utilizes the Duffel API through the Flights MCP Server:

```python
# Simplified example of Duffel API integration in Flights MCP Server
from duffel_api import Duffel
from datetime import datetime

class DuffelClient:
    def __init__(self, api_key: str):
        self.client = Duffel(access_token=api_key)

    async def search_flights(self, origin: str, destination: str,
                            departure_date: str, return_date: str = None,
                            passengers: int = 1, cabin_class: str = "economy"):
        """Search for flights using the Duffel API."""
        passengers_data = [{"type": "adult"}] * passengers

        # Build request
        request_data = {
            "slices": [
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date
                }
            ],
            "passengers": passengers_data,
            "cabin_class": cabin_class
        }

        # Add return slice if round-trip
        if return_date:
            request_data["slices"].append({
                "origin": destination,
                "destination": origin,
                "departure_date": return_date
            })

        # Create the offer request
        offer_request = await self.client.offer_requests.create(request_data)

        # Get the offers
        offers = await self.client.offers.list(offer_request_id=offer_request.id)

        return self._format_offers(offers)
```

## Implementation Details

### Flight Search Implementation

The TripSageTravelAgent class includes enhanced methods for flight search and comparison:

```python
# src/agents/flight_search.py

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
import asyncio
import logging

from src.cache.redis_cache import redis_cache
from src.db.client import get_client
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class FlightSearchParams(BaseModel):
    """Model for flight search parameters validation."""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin airport IATA code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination airport IATA code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(None, description="Return date for round trips (YYYY-MM-DD)")
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    cabin_class: str = Field("economy", description="Cabin class (economy, premium_economy, business, first)")
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price in USD")
    max_stops: Optional[int] = Field(None, ge=0, le=2, description="Maximum number of stops")
    preferred_airlines: Optional[List[str]] = Field(None, description="List of preferred airline codes")

    @validator("departure_date", "return_date")
    def validate_date_format(cls, v):
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @validator("return_date")
    def validate_return_date(cls, v, values):
        if v and "departure_date" in values:
            dep_date = datetime.strptime(values["departure_date"], "%Y-%m-%d")
            ret_date = datetime.strptime(v, "%Y-%m-%d")
            if ret_date <= dep_date:
                raise ValueError("Return date must be after departure date")
        return v


class TripSageFlightSearch:
    """Flight search functionality for the TripSage Travel Agent."""

    def __init__(self, flights_client):
        """Initialize with a flights MCP client."""
        self.flights_client = flights_client

    async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for flights with enhanced features and filtering.

        Args:
            params: Flight search parameters validated using FlightSearchParams

        Returns:
            Enhanced flight search results with filtering and sorting
        """
        try:
            # Validate parameters
            search_params = FlightSearchParams(**params)

            # Check cache first
            cache_key = f"flight_search:{search_params.origin}:{search_params.destination}:" \
                      f"{search_params.departure_date}:{search_params.return_date}:" \
                      f"{search_params.adults}:{search_params.cabin_class}"

            cached_result = await redis_cache.get(cache_key)
            if cached_result:
                # Apply post-search filtering to cached results
                filtered_results = self._filter_flights(
                    cached_result,
                    max_price=search_params.max_price,
                    max_stops=search_params.max_stops,
                    preferred_airlines=search_params.preferred_airlines
                )
                return {**filtered_results, "cache": "hit"}

            # Call Flights MCP client
            flight_results = await self.flights_client.search_flights(
                origin=search_params.origin,
                destination=search_params.destination,
                departure_date=search_params.departure_date,
                return_date=search_params.return_date,
                adults=search_params.adults,
                cabin_class=search_params.cabin_class
            )

            if "error" in flight_results:
                return flight_results

            # Cache raw results before filtering
            await redis_cache.set(
                cache_key,
                flight_results,
                ttl=3600  # Cache for 1 hour
            )

            # Apply post-search filtering
            filtered_results = self._filter_flights(
                flight_results,
                max_price=search_params.max_price,
                max_stops=search_params.max_stops,
                preferred_airlines=search_params.preferred_airlines
            )

            # Add price history data
            enhanced_results = await self._add_price_history(filtered_results)

            return {**enhanced_results, "cache": "miss"}

        except Exception as e:
            logger.error(f"Flight search error: {str(e)}")
            return {"error": f"Flight search error: {str(e)}"}

    def _filter_flights(self, results: Dict[str, Any],
                        max_price: Optional[float] = None,
                        max_stops: Optional[int] = None,
                        preferred_airlines: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply filters to flight search results.

        Args:
            results: Raw flight search results
            max_price: Maximum price filter
            max_stops: Maximum stops filter
            preferred_airlines: List of preferred airlines

        Returns:
            Filtered flight results
        """
        if "offers" not in results:
            return results

        filtered_offers = results["offers"].copy()

        # Apply price filter
        if max_price is not None:
            filtered_offers = [
                offer for offer in filtered_offers
                if offer.get("total_amount") <= max_price
            ]

        # Apply stops filter
        if max_stops is not None:
            filtered_offers = [
                offer for offer in filtered_offers
                if all(len(slice.get("segments", [])) - 1 <= max_stops
                      for slice in offer.get("slices", []))
            ]

        # Apply airline preference filter
        if preferred_airlines and len(preferred_airlines) > 0:
            # Boost preferred airlines by putting them first
            preferred = [
                offer for offer in filtered_offers
                if any(segment.get("operating_carrier_code") in preferred_airlines
                      for slice in offer.get("slices", [])
                      for segment in slice.get("segments", []))
            ]

            non_preferred = [
                offer for offer in filtered_offers
                if not any(segment.get("operating_carrier_code") in preferred_airlines
                          for slice in offer.get("slices", [])
                          for segment in slice.get("segments", []))
            ]

            filtered_offers = preferred + non_preferred

        # Sort by price (lowest first)
        filtered_offers.sort(key=lambda x: x.get("total_amount", float("inf")))

        # Return updated results
        return {
            **results,
            "offers": filtered_offers,
            "filtered_count": len(filtered_offers),
            "original_count": len(results.get("offers", []))
        }

    async def _add_price_history(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Add price history data to flight search results.

        Args:
            results: Filtered flight results

        Returns:
            Enhanced results with price history
        """
        if "origin" not in results or "destination" not in results:
            return results

        try:
            # Get price history data
            origin = results["origin"]
            destination = results["destination"]
            departure_date = results.get("departure_date")

            price_history = await self._get_price_history(
                origin, destination, departure_date
            )

            # Add pricing insights
            if price_history and "prices" in price_history:
                current_price = min(
                    offer.get("total_amount", float("inf"))
                    for offer in results.get("offers", [])
                )

                # Calculate pricing insights
                avg_price = sum(price_history["prices"]) / len(price_history["prices"])
                min_price = min(price_history["prices"])
                max_price = max(price_history["prices"])

                price_insights = {
                    "current_vs_avg": round((current_price / avg_price - 1) * 100, 1),
                    "current_vs_min": round((current_price / min_price - 1) * 100, 1),
                    "current_vs_max": round((current_price / max_price - 1) * 100, 1),
                    "avg_price": avg_price,
                    "min_price": min_price,
                    "max_price": max_price,
                    "recommendation": self._generate_price_recommendation(
                        current_price, avg_price, min_price, price_history
                    )
                }

                return {
                    **results,
                    "price_history": price_history,
                    "price_insights": price_insights
                }

            return results

        except Exception as e:
            logger.warning(f"Error adding price history: {str(e)}")
            return results

    async def _get_price_history(
        self, origin: str, destination: str, departure_date: Optional[str]
    ) -> Dict[str, Any]:
        """Get price history for a route.

        Args:
            origin: Origin airport code
            destination: Destination airport code
            departure_date: Departure date

        Returns:
            Price history data
        """
        try:
            # Get data from database
            db_client = get_client()
            history = await db_client.get_flight_price_history(
                origin=origin,
                destination=destination,
                date_from=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                date_to=datetime.now().strftime("%Y-%m-%d")
            )

            # Format history data
            if history:
                return {
                    "prices": [item["price"] for item in history],
                    "dates": [item["date"] for item in history],
                    "count": len(history)
                }

            # If no history in database, try getting from Flights MCP
            if hasattr(self.flights_client, "get_flight_prices"):
                try:
                    return await self.flights_client.get_flight_prices(
                        origin=origin,
                        destination=destination,
                        departure_date=departure_date
                    )
                except Exception as e:
                    logger.warning(f"Failed to get price history from MCP: {str(e)}")

            return {}

        except Exception as e:
            logger.error(f"Error retrieving price history: {str(e)}")
            return {}

    def _generate_price_recommendation(
        self, current_price: float, avg_price: float, min_price: float, history: Dict[str, Any]
    ) -> str:
        """Generate a price recommendation based on historical data.

        Args:
            current_price: Current lowest price
            avg_price: Average historical price
            min_price: Minimum historical price
            history: Price history data

        Returns:
            Price recommendation string
        """
        # Calculate thresholds
        good_deal_threshold = avg_price * 0.9  # 10% below average
        great_deal_threshold = avg_price * 0.8  # 20% below average

        if current_price <= min_price * 1.05:  # Within 5% of historical minimum
            return "Book now - this is among the lowest prices we've seen"
        elif current_price <= great_deal_threshold:
            return "Great deal - price significantly below average"
        elif current_price <= good_deal_threshold:
            return "Good deal - price below average"
        elif current_price <= avg_price * 1.1:  # Within 10% of average
            return "Fair price - close to typical prices for this route"
        else:
            return "Price higher than average - consider monitoring for better deals"
```

### Flight Booking Implementation

The booking functionality provides a streamlined workflow for reservations:

```python
# src/agents/flight_booking.py

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator
import asyncio
import logging
import uuid

from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class FlightBookingParams(BaseModel):
    """Model for flight booking parameters validation."""
    offer_id: str = Field(..., description="Duffel offer ID to book")
    trip_id: Optional[str] = Field(None, description="TripSage trip ID for association")
    passengers: List[Dict[str, Any]] = Field(..., min_items=1, description="Passenger information")
    payment_details: Dict[str, Any] = Field(..., description="Payment information")
    contact_details: Dict[str, Any] = Field(..., description="Contact information")

    @validator("passengers")
    def validate_passengers(cls, v):
        for passenger in v:
            required_fields = ["given_name", "family_name", "gender", "born_on"]
            for field in required_fields:
                if field not in passenger:
                    raise ValueError(f"Passenger missing required field: {field}")
        return v

    @validator("payment_details")
    def validate_payment(cls, v):
        required_fields = ["type", "amount", "currency"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Payment details missing required field: {field}")
        return v

    @validator("contact_details")
    def validate_contact(cls, v):
        required_fields = ["email", "phone"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Contact details missing required field: {field}")
        return v


class TripSageFlightBooking:
    """Flight booking functionality for the TripSage Travel Agent."""

    def __init__(self, flights_client):
        """Initialize with a flights MCP client."""
        self.flights_client = flights_client

    async def book_flight(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Book a flight based on a selected offer.

        Args:
            params: Booking parameters validated using FlightBookingParams

        Returns:
            Booking confirmation and status
        """
        try:
            # Validate parameters
            booking_params = FlightBookingParams(**params)

            # Call Flights MCP client to create order
            booking_result = await self.flights_client.create_order(
                offer_id=booking_params.offer_id,
                passengers=booking_params.passengers,
                payment_details=booking_params.payment_details,
                contact_details=booking_params.contact_details
            )

            if "error" in booking_result:
                return booking_result

            # If booking successful, store in TripSage database
            if booking_params.trip_id:
                await self._store_booking_in_database(
                    trip_id=booking_params.trip_id,
                    booking_result=booking_result
                )

            # Store in knowledge graph
            await self._update_knowledge_graph(booking_result)

            return {
                "success": True,
                "booking_id": booking_result.get("booking_id"),
                "confirmed": booking_result.get("status") == "confirmed",
                "total_price": booking_result.get("total_amount"),
                "currency": booking_result.get("currency"),
                "booking_details": booking_result
            }

        except Exception as e:
            logger.error(f"Flight booking error: {str(e)}")
            return {"error": f"Flight booking error: {str(e)}"}

    async def _store_booking_in_database(
        self, trip_id: str, booking_result: Dict[str, Any]
    ) -> None:
        """Store booking details in TripSage database.

        Args:
            trip_id: TripSage trip ID
            booking_result: Booking result from Flights MCP
        """
        try:
            from src.db.client import get_client
            db_client = get_client()

            # Extract flight information
            slices = booking_result.get("slices", [])
            for slice_idx, slice_data in enumerate(slices):
                # Create flight record for each slice
                flight_data = {
                    "trip_id": trip_id,
                    "airline": slice_data.get("operating_carrier", {}).get("name"),
                    "flight_number": "-".join([
                        segment.get("operating_carrier_code", ""),
                        segment.get("operating_flight_number", "")
                    ]) for segment in slice_data.get("segments", []),
                    "origin": slice_data.get("origin", {}).get("iata_code"),
                    "destination": slice_data.get("destination", {}).get("iata_code"),
                    "departure_time": slice_data.get("departure_datetime"),
                    "arrival_time": slice_data.get("arrival_datetime"),
                    "price": booking_result.get("total_amount") / len(slices) if len(slices) > 0 else 0,
                    "booking_reference": booking_result.get("booking_reference"),
                    "status": "booked"
                }

                # Add flight to database
                await db_client.create_flight(flight_data)

        except Exception as e:
            logger.error(f"Error storing booking in database: {str(e)}")

    async def _update_knowledge_graph(self, booking_result: Dict[str, Any]) -> None:
        """Update knowledge graph with booking information.

        Args:
            booking_result: Booking result from Flights MCP
        """
        try:
            # Only proceed if memory client is available
            if not hasattr(self, "memory_client") or not self.memory_client:
                return

            # Extract entities and observations
            booking_id = booking_result.get("booking_id")
            airline = booking_result.get("slices", [{}])[0].get("operating_carrier", {}).get("name")
            route = f"{booking_result.get('origin', {}).get('iata_code')}-{booking_result.get('destination', {}).get('iata_code')}"

            # Create booking entity
            await self.memory_client.create_entities([{
                "name": f"Booking:{booking_id}",
                "entityType": "Booking",
                "observations": [
                    f"Booking reference: {booking_result.get('booking_reference')}",
                    f"Airline: {airline}",
                    f"Route: {route}",
                    f"Price: {booking_result.get('total_amount')} {booking_result.get('currency')}",
                    f"Status: {booking_result.get('status')}"
                ]
            }])

            # Create relations
            relations = []

            # Relation to airline
            if airline:
                relations.append({
                    "from": f"Booking:{booking_id}",
                    "relationType": "with_airline",
                    "to": airline
                })

            # Relation to origin/destination
            origin = booking_result.get("origin", {}).get("iata_code")
            destination = booking_result.get("destination", {}).get("iata_code")

            if origin:
                relations.append({
                    "from": f"Booking:{booking_id}",
                    "relationType": "departs_from",
                    "to": origin
                })

            if destination:
                relations.append({
                    "from": f"Booking:{booking_id}",
                    "relationType": "arrives_at",
                    "to": destination
                })

            # Create relations if any exist
            if relations:
                await self.memory_client.create_relations(relations)

        except Exception as e:
            logger.warning(f"Error updating knowledge graph: {str(e)}")
```

### Integration with the Travel Planning Agent

This functionality is integrated into the TripSageTravelAgent class:

```python
# src/agents/travel_agent_impl.py
# Existing imports...
from .flight_search import TripSageFlightSearch, FlightSearchParams
from .flight_booking import TripSageFlightBooking, FlightBookingParams

class TripSageTravelAgent(TravelAgent):
    """Comprehensive travel planning agent for TripSage with all integrated tools."""

    def __init__(
        self,
        name: str = "TripSage Travel Planner",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the TripSage travel agent with all required tools and integrations."""
        super().__init__(name=name, model=model, temperature=temperature)

        # Initialize MCP clients
        self.flights_client = get_flights_client()
        # Other clients...

        # Initialize specialized modules
        self.flight_search = TripSageFlightSearch(self.flights_client)
        self.flight_booking = TripSageFlightBooking(self.flights_client)

        # Register all MCP tools
        self._register_all_mcp_tools()

        # Initialize knowledge graph
        self._initialize_knowledge_graph()

        logger.info("TripSage Travel Agent fully initialized with all MCP tools")

    # Existing methods...

    @function_tool
    async def enhanced_flight_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced flight search with filtering, price history, and recommendations.

        Args:
            params: Search parameters including:
                origin: Origin airport IATA code (e.g., 'SFO')
                destination: Destination airport IATA code (e.g., 'JFK')
                departure_date: Departure date (YYYY-MM-DD)
                return_date: Return date for round trips (YYYY-MM-DD)
                adults: Number of adult passengers (default: 1)
                cabin_class: Cabin class (economy, premium_economy, business, first)
                max_price: Maximum price in USD (optional)
                max_stops: Maximum number of stops (optional)
                preferred_airlines: List of preferred airline codes (optional)

        Returns:
            Comprehensive flight search results with price insights and recommendations
        """
        return await self.flight_search.search_flights(params)

    @function_tool
    async def advanced_flight_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for flight options with flexible dates to find the best deals.

        Args:
            params: Search parameters including:
                origin: Origin airport IATA code
                destination: Destination airport IATA code
                date_from: Start of date range (YYYY-MM-DD)
                date_to: End of date range (YYYY-MM-DD)
                trip_length: Length of trip in days for return flights
                adults: Number of adult passengers
                cabin_class: Cabin class

        Returns:
            Best flight options across the date range
        """
        try:
            # Validate core parameters
            required = ["origin", "destination", "date_from", "date_to"]
            for param in required:
                if param not in params:
                    return {"error": f"Missing required parameter: {param}"}

            origin = params["origin"]
            destination = params["destination"]
            date_from = datetime.strptime(params["date_from"], "%Y-%m-%d")
            date_to = datetime.strptime(params["date_to"], "%Y-%m-%d")
            trip_length = params.get("trip_length")
            adults = params.get("adults", 1)
            cabin_class = params.get("cabin_class", "economy")

            # Generate dates to search
            if (date_to - date_from).days > 30:
                # Limit search to 30 days to avoid too many API calls
                date_to = date_from + timedelta(days=30)

            dates_to_search = []
            current_date = date_from
            while current_date <= date_to:
                dates_to_search.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)

            # Search flights for each date combination
            results = []

            # Limit number of concurrent searches
            sem = asyncio.Semaphore(3)

            async def search_for_date(dep_date):
                async with sem:
                    search_params = {
                        "origin": origin,
                        "destination": destination,
                        "departure_date": dep_date,
                        "adults": adults,
                        "cabin_class": cabin_class
                    }

                    # Add return date if trip length specified
                    if trip_length:
                        ret_date = (datetime.strptime(dep_date, "%Y-%m-%d") +
                                   timedelta(days=trip_length)).strftime("%Y-%m-%d")
                        search_params["return_date"] = ret_date

                    result = await self.flight_search.search_flights(search_params)

                    # Extract best price for this date
                    if "offers" in result and result["offers"]:
                        best_price = min(
                            offer.get("total_amount", float("inf"))
                            for offer in result["offers"]
                        )

                        return {
                            "departure_date": dep_date,
                            "return_date": search_params.get("return_date"),
                            "best_price": best_price,
                            "currency": result["offers"][0].get("currency", "USD"),
                            "offer_count": len(result["offers"])
                        }

                    return None

            # Run searches concurrently
            search_tasks = [search_for_date(date) for date in dates_to_search]
            date_results = await asyncio.gather(*search_tasks)

            # Filter out None results and sort by price
            valid_results = [r for r in date_results if r]
            valid_results.sort(key=lambda x: x.get("best_price", float("inf")))

            return {
                "origin": origin,
                "destination": destination,
                "date_range": {
                    "from": params["date_from"],
                    "to": params["date_to"]
                },
                "trip_length": trip_length,
                "best_date": valid_results[0] if valid_results else None,
                "all_dates": valid_results,
                "total_options": len(valid_results)
            }

        except Exception as e:
            logger.error(f"Advanced flight search error: {str(e)}")
            return {"error": f"Advanced flight search error: {str(e)}"}

    @function_tool
    async def book_flight(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Book a flight based on a selected offer.

        Args:
            params: Booking parameters including:
                offer_id: Duffel offer ID to book
                trip_id: TripSage trip ID for association (optional)
                passengers: List of passenger information
                payment_details: Payment information
                contact_details: Contact information

        Returns:
            Booking confirmation and details
        """
        return await self.flight_booking.book_flight(params)

    @function_tool
    async def track_flight_prices(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set up price tracking for a specific flight route.

        Args:
            params: Tracking parameters including:
                origin: Origin airport IATA code
                destination: Destination airport IATA code
                departure_date: Departure date or date range
                return_date: Return date or date range (optional)
                email: Email address for notifications
                price_threshold: Target price for alerts (optional)

        Returns:
            Confirmation of price tracking setup
        """
        try:
            # Validate required parameters
            required = ["origin", "destination", "departure_date", "email"]
            for param in required:
                if param not in params:
                    return {"error": f"Missing required parameter: {param}"}

            # Call Flights MCP to set up tracking
            if hasattr(self.flights_client, "track_flight_price"):
                tracking_result = await self.flights_client.track_flight_price(
                    origin=params["origin"],
                    destination=params["destination"],
                    departure_date=params["departure_date"],
                    return_date=params.get("return_date"),
                    notification_email=params["email"],
                    price_threshold=params.get("price_threshold")
                )

                return tracking_result

            # Fallback implementation if MCP doesn't support tracking
            tracking_id = str(uuid.uuid4())

            # Store tracking request in database
            from src.db.client import get_client
            db_client = get_client()

            await db_client.create_price_tracking(
                tracking_id=tracking_id,
                origin=params["origin"],
                destination=params["destination"],
                departure_date=params["departure_date"],
                return_date=params.get("return_date"),
                email=params["email"],
                price_threshold=params.get("price_threshold"),
                status="active"
            )

            return {
                "tracking_id": tracking_id,
                "status": "active",
                "message": "Price tracking created successfully"
            }

        except Exception as e:
            logger.error(f"Flight price tracking error: {str(e)}")
            return {"error": f"Flight price tracking error: {str(e)}"}
```

## Caching Strategy

The flight search implementation includes a caching strategy for improved performance:

1. **Client-side Cache**: Raw flight search results are cached before filtering
2. **Cache Keys**: Based on origin, destination, dates, passengers, and cabin class
3. **TTL Strategy**: 1-hour TTL for flight search results due to price volatility
4. **Filtering**: Post-cache filtering for max_price, max_stops, and airline preferences

This approach allows for efficient retrieval of flight data while still providing flexible filtering options.

## Dual Storage Implementation

The flight booking functionality leverages the dual storage architecture:

1. **Supabase**: Stores structured flight booking data in the `flights` table

   - Linked to `trips` table via `trip_id` foreign key
   - Includes booking references, prices, and flight details

2. **Knowledge Graph**: Stores semantic relationships and observations
   - Creates `Booking` entity type with observations
   - Establishes relationships like `with_airline`, `departs_from`, and `arrives_at`
   - Links bookings to airports, airlines, and destinations

This dual approach allows for both structured queries and semantic reasoning about flight bookings.

## Testing Strategy

### Unit Tests

```python
# tests/agents/test_flight_search.py
import pytest
from unittest.mock import AsyncMock, patch
import datetime

from src.agents.flight_search import TripSageFlightSearch, FlightSearchParams

@pytest.fixture
def mock_flights_client():
    client = AsyncMock()
    client.search_flights.return_value = {
        "origin": "SFO",
        "destination": "JFK",
        "departure_date": "2025-06-15",
        "offers": [
            {
                "id": "offer_1",
                "total_amount": 299.99,
                "currency": "USD",
                "slices": [
                    {
                        "segments": [
                            {
                                "operating_carrier_code": "UA",
                                "operating_flight_number": "1234",
                                "departure": {
                                    "airport": {"iata_code": "SFO"},
                                    "datetime": "2025-06-15T08:00:00"
                                },
                                "arrival": {
                                    "airport": {"iata_code": "JFK"},
                                    "datetime": "2025-06-15T16:30:00"
                                }
                            }
                        ]
                    }
                ]
            },
            {
                "id": "offer_2",
                "total_amount": 349.99,
                "currency": "USD",
                "slices": [
                    {
                        "segments": [
                            {
                                "operating_carrier_code": "DL",
                                "operating_flight_number": "5678",
                                "departure": {
                                    "airport": {"iata_code": "SFO"},
                                    "datetime": "2025-06-15T10:00:00"
                                },
                                "arrival": {
                                    "airport": {"iata_code": "JFK"},
                                    "datetime": "2025-06-15T18:30:00"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
    return client

@pytest.mark.asyncio
async def test_search_flights(mock_flights_client):
    """Test the flight search functionality."""
    # Setup
    search = TripSageFlightSearch(mock_flights_client)

    # Mock redis cache
    with patch("src.cache.redis_cache.redis_cache.get") as mock_get:
        mock_get.return_value = None  # No cache hit

        with patch("src.cache.redis_cache.redis_cache.set") as mock_set:
            # Test search
            result = await search.search_flights({
                "origin": "SFO",
                "destination": "JFK",
                "departure_date": "2025-06-15",
                "adults": 1,
                "cabin_class": "economy",
                "max_price": 400
            })

            # Assertions
            assert result["cache"] == "miss"
            assert len(result["offers"]) == 2
            assert result["filtered_count"] == 2
            assert result["origin"] == "SFO"
            assert result["destination"] == "JFK"

            # Test max_price filter
            result = await search.search_flights({
                "origin": "SFO",
                "destination": "JFK",
                "departure_date": "2025-06-15",
                "adults": 1,
                "cabin_class": "economy",
                "max_price": 300
            })

            assert len(result["offers"]) == 1
            assert result["offers"][0]["id"] == "offer_1"

@pytest.mark.asyncio
async def test_flight_search_params_validation():
    """Test parameter validation for flight search."""
    # Valid parameters
    valid_params = {
        "origin": "SFO",
        "destination": "JFK",
        "departure_date": "2025-06-15",
        "adults": 1,
        "cabin_class": "economy"
    }
    params = FlightSearchParams(**valid_params)
    assert params.origin == "SFO"

    # Invalid origin (too short)
    with pytest.raises(ValueError):
        FlightSearchParams(**{**valid_params, "origin": "SF"})

    # Invalid date format
    with pytest.raises(ValueError):
        FlightSearchParams(**{**valid_params, "departure_date": "15/06/2025"})

    # Invalid return date (before departure)
    with pytest.raises(ValueError):
        FlightSearchParams(**{
            **valid_params,
            "return_date": "2025-06-10"  # Before departure
        })
```

### Integration Tests

```python
# tests/agents/test_flight_integration.py
import pytest
from unittest.mock import AsyncMock, patch
import asyncio

from src.agents.travel_agent_impl import TripSageTravelAgent

@pytest.fixture
async def setup_agent():
    """Set up a TripSageTravelAgent with mocked clients."""
    agent = TripSageTravelAgent()

    # Mock the flights client
    mock_flights = AsyncMock()
    mock_flights.search_flights.return_value = {
        "origin": "SFO",
        "destination": "JFK",
        "departure_date": "2025-06-15",
        "offers": [
            {
                "id": "offer_1",
                "total_amount": 299.99,
                "currency": "USD",
                "slices": [...]
            }
        ]
    }

    mock_flights.create_order.return_value = {
        "booking_id": "booking_1",
        "booking_reference": "ABC123",
        "status": "confirmed",
        "total_amount": 299.99,
        "currency": "USD",
        "slices": [...]
    }

    # Replace the real client with mock
    agent.flights_client = mock_flights

    # Also update the specialized modules to use the mock
    agent.flight_search.flights_client = mock_flights
    agent.flight_booking.flights_client = mock_flights

    return agent

@pytest.mark.asyncio
async def test_agent_enhanced_flight_search(setup_agent):
    """Test the enhanced flight search via the agent."""
    agent = await setup_agent

    # Test the enhanced flight search
    result = await agent.enhanced_flight_search({
        "origin": "SFO",
        "destination": "JFK",
        "departure_date": "2025-06-15",
        "adults": 1
    })

    # Assertions
    assert "offers" in result
    assert len(result["offers"]) > 0
    assert result["origin"] == "SFO"
    assert result["destination"] == "JFK"

    # Verify the flights client was called
    agent.flights_client.search_flights.assert_called_once()

@pytest.mark.asyncio
async def test_agent_book_flight(setup_agent):
    """Test the flight booking via the agent."""
    agent = await setup_agent

    # Test booking
    result = await agent.book_flight({
        "offer_id": "offer_1",
        "passengers": [
            {
                "given_name": "John",
                "family_name": "Doe",
                "gender": "m",
                "born_on": "1980-01-01"
            }
        ],
        "payment_details": {
            "type": "credit_card",
            "amount": 299.99,
            "currency": "USD"
        },
        "contact_details": {
            "email": "john.doe@example.com",
            "phone": "+1234567890"
        }
    })

    # Assertions
    assert result["success"] is True
    assert result["booking_id"] == "booking_1"
    assert result["confirmed"] is True

    # Verify the flights client was called
    agent.flights_client.create_order.assert_called_once()
```

## Deployment Requirements

### Resources

- **CPU**: 2-4 cores recommended
- **Memory**: 4-8GB RAM
- **Storage**: Minimal (primarily uses Supabase and Neo4j)
- **Network**: Internet connection for API access
- **Dependencies**: Redis for caching, Supabase for relational data, Neo4j for knowledge graph

### Environment Variables

```
# Duffel API credentials
DUFFEL_API_KEY=duffel_test_...

# Database connection
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Cache configuration
REDIS_URL=redis://localhost:6379/0

# Memory MCP (Neo4j) connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

## Monitoring

The TripSageTravelAgent includes metrics for monitoring flight search and booking activities:

```python
import prometheus_client
from prometheus_client import Counter, Histogram, Summary

# Flight search metrics
FLIGHT_SEARCH_REQUESTS = Counter(
    'tripsage_flight_search_requests_total',
    'Total number of flight search requests',
    ['origin', 'destination']
)

FLIGHT_SEARCH_DURATION = Histogram(
    'tripsage_flight_search_duration_seconds',
    'Flight search request duration in seconds',
    ['origin', 'destination'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

FLIGHT_BOOKING_REQUESTS = Counter(
    'tripsage_flight_booking_requests_total',
    'Total number of flight booking requests',
    ['status']
)

FLIGHT_SEARCH_RESULTS = Summary(
    'tripsage_flight_search_results',
    'Statistics on flight search results',
    ['origin', 'destination']
)

# Update metrics in search method
async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
    origin = params.get("origin", "unknown")
    destination = params.get("destination", "unknown")

    # Increment counter
    FLIGHT_SEARCH_REQUESTS.labels(origin=origin, destination=destination).inc()

    # Time the search
    with FLIGHT_SEARCH_DURATION.labels(origin=origin, destination=destination).time():
        result = await self._perform_search(params)

    # Record result count
    if "offers" in result:
        FLIGHT_SEARCH_RESULTS.labels(
            origin=origin, destination=destination
        ).observe(len(result["offers"]))

    return result
```

## Conclusion

The Flight Search and Booking implementation leverages the TripSageTravelAgent's capabilities and the Flights MCP Server to provide a comprehensive solution for finding and booking flights. Key features include:

1. **Enhanced Search**: Advanced filtering, price history, and recommendations
2. **Flexible Dates**: Search across date ranges to find best prices
3. **Booking Workflow**: Streamlined booking process with database integration
4. **Price Tracking**: Monitoring flight prices for better deals
5. **Caching Strategy**: Efficient caching for improved performance
6. **Dual Storage**: Integration with both Supabase and knowledge graph

This implementation follows TripSage's architectural principles including proper error handling, validation, logging, and testing, ensuring a robust and maintainable solution.
