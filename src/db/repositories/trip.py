"""
Trip repository for TripSage.

This module provides the Trip repository for interacting with the trips table.
"""

from typing import List, Optional

from src.db.models.trip import Trip
from src.db.repositories.base import BaseRepository
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)


class TripRepository(BaseRepository[Trip]):
    """
    Repository for Trip entities.

    This repository provides methods for interacting with the trips table.
    """

    def __init__(self):
        """Initialize the repository with the Trip model class."""
        super().__init__(Trip)

    async def find_by_user_id(self, user_id: int) -> List[Trip]:
        """
        Find trips for a specific user.

        Args:
            user_id: The ID of the user to find trips for.

        Returns:
            List of trips belonging to the user.
        """
        return await self.find_by(user_id=user_id)

    async def find_by_destination(self, destination: str) -> List[Trip]:
        """
        Find trips by destination.

        Args:
            destination: The destination to search for.

        Returns:
            List of trips with matching destination.
        """
        try:
            response = (
                self._get_table()
                .select("*")
                .ilike("destination", f"%{destination}%")
                .execute()
            )
            if not response.data:
                return []

            return Trip.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding trips by destination: {e}")
            raise

    async def find_by_date_range(self, start_date: str, end_date: str) -> List[Trip]:
        """
        Find trips within a date range.

        Args:
            start_date: The start date in ISO format (YYYY-MM-DD).
            end_date: The end date in ISO format (YYYY-MM-DD).

        Returns:
            List of trips with dates overlapping the specified range.
        """
        try:
            # Find trips where:
            # 1. Trip start_date is between provided start_date and end_date, OR
            # 2. Trip end_date is between provided start_date and end_date, OR
            # 3. Trip completely encompasses the provided date range
            query = (
                self._get_table()
                .select("*")
                .filter(
                    f"(start_date >= '{start_date}' AND start_date <= '{end_date}') OR "
                    f"(end_date >= '{start_date}' AND end_date <= '{end_date}') OR "
                    f"(start_date <= '{start_date}' AND end_date >= '{end_date}')"
                )
                .execute()
            )

            if not query.data:
                return []

            return Trip.from_rows(query.data)
        except Exception as e:
            logger.error(f"Error finding trips by date range: {e}")
            raise

    async def get_upcoming_trips(self, user_id: Optional[int] = None) -> List[Trip]:
        """
        Get upcoming trips (trips with start_date in the future).

        Args:
            user_id: Optional user ID to filter trips by user.

        Returns:
            List of upcoming trips.
        """
        try:
            today = "CURRENT_DATE"
            query = self._get_table().select("*").gte("start_date", today)

            if user_id is not None:
                query = query.eq("user_id", user_id)

            response = query.execute()

            if not response.data:
                return []

            return Trip.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding upcoming trips: {e}")
            raise
