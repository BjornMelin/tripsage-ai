"""
Flight repository for TripSage.

This module provides the Flight repository for interacting with the flights table.
"""

import logging
from datetime import datetime
from typing import List, Optional, Union, Dict, Any

from src.db.models.flight import Flight, BookingStatus
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
    
    async def find_by_origin_destination(
        self, 
        origin: str, 
        destination: str,
        case_sensitive: bool = False
    ) -> List[Flight]:
        """
        Find flights by origin and destination.
        
        Args:
            origin: The origin to search for.
            destination: The destination to search for.
            case_sensitive: Whether to perform a case-sensitive search.
            
        Returns:
            List of flights matching the origin and destination.
        """
        try:
            query = self._get_table().select("*")
            
            if case_sensitive:
                query = query.eq("origin", origin).eq("destination", destination)
            else:
                query = query.ilike("origin", origin).ilike("destination", destination)
            
            response = query.execute()
            if not response.data:
                return []
            
            return Flight.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding flights by origin and destination: {e}")
            raise
    
    async def find_by_date_range(
        self, 
        start_datetime: Optional[datetime] = None, 
        end_datetime: Optional[datetime] = None
    ) -> List[Flight]:
        """
        Find flights within a departure date range.
        
        Args:
            start_datetime: The start date and time of the range. If None, all flights up to end_datetime.
            end_datetime: The end date and time of the range. If None, all flights from start_datetime.
            
        Returns:
            List of flights within the date range.
        """
        try:
            query = self._get_table().select("*")
            
            if start_datetime:
                query = query.gte("departure_time", start_datetime.isoformat())
            if end_datetime:
                query = query.lte("departure_time", end_datetime.isoformat())
                
            response = query.execute()
            if not response.data:
                return []
            
            return Flight.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding flights by date range: {e}")
            raise
    
    async def find_by_price_range(self, min_price: float, max_price: float) -> List[Flight]:
        """
        Find flights within a price range.
        
        Args:
            min_price: The minimum price.
            max_price: The maximum price.
            
        Returns:
            List of flights within the price range.
        """
        try:
            response = self._get_table().select("*")\
                .gte("price", min_price)\
                .lte("price", max_price)\
                .execute()
                
            if not response.data:
                return []
            
            return Flight.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding flights by price range: {e}")
            raise
    
    async def find_by_booking_status(self, status: Union[BookingStatus, str]) -> List[Flight]:
        """
        Find flights by booking status.
        
        Args:
            status: The booking status to search for. Can be a BookingStatus enum or string.
            
        Returns:
            List of flights with the specified booking status.
        """
        # Convert to string if enum
        status_str = status.value if isinstance(status, BookingStatus) else status
        
        try:
            response = self._get_table().select("*").eq("booking_status", status_str).execute()
            if not response.data:
                return []
            
            return Flight.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding flights by booking status: {e}")
            raise
    
    async def update_booking_status(
        self, 
        flight_id: int, 
        status: Union[BookingStatus, str]
    ) -> Optional[Flight]:
        """
        Update a flight's booking status.
        
        Args:
            flight_id: The ID of the flight to update.
            status: The new booking status. Can be a BookingStatus enum or string.
            
        Returns:
            The updated flight if found, None otherwise.
        """
        # Convert to string if enum
        status_str = status.value if isinstance(status, BookingStatus) else status
        
        try:
            response = self._get_table()\
                .update({"booking_status": status_str})\
                .eq("id", flight_id)\
                .execute()
                
            if not response.data or len(response.data) == 0:
                return None
            
            return Flight.from_row(response.data[0])
        except Exception as e:
            logger.error(f"Error updating flight booking status: {e}")
            raise
    
    async def find_by_airline(self, airline: str, partial_match: bool = True) -> List[Flight]:
        """
        Find flights by airline.
        
        Args:
            airline: The airline to search for.
            partial_match: Whether to perform a partial match (contains) or exact match.
            
        Returns:
            List of flights with the specified airline.
        """
        try:
            query = self._get_table().select("*")
            if partial_match:
                query = query.ilike("airline", f"%{airline}%")
            else:
                query = query.eq("airline", airline)
                
            response = query.execute()
            if not response.data:
                return []
            
            return Flight.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding flights by airline: {e}")
            raise
    
    async def get_recent_searches(self, limit: int = 20) -> List[Flight]:
        """
        Get recently searched flights, ordered by search timestamp.
        
        Args:
            limit: Maximum number of flights to return.
            
        Returns:
            List of recently searched flights.
        """
        try:
            response = self._get_table().select("*")\
                .order("search_timestamp", {"ascending": False})\
                .limit(limit)\
                .execute()
                
            if not response.data:
                return []
            
            return Flight.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error getting recent flight searches: {e}")
            raise