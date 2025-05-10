"""
Trip repository for TripSage.

This module provides the Trip repository for interacting with the trips table.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Union

from src.db.models.trip import Trip, TripStatus, TripType
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

    async def find_by_destination(self, destination: str) -> List[Trip]:
        """
        Find trips by destination.

        Args:
            destination: The destination to search for (case insensitive partial match).

        Returns:
            List of trips matching the destination.
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

    async def find_by_date_range(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Trip]:
        """
        Find trips within a date range.

        Args:
            start_date: The start date of the range. If None, all trips up to end_date.
            end_date: The end date of the range. If None, all trips from start_date.

        Returns:
            List of trips within the date range.
        """
        try:
            query = self._get_table().select("*")

            if start_date:
                query = query.gte("start_date", start_date.isoformat())
            if end_date:
                query = query.lte("end_date", end_date.isoformat())

            response = query.execute()
            if not response.data:
                return []

            return Trip.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding trips by date range: {e}")
            raise

    async def find_by_status(self, status: Union[TripStatus, str]) -> List[Trip]:
        """
        Find trips by status.

        Args:
            status: The status to search for. Can be a TripStatus enum or string.

        Returns:
            List of trips with the specified status.
        """
        # Convert to string if enum
        status_str = status.value if isinstance(status, TripStatus) else status

        try:
            response = self._get_table().select("*").eq("status", status_str).execute()
            if not response.data:
                return []

            return Trip.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding trips by status: {e}")
            raise

    async def find_by_budget_range(
        self, min_budget: float, max_budget: float
    ) -> List[Trip]:
        """
        Find trips within a budget range.

        Args:
            min_budget: The minimum budget.
            max_budget: The maximum budget.

        Returns:
            List of trips within the budget range.
        """
        try:
            response = (
                self._get_table()
                .select("*")
                .gte("budget", min_budget)
                .lte("budget", max_budget)
                .execute()
            )

            if not response.data:
                return []

            return Trip.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding trips by budget range: {e}")
            raise

    async def update_status(
        self, trip_id: int, status: Union[TripStatus, str]
    ) -> Optional[Trip]:
        """
        Update a trip's status.

        Args:
            trip_id: The ID of the trip to update.
            status: The new status. Can be a TripStatus enum or string.

        Returns:
            The updated trip if found, None otherwise.
        """
        # Convert to string if enum
        status_str = status.value if isinstance(status, TripStatus) else status

        try:
            response = (
                self._get_table()
                .update({"status": status_str})
                .eq("id", trip_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                return None

            return Trip.from_row(response.data[0])
        except Exception as e:
            logger.error(f"Error updating trip status: {e}")
            raise

    async def find_upcoming_trips(self, from_date: Optional[date] = None) -> List[Trip]:
        """
        Find upcoming trips that haven't started yet.

        Args:
            from_date: The date to check from. Defaults to today.

        Returns:
            List of upcoming trips.
        """
        if from_date is None:
            from_date = date.today()

        try:
            response = (
                self._get_table()
                .select("*")
                .gte("start_date", from_date.isoformat())
                .order("start_date")
                .execute()
            )

            if not response.data:
                return []

            return Trip.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding upcoming trips: {e}")
            raise

    async def find_active_trips(self, on_date: Optional[date] = None) -> List[Trip]:
        """
        Find trips that are active on a specific date.

        Args:
            on_date: The date to check. Defaults to today.

        Returns:
            List of active trips.
        """
        if on_date is None:
            on_date = date.today()

        try:
            date_str = on_date.isoformat()
            response = (
                self._get_table()
                .select("*")
                .lte("start_date", date_str)
                .gte("end_date", date_str)
                .eq("status", TripStatus.BOOKED.value)
                .execute()
            )

            if not response.data:
                return []

            return Trip.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding active trips: {e}")
            raise
