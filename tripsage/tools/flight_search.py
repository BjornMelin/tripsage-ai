"""
Flight search implementation for the TripSage Travel Agent.

This module provides enhanced flight search functionality for the TripSage Travel Agent,
with support for price history, recommendations, and advanced filtering.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents import function_tool
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tripsage.mcp.flights.client import get_client as get_flights_client
from tripsage.mcp.flights.service import get_service as get_flights_service
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class FlightSearchParams(BaseModel):
    """Parameters for flight search queries."""

    origin: str = Field(
        ..., min_length=3, max_length=3, description="Origin airport IATA code"
    )
    destination: str = Field(
        ..., min_length=3, max_length=3, description="Destination airport IATA code"
    )
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(
        None, description="Return date for round trips (YYYY-MM-DD)"
    )
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, description="Number of child passengers")
    infants: int = Field(0, ge=0, description="Number of infant passengers")
    cabin_class: str = Field(
        "economy", description="Cabin class (economy, premium_economy, business, first)"
    )
    max_stops: Optional[int] = Field(
        None, ge=0, le=2, description="Maximum number of stops"
    )
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price in USD")
    preferred_airlines: Optional[List[str]] = Field(
        None, description="List of preferred airline codes"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("departure_date", "return_date")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v


class FlightSearchResult(BaseModel):
    """Flight search result model."""

    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_date: str = Field(..., description="Departure date")
    return_date: Optional[str] = Field(None, description="Return date")
    offers: List[Dict[str, Any]] = Field([], description="List of flight offers")
    search_criteria: Dict[str, Any] = Field({}, description="Original search criteria")
    price_insights: Optional[Dict[str, Any]] = Field(None, description="Price insights")
    cache: str = Field("miss", description="Cache status (hit/miss)")
    error: Optional[str] = Field(None, description="Error message if search failed")

    model_config = ConfigDict(extra="allow")


class TripSageFlightSearch:
    """Enhanced flight search functionality for the TripSage Travel Agent."""

    def __init__(self, flights_client=None, flights_service=None):
        """Initialize the flight search module.

        Args:
            flights_client: Optional flights MCP client instance
            flights_service: Optional flights service instance for
                enhanced functionality
        """
        self.flights_client = flights_client or get_flights_client()
        self.flights_service = flights_service or get_flights_service()
        logger.info(
            "Initialized TripSage Flight Search with ravinahp/flights-mcp integration"
        )

    @function_tool
    @with_error_handling
    async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for flights with enhanced features and filtering.

        Args:
            params: Flight search parameters

        Returns:
            Enhanced flight search results with filtering and price insights
        """
        # Validate parameters
        search_params = FlightSearchParams(**params)

        # Check cache first
        from tripsage.cache.redis_cache import redis_cache

        cache_key = (
            f"flight_search:{search_params.origin}:{search_params.destination}:"
            f"{search_params.departure_date}:{search_params.return_date}:"
            f"{search_params.adults}:{search_params.cabin_class}"
        )

        cached_result = await redis_cache.get(cache_key)
        if cached_result:
            # Apply post-search filtering to cached results
            filtered_results = self._filter_flights(
                cached_result,
                max_price=search_params.max_price,
                max_stops=search_params.max_stops,
                preferred_airlines=search_params.preferred_airlines,
            )
            return {**filtered_results, "cache": "hit"}

        # Call the higher-level Flights service for enhanced functionality
        # This ensures proper dual storage in Supabase and Memory MCP
        flight_results = await self.flights_service.search_best_flights(
            origin=search_params.origin,
            destination=search_params.destination,
            departure_date=search_params.departure_date,
            return_date=search_params.return_date,
            adults=search_params.adults,
            max_price=search_params.max_price,
        )

        # If service call fails, fall back to direct client call
        if "error" in flight_results and "results" not in flight_results:
            logger.warning("Falling back to direct client call after service error")
            flight_results = await self.flights_client.search_flights(
                origin=search_params.origin,
                destination=search_params.destination,
                departure_date=search_params.departure_date,
                return_date=search_params.return_date,
                adults=search_params.adults,
                children=search_params.children,
                infants=search_params.infants,
                cabin_class=search_params.cabin_class,
            )

        if "error" in flight_results:
            return flight_results

        # Cache raw results before filtering
        await redis_cache.set(
            cache_key,
            flight_results,
            ttl=3600,  # Cache for 1 hour
        )

        # Apply post-search filtering
        filtered_results = self._filter_flights(
            flight_results,
            max_price=search_params.max_price,
            max_stops=search_params.max_stops,
            preferred_airlines=search_params.preferred_airlines,
        )

        # Add price history data
        enhanced_results = await self._add_price_history(filtered_results)

        return {**enhanced_results, "cache": "miss"}

    def _filter_flights(
        self,
        results: Dict[str, Any],
        max_price: Optional[float] = None,
        max_stops: Optional[int] = None,
        preferred_airlines: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
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
                offer
                for offer in filtered_offers
                if offer.get("total_amount") <= max_price
            ]

        # Apply stops filter
        if max_stops is not None:
            filtered_offers = [
                offer
                for offer in filtered_offers
                if all(
                    len(slice.get("segments", [])) - 1 <= max_stops
                    for slice in offer.get("slices", [])
                )
            ]

        # Apply airline preference filter
        if preferred_airlines and len(preferred_airlines) > 0:
            # Boost preferred airlines by putting them first
            preferred = [
                offer
                for offer in filtered_offers
                if any(
                    segment.get("operating_carrier_code") in preferred_airlines
                    for slice in offer.get("slices", [])
                    for segment in slice.get("segments", [])
                )
            ]

            non_preferred = [
                offer
                for offer in filtered_offers
                if not any(
                    segment.get("operating_carrier_code") in preferred_airlines
                    for slice in offer.get("slices", [])
                    for segment in slice.get("segments", [])
                )
            ]

            filtered_offers = preferred + non_preferred

        # Sort by price (lowest first)
        filtered_offers.sort(key=lambda x: x.get("total_amount", float("inf")))

        # Return updated results
        return {
            **results,
            "offers": filtered_offers,
            "filtered_count": len(filtered_offers),
            "original_count": len(results.get("offers", [])),
        }

    @with_error_handling
    async def _add_price_history(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Add price history data to flight search results.

        Args:
            results: Filtered flight results

        Returns:
            Enhanced results with price history
        """
        if "origin" not in results or "destination" not in results:
            return results

        # Get price history data
        origin = results["origin"]
        destination = results["destination"]
        departure_date = results.get("departure_date")

        price_history = await self._get_price_history(
            origin, destination, departure_date
        )

        # Add pricing insights
        if price_history and "prices" in price_history and price_history["prices"]:
            current_price = (
                min(
                    offer.get("total_amount", float("inf"))
                    for offer in results.get("offers", [])
                )
                if results.get("offers")
                else None
            )

            if current_price:
                # Calculate pricing insights
                prices = price_history["prices"]
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)

                # Determine trend
                trend = "stable"
                if len(prices) > 3:
                    recent_avg = sum(prices[-3:]) / 3
                    earlier_avg = sum(prices[:-3]) / (len(prices) - 3)
                    if recent_avg < earlier_avg * 0.95:
                        trend = "decreasing"
                    elif recent_avg > earlier_avg * 1.05:
                        trend = "increasing"

                price_insights = {
                    "current_vs_avg": round((current_price / avg_price - 1) * 100, 1),
                    "current_vs_min": round((current_price / min_price - 1) * 100, 1),
                    "current_vs_max": round((current_price / max_price - 1) * 100, 1),
                    "avg_price": avg_price,
                    "min_price": min_price,
                    "max_price": max_price,
                    "trend": trend,
                    "recommendation": self._generate_price_recommendation(
                        current_price, avg_price, min_price, price_history
                    ),
                }

                return {
                    **results,
                    "price_history": price_history,
                    "price_insights": price_insights,
                }

        return results

    @with_error_handling
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
        # Try to get data from Flights MCP
        try:
            return await self.flights_client.get_flight_prices(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
            )
        except Exception as e:
            logger.warning(f"Failed to get price history from MCP: {str(e)}")

        # Fallback to database
        try:
            from tripsage.db.client import get_client as get_db_client

            db_client = get_db_client()
            history = await db_client.get_flight_price_history(
                origin=origin,
                destination=destination,
                date_from=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                date_to=datetime.now().strftime("%Y-%m-%d"),
            )

            # Format history data
            if history:
                return {
                    "prices": [item["price"] for item in history],
                    "dates": [item["date"] for item in history],
                    "count": len(history),
                }
        except Exception as e:
            logger.warning(f"Failed to get price history from database: {str(e)}")

        # Return empty history if all methods fail
        return {"prices": [], "dates": [], "count": 0}

    def _generate_price_recommendation(
        self,
        current_price: float,
        avg_price: float,
        min_price: float,
        history: Dict[str, Any],
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
            return "book_now"  # Book now - this is among the lowest prices we've seen
        elif current_price <= great_deal_threshold:
            return "great_deal"  # Great deal - price significantly below average
        elif current_price <= good_deal_threshold:
            return "good_deal"  # Good deal - price below average
        elif current_price <= avg_price * 1.1:  # Within 10% of average
            return "fair_price"  # Fair price - close to typical prices for this route
        else:
            # Price higher than average - consider monitoring for better deals
            return "monitor"

    @function_tool
    @with_error_handling
    async def search_flexible_dates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for flight options with flexible dates to find the best deals.

        Args:
            params: Search parameters including origin, destination, date range

        Returns:
            Best flight options across the date range
        """
        # Validate required parameters
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
            current_date += timedelta(days=3)  # Search every 3 days to limit API calls

        # Search flights for each date combination
        results = []

        for dep_date in dates_to_search:
            search_params = {
                "origin": origin,
                "destination": destination,
                "departure_date": dep_date,
                "adults": adults,
                "cabin_class": cabin_class,
            }

            # Add return date if trip length specified
            if trip_length:
                ret_date = (
                    datetime.strptime(dep_date, "%Y-%m-%d")
                    + timedelta(days=trip_length)
                ).strftime("%Y-%m-%d")
                search_params["return_date"] = ret_date

            # Search flights
            try:
                result = await self.search_flights(search_params)

                # Extract best price for this date
                if "offers" in result and result["offers"]:
                    best_price = min(
                        offer.get("total_amount", float("inf"))
                        for offer in result["offers"]
                    )

                    results.append(
                        {
                            "departure_date": dep_date,
                            "return_date": search_params.get("return_date"),
                            "best_price": best_price,
                            "currency": result["offers"][0].get("currency", "USD"),
                            "offer_count": len(result["offers"]),
                        }
                    )
            except Exception as e:
                logger.warning(f"Error searching flights for {dep_date}: {str(e)}")

        # Sort by price
        results.sort(key=lambda x: x.get("best_price", float("inf")))

        return {
            "origin": origin,
            "destination": destination,
            "date_range": {"from": params["date_from"], "to": params["date_to"]},
            "trip_length": trip_length,
            "best_date": results[0] if results else None,
            "all_dates": results,
            "total_options": len(results),
            "recommendation": (
                self._generate_date_recommendation(results) if results else None
            ),
        }

    def _generate_date_recommendation(
        self, date_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a recommendation based on flexible date search results.

        Args:
            date_results: List of prices by date

        Returns:
            Recommendation data
        """
        if not date_results:
            return {}

        # Find cheapest date
        cheapest = min(date_results, key=lambda x: x.get("best_price", float("inf")))

        # Calculate average price
        avg_price = sum(r.get("best_price", 0) for r in date_results) / len(
            date_results
        )

        # Calculate savings compared to average
        savings = avg_price - cheapest.get("best_price", 0)
        savings_percent = (savings / avg_price) * 100 if avg_price > 0 else 0

        # Generate recommendation text
        if savings_percent >= 30:
            recommendation = "significant_savings"
        elif savings_percent >= 15:
            recommendation = "good_savings"
        else:
            recommendation = "minor_savings"

        return {
            "best_date": {
                "departure": cheapest.get("departure_date"),
                "return": cheapest.get("return_date"),
            },
            "savings": {
                "amount": round(savings, 2),
                "percent": round(savings_percent, 1),
            },
            "recommendation": recommendation,
        }


# Create singleton instance for easy access
flight_search = TripSageFlightSearch()
