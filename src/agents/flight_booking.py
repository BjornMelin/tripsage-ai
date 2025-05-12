"""
Flight booking implementation for the TripSage Travel Agent.

This module provides flight booking functionality for the TripSage Travel Agent,
with support for order creation, booking management, and integration with the
TripSage dual storage architecture.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..cache.redis_cache import redis_cache
from ..db.client import get_client as get_db_client
from ..mcp.flights import get_client as get_flights_client
from ..mcp.memory import get_client as get_memory_client
from ..utils.error_handling import MCPError
from ..utils.logging import get_module_logger

logger = get_module_logger(__name__)


class Passenger(BaseModel):
    """Passenger information model."""

    given_name: str = Field(
        ..., min_length=1, description="Passenger's first/given name"
    )
    family_name: str = Field(
        ..., min_length=1, description="Passenger's last/family name"
    )
    gender: str = Field(..., description="Passenger's gender (m/f)")
    born_on: str = Field(..., description="Passenger's date of birth (YYYY-MM-DD)")
    email: Optional[str] = Field(None, description="Passenger's email address")
    phone: Optional[str] = Field(None, description="Passenger's phone number")
    nationality: Optional[str] = Field(
        None, description="Passenger's nationality (ISO country code)"
    )
    document_type: Optional[str] = Field(
        None, description="Travel document type (passport/id_card)"
    )
    document_number: Optional[str] = Field(None, description="Travel document number")

    model_config = ConfigDict(extra="forbid")

    @field_validator("born_on")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that date is in YYYY-MM-DD format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v


class PaymentDetails(BaseModel):
    """Payment information model."""

    type: str = Field(..., description="Payment type (credit_card/paypal/etc)")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(..., description="Payment currency code (e.g., USD)")
    card_number: Optional[str] = Field(
        None, description="Credit card number (if applicable)"
    )
    card_holder: Optional[str] = Field(None, description="Name on card (if applicable)")
    expiry_month: Optional[str] = Field(
        None, description="Card expiry month (if applicable)"
    )
    expiry_year: Optional[str] = Field(
        None, description="Card expiry year (if applicable)"
    )

    model_config = ConfigDict(extra="forbid")


class ContactDetails(BaseModel):
    """Contact information model."""

    email: str = Field(..., description="Contact email address")
    phone: str = Field(..., description="Contact phone number")
    address: Optional[Dict[str, Any]] = Field(
        None, description="Contact postal address"
    )

    model_config = ConfigDict(extra="forbid")


class FlightBookingParams(BaseModel):
    """Parameters for flight booking."""

    offer_id: str = Field(..., description="Duffel offer ID to book")
    trip_id: Optional[str] = Field(None, description="TripSage trip ID for association")
    passengers: List[Dict[str, Any]] = Field(
        ..., min_items=1, description="Passenger information"
    )
    payment_details: Dict[str, Any] = Field(..., description="Payment information")
    contact_details: Dict[str, Any] = Field(..., description="Contact information")

    model_config = ConfigDict(extra="forbid")

    @field_validator("passengers")
    @classmethod
    def validate_passengers(cls, v):
        """Validate passenger information."""
        for passenger in v:
            required_fields = ["given_name", "family_name", "gender", "born_on"]
            for field in required_fields:
                if field not in passenger:
                    raise ValueError(f"Passenger missing required field: {field}")
        return v

    @field_validator("payment_details")
    @classmethod
    def validate_payment(cls, v):
        """Validate payment details."""
        required_fields = ["type", "amount", "currency"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Payment details missing required field: {field}")
        return v

    @field_validator("contact_details")
    @classmethod
    def validate_contact(cls, v):
        """Validate contact details."""
        required_fields = ["email", "phone"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Contact details missing required field: {field}")
        return v


class TripSageFlightBooking:
    """Flight booking functionality for the TripSage Travel Agent."""

    def __init__(self, flights_client=None, memory_client=None):
        """Initialize the flight booking module.

        Args:
            flights_client: Optional flights MCP client instance
            memory_client: Optional memory MCP client instance
        """
        self.flights_client = flights_client or get_flights_client()
        self.memory_client = memory_client
        logger.info("Initialized TripSage Flight Booking")

    async def book_flight(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Book a flight based on a selected offer.

        Note: When using ravinahp/flights-mcp, booking operations are not supported
        as it is a read-only MCP server. This method will return an error in that case.

        Args:
            params: Booking parameters validated using FlightBookingParams

        Returns:
            Booking confirmation and status, or error if using ravinahp/flights-mcp
        """
        try:
            # Validate parameters
            booking_params = FlightBookingParams(**params)

            # Call Flights MCP client to create order
            booking_result = await self.flights_client.create_order(
                offer_id=booking_params.offer_id,
                passengers=booking_params.passengers,
                payment_details=booking_params.payment_details,
                contact_details=booking_params.contact_details,
            )

            if "error" in booking_result:
                return booking_result

            # If booking successful and trip_id provided, store in TripSage database
            if booking_params.trip_id:
                await self._store_booking_in_database(
                    trip_id=booking_params.trip_id, booking_result=booking_result
                )

            # Store in knowledge graph if memory client is available
            if self.memory_client:
                await self._update_knowledge_graph(booking_result)
            else:
                # Try to get a memory client if not provided
                try:
                    memory_client = get_memory_client()
                    await self._update_knowledge_graph(booking_result, memory_client)
                except Exception as e:
                    logger.warning(f"Failed to update knowledge graph: {str(e)}")

            return {
                "success": True,
                "booking_id": booking_result.get("booking_id"),
                "confirmed": booking_result.get("status") == "confirmed",
                "total_price": booking_result.get("total_amount"),
                "currency": booking_result.get("currency"),
                "booking_details": booking_result,
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
            db_client = get_db_client()

            # Extract flight information
            slices = booking_result.get("slices", [])
            for _slice_idx, slice_data in enumerate(slices):
                # Create flight record for each slice
                flight_data = {
                    "trip_id": trip_id,
                    "airline": slice_data.get("operating_carrier", {}).get(
                        "name", "Unknown Airline"
                    ),
                    "flight_number": "-".join(
                        [
                            segment.get("operating_carrier_code", ""),
                            segment.get("operating_flight_number", ""),
                        ]
                        for segment in slice_data.get("segments", [])
                    ),
                    "origin": slice_data.get("origin", {}).get("iata_code", ""),
                    "destination": slice_data.get("destination", {}).get(
                        "iata_code", ""
                    ),
                    "departure_time": slice_data.get("departure_datetime", ""),
                    "arrival_time": slice_data.get("arrival_datetime", ""),
                    "price": (
                        booking_result.get("total_amount", 0) / len(slices)
                        if len(slices) > 0
                        else 0
                    ),
                    "booking_reference": booking_result.get("booking_reference", ""),
                    "status": "booked",
                }

                # Add flight to database
                await db_client.create_flight(flight_data)

        except Exception as e:
            logger.error(f"Error storing booking in database: {str(e)}")
            raise

    async def _update_knowledge_graph(
        self, booking_result: Dict[str, Any], memory_client=None
    ) -> None:
        """Update knowledge graph with booking information.

        Args:
            booking_result: Booking result from Flights MCP
            memory_client: Optional memory client instance
        """
        try:
            # Get memory client if not provided
            if memory_client is None:
                if self.memory_client:
                    memory_client = self.memory_client
                else:
                    memory_client = get_memory_client()

            # Extract entities and observations
            booking_id = booking_result.get("booking_id", str(uuid.uuid4()))
            booking_reference = booking_result.get("booking_reference", "")

            # Extract airline information from the first segment of the first slice
            airline = None
            airline_code = None
            if (
                "slices" in booking_result
                and booking_result["slices"]
                and "segments" in booking_result["slices"][0]
                and booking_result["slices"][0]["segments"]
            ):
                first_segment = booking_result["slices"][0]["segments"][0]
                airline = first_segment.get("operating_carrier", {}).get("name")
                airline_code = first_segment.get("operating_carrier_code")

            # Create route string (origin-destination)
            origin = None
            destination = None
            if "slices" in booking_result and booking_result["slices"]:
                first_slice = booking_result["slices"][0]
                origin = first_slice.get("origin", {}).get("iata_code")
                destination = first_slice.get("destination", {}).get("iata_code")

            route = (
                f"{origin}-{destination}" if origin and destination else "Unknown Route"
            )

            # Create booking entity
            entity_name = f"Booking:{booking_id}"
            observations = [
                f"Booking reference: {booking_reference}",
                f"Route: {route}",
                (
                    f"Price: {booking_result.get('total_amount')} "
                    f"{booking_result.get('currency')}"
                ),
                f"Status: {booking_result.get('status')}",
            ]

            if airline:
                observations.append(f"Airline: {airline}")

            await memory_client.create_entities(
                [
                    {
                        "name": entity_name,
                        "entityType": "Booking",
                        "observations": observations,
                    }
                ]
            )

            # Create relations
            relations = []

            # Relation to airline if available
            if airline:
                # Create airline entity if it doesn't exist
                await memory_client.create_entities(
                    [
                        {
                            "name": airline,
                            "entityType": "Airline",
                            "observations": [
                                (
                                    f"Airline code: {airline_code}"
                                    if airline_code
                                    else "No airline code available"
                                )
                            ],
                        }
                    ]
                )

                relations.append(
                    {"from": entity_name, "relationType": "with_airline", "to": airline}
                )

            # Relations to origin/destination
            if origin:
                # Create origin airport entity if it doesn't exist
                await memory_client.create_entities(
                    [
                        {
                            "name": origin,
                            "entityType": "Airport",
                            "observations": [
                                f"IATA code: {origin}",
                                "Created from booking information",
                            ],
                        }
                    ]
                )

                relations.append(
                    {"from": entity_name, "relationType": "departs_from", "to": origin}
                )

            if destination:
                # Create destination airport entity if it doesn't exist
                await memory_client.create_entities(
                    [
                        {
                            "name": destination,
                            "entityType": "Airport",
                            "observations": [
                                f"IATA code: {destination}",
                                "Created from booking information",
                            ],
                        }
                    ]
                )

                relations.append(
                    {
                        "from": entity_name,
                        "relationType": "arrives_at",
                        "to": destination,
                    }
                )

            # Create relations if any exist
            if relations:
                await memory_client.create_relations(relations)

        except Exception as e:
            logger.warning(f"Error updating knowledge graph: {str(e)}")
            raise

    async def get_booking_details(self, booking_id: str) -> Dict[str, Any]:
        """Get details of a flight booking.

        Args:
            booking_id: Booking ID or reference number

        Returns:
            Booking details
        """
        try:
            # Check database first
            try:
                db_client = get_db_client()
                booking = await db_client.get_flight_by_booking_reference(booking_id)
                if booking:
                    return {
                        "success": True,
                        "booking_id": booking_id,
                        "booking_details": booking,
                    }
            except Exception as e:
                logger.warning(f"Error getting booking from database: {str(e)}")

            # Try to get from Flights MCP (if implemented)
            try:
                booking_details = await self.flights_client.get_booking(booking_id)
                return {
                    "success": True,
                    "booking_id": booking_id,
                    "booking_details": booking_details,
                }
            except Exception as e:
                logger.warning(f"Error getting booking from Flights MCP: {str(e)}")

            # Try knowledge graph as last resort
            try:
                memory_client = self.memory_client or get_memory_client()
                booking_entity = await memory_client.open_nodes(
                    [f"Booking:{booking_id}"]
                )
                if booking_entity:
                    return {
                        "success": True,
                        "booking_id": booking_id,
                        "booking_details": booking_entity[0],
                    }
            except Exception as e:
                logger.warning(f"Error getting booking from knowledge graph: {str(e)}")

            # If all methods fail, return error
            return {
                "success": False,
                "error": f"Booking not found with ID: {booking_id}",
            }

        except Exception as e:
            logger.error(f"Error getting booking details: {str(e)}")
            return {"error": f"Error retrieving booking details: {str(e)}"}

    async def cancel_booking(self, booking_id: str) -> Dict[str, Any]:
        """Cancel a flight booking.

        Note: When using ravinahp/flights-mcp, booking operations (including cancellation)
        are not supported as it is a read-only MCP server. This method will return an
        error in that case.

        Args:
            booking_id: Booking ID or reference number

        Returns:
            Cancellation confirmation, or error if using ravinahp/flights-mcp
        """
        try:
            # Call Flights MCP to cancel booking (if implemented)
            try:
                cancellation_result = await self.flights_client.cancel_booking(
                    booking_id
                )

                # Update database
                try:
                    db_client = get_db_client()
                    await db_client.update_flight_status(booking_id, "cancelled")
                except Exception as e:
                    logger.warning(f"Error updating booking in database: {str(e)}")

                # Update knowledge graph
                try:
                    memory_client = self.memory_client or get_memory_client()
                    await memory_client.add_observations(
                        [
                            {
                                "entityName": f"Booking:{booking_id}",
                                "contents": [
                                    "Status: cancelled",
                                    f"Cancelled at: {datetime.now().isoformat()}",
                                ],
                            }
                        ]
                    )
                except Exception as e:
                    logger.warning(
                        f"Error updating booking in knowledge graph: {str(e)}"
                    )

                return {
                    "success": True,
                    "booking_id": booking_id,
                    "status": "cancelled",
                    "cancellation_details": cancellation_result,
                }
            except Exception as e:
                logger.error(f"Error cancelling booking with Flights MCP: {str(e)}")
                return {
                    "success": False,
                    "error": f"Failed to cancel booking: {str(e)}",
                }

        except Exception as e:
            logger.error(f"Error cancelling booking: {str(e)}")
            return {"error": f"Error cancelling booking: {str(e)}"}

    async def track_price_changes(
        self,
        booking_id: str,
        notification_threshold: Optional[float] = None,
        notification_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Track price changes for a booked flight.

        Args:
            booking_id: Booking ID or reference number
            notification_threshold: Price threshold for notifications (percentage)
            notification_email: Email to send notifications to

        Returns:
            Price tracking confirmation
        """
        try:
            # Get booking details
            booking_details = await self.get_booking_details(booking_id)
            if "error" in booking_details:
                return booking_details

            # Extract route information
            origin = None
            destination = None
            departure_date = None
            return_date = None

            booking = booking_details.get("booking_details", {})

            # Extract from database format
            if "origin" in booking and "destination" in booking:
                origin = booking.get("origin")
                destination = booking.get("destination")
                departure_date = (
                    booking.get("departure_time", "").split("T")[0]
                    if "departure_time" in booking
                    else None
                )
                return_date = (
                    booking.get("return_departure_time", "").split("T")[0]
                    if "return_departure_time" in booking
                    else None
                )

            # Extract from Flights MCP format
            elif "slices" in booking and booking["slices"]:
                slices = booking["slices"]
                if len(slices) > 0:
                    origin = slices[0].get("origin", {}).get("iata_code")
                    destination = slices[0].get("destination", {}).get("iata_code")
                    departure_date = (
                        slices[0].get("departure_datetime", "").split("T")[0]
                        if "departure_datetime" in slices[0]
                        else None
                    )

                # Check for return slice
                if len(slices) > 1:
                    return_date = (
                        slices[1].get("departure_datetime", "").split("T")[0]
                        if "departure_datetime" in slices[1]
                        else None
                    )

            # Extract from knowledge graph format
            elif "observations" in booking:
                for obs in booking.get("observations", []):
                    if obs.startswith("Route:"):
                        route_parts = obs.replace("Route:", "").strip().split("-")
                        if len(route_parts) == 2:
                            origin, destination = route_parts

            # If we couldn't extract the necessary information, return error
            if not origin or not destination or not departure_date:
                return {
                    "success": False,
                    "error": "Could not extract route information from booking",
                }

            # Call Flights MCP to track price
            tracking_result = await self.flights_client.track_flight_price(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                notification_email=notification_email,
                price_threshold=notification_threshold,
            )

            return {
                "success": True,
                "booking_id": booking_id,
                "tracking_id": tracking_result.get("tracking_id"),
                "route": f"{origin}-{destination}",
                "departure_date": departure_date,
                "return_date": return_date,
                "tracking_details": tracking_result,
            }

        except Exception as e:
            logger.error(f"Error setting up price tracking: {str(e)}")
            return {"error": f"Error setting up price tracking: {str(e)}"}
