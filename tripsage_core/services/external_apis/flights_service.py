"""Duffel Flights API service implementation.

This module provides direct integration with the Duffel API for flight search,
booking, and management operations.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

import httpx
from pydantic import ValidationError as PydanticValidationError

from tripsage_core.config.base_app_settings import get_settings
from tripsage_core.config.service_registry import BaseService
from tripsage_core.models.api.flights_models import (
    Airport,
    CabinClass,
    FlightOffer,
    OrderCancellation,
    Passenger,
    PassengerType,
    PaymentRequest,
    SeatMap,
)
from tripsage_core.models.api.flights_models import (
    FlightOfferRequest as OfferRequest,
)
from tripsage_core.models.api.flights_models import (
    Order as FlightOrder,
)
from tripsage_core.models.api.flights_models import (
    OrderCreateRequest as CreateOrderRequest,
)
from tripsage_core.utils.cache_utils import cached
from tripsage_core.utils.decorator_utils import retry_on_failure
from tripsage_core.utils.logging_utils import get_logger

settings = get_settings()

logger = get_logger(__name__)


class DuffelFlightsService(BaseService):
    """Service for interacting with Duffel Flights API."""

    def __init__(self):
        """Initialize the Duffel Flights service."""
        super().__init__()
        self.base_url = "https://api.duffel.com"
        self.api_token = settings.DUFFEL_API_TOKEN
        self.test_mode = settings.DUFFEL_TEST_MODE

        if not self.api_token:
            raise ValueError("DUFFEL_API_TOKEN not configured")

        # Configure HTTP client with auth header
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Duffel-Version": "v1",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    @retry_on_failure(max_attempts=3, backoff_factor=2)
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated request to the Duffel API.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            API response data

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{endpoint}" if endpoint.startswith("/") else f"/{endpoint}"

        response = await self.client.request(
            method=method,
            url=url,
            json=data,
            params=params,
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            logger.error(f"Duffel API error: {error_data}")
            raise

        return response.json()

    @cached(ttl=300)  # Cache for 5 minutes
    async def search_airports(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Airport]:
        """Search for airports by name, city, or code.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching airports
        """
        params = {
            "query": query,
            "limit": limit,
        }

        response = await self._make_request("GET", "/places/suggestions", params=params)

        airports = []
        for place in response.get("data", []):
            if place.get("type") == "airport":
                airports.append(Airport(**place))

        return airports

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: datetime,
        return_date: Optional[datetime] = None,
        passengers: Optional[List[Passenger]] = None,
        cabin_class: Optional[CabinClass] = None,
        max_connections: Optional[int] = None,
        currency: str = "USD",
    ) -> List[FlightOffer]:
        """Search for flight offers.

        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Departure date
            return_date: Return date for round trips
            passengers: List of passengers
            cabin_class: Preferred cabin class
            max_connections: Maximum number of connections
            currency: Currency for prices

        Returns:
            List of flight offers
        """
        # Build passenger list if not provided
        if not passengers:
            passengers = [
                Passenger(
                    type=PassengerType.adult,
                    given_name="",
                    family_name="",
                )
            ]

        # Build slices
        slices = [
            {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date.date().isoformat(),
            }
        ]

        if return_date:
            slices.append(
                {
                    "origin": destination,
                    "destination": origin,
                    "departure_date": return_date.date().isoformat(),
                }
            )

        # Create offer request
        offer_request = OfferRequest(
            slices=slices,
            passengers=[{"type": p.type.value} for p in passengers],
            cabin_class=cabin_class.value if cabin_class else None,
            max_connections=max_connections,
            return_offers=False,  # Get offers directly
        )

        # Make request
        request_data = {"data": offer_request.model_dump(exclude_none=True)}

        response = await self._make_request(
            "POST", "/offer_requests", data=request_data
        )

        # Parse offers
        offers = []
        for offer_data in response.get("data", {}).get("offers", []):
            try:
                offer = FlightOffer(**offer_data)
                offers.append(offer)
            except PydanticValidationError as e:
                logger.warning(f"Failed to parse offer: {e}")
                continue

        return offers

    async def get_offer_details(self, offer_id: str) -> FlightOffer:
        """Get detailed information about a specific offer.

        Args:
            offer_id: Offer ID

        Returns:
            Flight offer details
        """
        response = await self._make_request("GET", f"/offers/{offer_id}")
        return FlightOffer(**response["data"])

    async def create_order(
        self,
        offer_id: str,
        passengers: List[Passenger],
        payment: PaymentRequest,
        selected_offers: Optional[List[str]] = None,
    ) -> FlightOrder:
        """Create a flight order (booking).

        Args:
            offer_id: ID of the offer to book
            passengers: Passenger details
            payment: Payment information
            selected_offers: Additional service offer IDs

        Returns:
            Created order
        """
        # Build passenger data with required fields
        passenger_data = []
        for passenger in passengers:
            p_data = passenger.model_dump(exclude_none=True)
            # Ensure required fields
            if not p_data.get("phone_number"):
                p_data["phone_number"] = "+1234567890"  # Default if not provided
            if not p_data.get("email"):
                p_data["email"] = (
                    f"{p_data['given_name'].lower()}.{p_data['family_name'].lower()}@example.com"
                )
            passenger_data.append(p_data)

        # Create order request
        order_request = CreateOrderRequest(
            type="instant",
            selected_offers=[offer_id] + (selected_offers or []),
            passengers=passenger_data,
            payments=[payment.model_dump()],
        )

        request_data = {"data": order_request.model_dump(exclude_none=True)}

        response = await self._make_request("POST", "/orders", data=request_data)
        return FlightOrder(**response["data"])

    async def get_order(self, order_id: str) -> FlightOrder:
        """Get order details.

        Args:
            order_id: Order ID

        Returns:
            Order details
        """
        response = await self._make_request("GET", f"/orders/{order_id}")
        return FlightOrder(**response["data"])

    async def list_orders(
        self,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[FlightOrder]:
        """List orders with optional filters.

        Args:
            created_after: Filter orders created after this date
            created_before: Filter orders created before this date
            limit: Maximum number of orders to return

        Returns:
            List of orders
        """
        params = {"limit": limit}

        if created_after:
            params["created_at[gte]"] = created_after.isoformat()
        if created_before:
            params["created_at[lte]"] = created_before.isoformat()

        response = await self._make_request("GET", "/orders", params=params)

        orders = []
        for order_data in response.get("data", []):
            try:
                orders.append(FlightOrder(**order_data))
            except PydanticValidationError as e:
                logger.warning(f"Failed to parse order: {e}")
                continue

        return orders

    async def cancel_order(self, order_id: str) -> OrderCancellation:
        """Cancel a flight order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation details
        """
        request_data = {
            "data": {
                "order_id": order_id,
            }
        }

        response = await self._make_request(
            "POST", "/order_cancellations", data=request_data
        )
        return OrderCancellation(**response["data"])

    async def get_seat_maps(self, offer_id: str) -> List[SeatMap]:
        """Get seat maps for an offer.

        Args:
            offer_id: Offer ID

        Returns:
            List of seat maps for each segment
        """
        params = {"offer_id": offer_id}
        response = await self._make_request("GET", "/seat_maps", params=params)

        seat_maps = []
        for seat_map_data in response.get("data", []):
            try:
                seat_maps.append(SeatMap(**seat_map_data))
            except PydanticValidationError as e:
                logger.warning(f"Failed to parse seat map: {e}")
                continue

        return seat_maps

    # Travel-specific helper methods

    async def search_flexible_dates(
        self,
        origin: str,
        destination: str,
        departure_date: datetime,
        flexibility_days: int = 3,
        return_date: Optional[datetime] = None,
        **kwargs,
    ) -> Dict[str, List[FlightOffer]]:
        """Search flights with flexible dates.

        Args:
            origin: Origin airport code
            destination: Destination airport code
            departure_date: Preferred departure date
            flexibility_days: Number of days flexibility (before/after)
            return_date: Return date for round trips
            **kwargs: Additional search parameters

        Returns:
            Dictionary mapping dates to flight offers
        """
        search_tasks = []
        date_range = []

        # Generate date range
        for delta in range(-flexibility_days, flexibility_days + 1):
            search_date = departure_date + timedelta(days=delta)
            date_range.append(search_date)

            # Create search task
            if return_date:
                return_search_date = return_date + timedelta(days=delta)
                search_tasks.append(
                    self.search_flights(
                        origin=origin,
                        destination=destination,
                        departure_date=search_date,
                        return_date=return_search_date,
                        **kwargs,
                    )
                )
            else:
                search_tasks.append(
                    self.search_flights(
                        origin=origin,
                        destination=destination,
                        departure_date=search_date,
                        **kwargs,
                    )
                )

        # Execute searches in parallel
        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Build results dictionary
        flexible_results = {}
        for date, result in zip(date_range, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(f"Search failed for {date}: {result}")
                flexible_results[date.isoformat()] = []
            else:
                flexible_results[date.isoformat()] = result

        return flexible_results

    async def find_cheapest_offer(
        self,
        offers: List[FlightOffer],
        max_stops: Optional[int] = None,
        max_duration_hours: Optional[float] = None,
    ) -> Optional[FlightOffer]:
        """Find the cheapest offer matching criteria.

        Args:
            offers: List of flight offers
            max_stops: Maximum number of stops
            max_duration_hours: Maximum total duration in hours

        Returns:
            Cheapest matching offer or None
        """
        valid_offers = []

        for offer in offers:
            # Check stops constraint
            if max_stops is not None:
                total_stops = sum(len(slice.segments) - 1 for slice in offer.slices)
                if total_stops > max_stops:
                    continue

            # Check duration constraint
            if max_duration_hours is not None:
                total_duration = sum(
                    (
                        datetime.fromisoformat(slice.segments[-1].arriving_at)
                        - datetime.fromisoformat(slice.segments[0].departing_at)
                    ).total_seconds()
                    / 3600
                    for slice in offer.slices
                )
                if total_duration > max_duration_hours:
                    continue

            valid_offers.append(offer)

        # Sort by total amount
        if valid_offers:
            return min(valid_offers, key=lambda x: Decimal(x.total_amount))

        return None

    async def get_airline_preferences(
        self,
        offers: List[FlightOffer],
        preferred_airlines: Optional[Set[str]] = None,
        excluded_airlines: Optional[Set[str]] = None,
    ) -> List[FlightOffer]:
        """Filter offers by airline preferences.

        Args:
            offers: List of flight offers
            preferred_airlines: Set of preferred airline codes
            excluded_airlines: Set of excluded airline codes

        Returns:
            Filtered list of offers
        """
        filtered_offers = []

        for offer in offers:
            # Get all airlines in the offer
            offer_airlines = set()
            for slice in offer.slices:
                for segment in slice.segments:
                    if segment.operating_carrier:
                        offer_airlines.add(segment.operating_carrier.iata_code)
                    if segment.marketing_carrier:
                        offer_airlines.add(segment.marketing_carrier.iata_code)

            # Check excluded airlines
            if excluded_airlines and offer_airlines.intersection(excluded_airlines):
                continue

            # Check preferred airlines (if specified, at least one must match)
            if preferred_airlines and not offer_airlines.intersection(
                preferred_airlines
            ):
                continue

            filtered_offers.append(offer)

        return filtered_offers

    async def create_trip_booking(
        self,
        offer_id: str,
        trip_id: str,
        lead_passenger: Passenger,
        additional_passengers: Optional[List[Passenger]] = None,
        payment: Optional[PaymentRequest] = None,
    ) -> FlightOrder:
        """Create a flight booking for a trip.

        Args:
            offer_id: Selected offer ID
            trip_id: Associated trip ID
            lead_passenger: Primary passenger details
            additional_passengers: Additional passengers
            payment: Payment information

        Returns:
            Created order
        """
        # Combine passengers
        all_passengers = [lead_passenger]
        if additional_passengers:
            all_passengers.extend(additional_passengers)

        # Create default payment if not provided (for test mode)
        if not payment and self.test_mode:
            payment = PaymentRequest(
                type="balance",
                amount=0,  # Will be calculated by Duffel
                currency="USD",
            )

        # Add trip metadata to passengers
        for passenger in all_passengers:
            if not passenger.metadata:
                passenger.metadata = {}
            passenger.metadata["trip_id"] = trip_id

        # Create the order
        order = await self.create_order(
            offer_id=offer_id,
            passengers=all_passengers,
            payment=payment,
        )

        logger.info(f"Created flight order {order.id} for trip {trip_id}")
        return order
