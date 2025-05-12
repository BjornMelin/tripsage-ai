"""
Flight repository for TripSage.

This module provides the Flight repository for interacting with the flights table.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.db.models.flight import BookingStatus, Flight
from src.db.repositories.base import BaseRepository
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)


class FlightRepository(BaseRepository[Flight]):
    """
    Repository for Flight entities.

    This repository provides methods for interacting with the flights table.
    """

    def __init__(self):
        """Initialize the repository with the Flight model class."""
        super().__init__(Flight)

    async def find_by_trip_id(self, trip_id: int) -> List[Flight]:
        """
        Find flights for a specific trip.

        Args:
            trip_id: The ID of the trip to find flights for.

        Returns:
            List of flights for the trip.
        """
        return await self.find_by(trip_id=trip_id)

    async def find_by_route(self, origin: str, destination: str) -> List[Flight]:
        """
        Find flights by origin and destination.

        Args:
            origin: The origin airport or city code.
            destination: The destination airport or city code.

        Returns:
            List of flights matching the route.
        """
        try:
            response = (
                self._get_table()
                .select("*")
                .eq("origin", origin)
                .eq("destination", destination)
                .execute()
            )
            if not response.data:
                return []

            return Flight.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding flights by route: {e}")
            raise

    async def find_by_date_range(
        self, start_date: datetime, end_date: datetime, trip_id: Optional[int] = None
    ) -> List[Flight]:
        """
        Find flights within a date range.

        Args:
            start_date: The start date for the search range.
            end_date: The end date for the search range.
            trip_id: Optional trip ID to filter flights.

        Returns:
            List of flights within the date range.
        """
        try:
            query = (
                self._get_table()
                .select("*")
                .gte("departure_time", start_date.isoformat())
                .lte("departure_time", end_date.isoformat())
            )

            if trip_id is not None:
                query = query.eq("trip_id", trip_id)

            response = query.execute()
            if not response.data:
                return []

            return Flight.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding flights by date range: {e}")
            raise

    async def update_booking_status(
        self, flight_id: int, new_status: BookingStatus
    ) -> Optional[Flight]:
        """
        Update the booking status of a flight.

        Args:
            flight_id: The ID of the flight to update.
            new_status: The new booking status.

        Returns:
            The updated flight if found, None otherwise.
        """
        flight = await self.get_by_id(flight_id)
        if not flight:
            return None

        flight.booking_status = new_status
        return await self.update(flight)

    async def get_flight_statistics(
        self, trip_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about flights.

        Args:
            trip_id: Optional trip ID to filter flights.

        Returns:
            Dictionary containing flight statistics.
        """
        try:
            # Construct base query
            query = (
                "SELECT COUNT(*) as total_flights, "
                "AVG(price) as avg_price, "
                "MIN(price) as min_price, "
                "MAX(price) as max_price, "
                "COUNT(DISTINCT origin) as distinct_origins, "
                "COUNT(DISTINCT destination) as distinct_destinations "
                f"FROM {self.table_name}"
            )

            # Add trip_id filter if provided
            if trip_id is not None:
                query += f" WHERE trip_id = {trip_id}"

            # Execute query
            response = self._get_client().rpc("query", {"q": query}).execute()

            if not response.data or len(response.data) == 0:
                # Return default statistics if no data found
                return {
                    "total_flights": 0,
                    "avg_price": 0.0,
                    "min_price": 0.0,
                    "max_price": 0.0,
                    "distinct_origins": 0,
                    "distinct_destinations": 0,
                }

            return response.data[0]
        except Exception as e:
            logger.error(f"Error getting flight statistics: {e}")
            # Fallback to default statistics
            return {
                "total_flights": 0,
                "avg_price": 0.0,
                "min_price": 0.0,
                "max_price": 0.0,
                "distinct_origins": 0,
                "distinct_destinations": 0,
            }
