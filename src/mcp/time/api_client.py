"""
Time API client implementations for TripSage.

This module provides API client implementations for time and
timezone data providers.
"""

import datetime
import time
import zoneinfo
from enum import Enum
from typing import Any, Dict, List

import pytz
from pydantic import BaseModel, ConfigDict

from ...cache.redis_cache import redis_cache
from ...utils.config import get_config
from ...utils.logging import get_module_logger

logger = get_module_logger(__name__)
config = get_config()


class TimeFormat(str, Enum):
    """Time format options."""

    FULL = "full"
    SHORT = "short"
    DATE_ONLY = "date_only"
    TIME_ONLY = "time_only"
    ISO = "iso"


class TimeZoneDatabase(BaseModel):
    """Timezone database service."""

    model_config = ConfigDict(extra="forbid", validate_default=True)

    @redis_cache.cached(
        "timezone_list", 86400 * 7
    )  # Cache for 1 week (timezones rarely change)
    async def list_timezones(self) -> List[str]:
        """List all available timezones.

        Returns:
            List of timezone names
        """
        # Use zoneinfo first (Python 3.9+)
        try:
            zones = sorted(zoneinfo.available_timezones())
            if zones:
                return zones
        except Exception:
            pass

        # Fallback to pytz
        zones = sorted(pytz.all_timezones)
        return zones

    @redis_cache.cached("timezone_info", 86400 * 7)  # Cache for 1 week
    async def get_timezone_info(self, timezone: str) -> Dict[str, Any]:
        """Get information about a timezone.

        Args:
            timezone: IANA timezone name

        Returns:
            Timezone information

        Raises:
            ValueError: If timezone is invalid
        """
        try:
            # Get current time in the timezone
            tz = pytz.timezone(timezone)
            now = datetime.datetime.now(tz)

            # Get timezone abbreviation
            tzname = now.tzname()

            # Get UTC offset
            offset = now.utcoffset()
            if offset is None:
                offset_seconds = 0
            else:
                offset_seconds = int(offset.total_seconds())
            offset_hours = offset_seconds // 3600
            offset_minutes = (abs(offset_seconds) % 3600) // 60

            # Format UTC offset
            if offset_hours >= 0:
                offset_str = f"+{offset_hours:02d}:{offset_minutes:02d}"
            else:
                offset_str = f"-{abs(offset_hours):02d}:{offset_minutes:02d}"

            # Check if timezone is currently in DST
            is_dst = now.dst() is not None and now.dst().total_seconds() > 0

            return {
                "timezone": timezone,
                "abbreviation": tzname,
                "utc_offset": offset_str,
                "utc_offset_seconds": offset_seconds,
                "is_dst": is_dst,
            }
        except pytz.exceptions.UnknownTimeZoneError as e:
            raise ValueError(f"Unknown timezone: {timezone}") from e
        except Exception as e:
            raise ValueError(f"Error getting timezone info: {str(e)}") from e

    @redis_cache.cached("current_time", 60)  # Cache for 1 minute
    async def get_current_time(self, timezone: str) -> Dict[str, Any]:
        """Get current time in a timezone.

        Args:
            timezone: IANA timezone name

        Returns:
            Current time information

        Raises:
            ValueError: If timezone is invalid
        """
        try:
            # Get timezone info
            tz_info = await self.get_timezone_info(timezone)

            # Get current time in the timezone
            tz = pytz.timezone(timezone)
            now = datetime.datetime.now(tz)

            # Format time
            return {
                "timezone": timezone,
                "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "current_date": now.strftime("%Y-%m-%d"),
                "current_time_12h": now.strftime("%I:%M:%S %p"),
                "utc_offset": tz_info["utc_offset"],
                "utc_offset_seconds": tz_info["utc_offset_seconds"],
                "is_dst": tz_info["is_dst"],
                "abbreviation": tz_info["abbreviation"],
                "unix_timestamp": int(time.time()),
            }
        except pytz.exceptions.UnknownTimeZoneError as e:
            raise ValueError(f"Unknown timezone: {timezone}") from e
        except Exception as e:
            raise ValueError(f"Error getting current time: {str(e)}") from e

    @redis_cache.cached("time_convert", 86400)  # Cache for 1 day
    async def convert_time(
        self, time_str: str, source_timezone: str, target_timezone: str
    ) -> Dict[str, Any]:
        """Convert time between timezones.

        Args:
            time_str: Time string in format HH:MM
            source_timezone: Source IANA timezone name
            target_timezone: Target IANA timezone name

        Returns:
            Time conversion information

        Raises:
            ValueError: If timezone is invalid or time format is incorrect
        """
        try:
            # Parse time
            try:
                hour, minute = map(int, time_str.split(":"))
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError(
                        f"Invalid time values: hours={hour}, minutes={minute}"
                    )
            except Exception as e:
                raise ValueError("Time must be in format HH:MM") from e

            # Get source and target timezone objects
            source_tz = pytz.timezone(source_timezone)
            target_tz = pytz.timezone(target_timezone)

            # Get current date in source timezone
            now = datetime.datetime.now(source_tz)
            source_date = now.date()

            # Create datetime with the specified time in source timezone
            source_dt = source_tz.localize(
                datetime.datetime.combine(source_date, datetime.time(hour, minute))
            )

            # Convert to target timezone
            target_dt = source_dt.astimezone(target_tz)

            # Get timezone info
            source_tz_info = await self.get_timezone_info(source_timezone)
            target_tz_info = await self.get_timezone_info(target_timezone)

            # Calculate time difference in hours
            time_diff_seconds = (
                target_tz_info["utc_offset_seconds"]
                - source_tz_info["utc_offset_seconds"]
            )
            time_diff_hours = time_diff_seconds / 3600

            if time_diff_hours >= 0:
                time_diff_str = f"+{time_diff_hours:.1f}"
            else:
                time_diff_str = f"{time_diff_hours:.1f}"

            return {
                "source_timezone": source_timezone,
                "source_time": time_str,
                "target_timezone": target_timezone,
                "target_time": target_dt.strftime("%H:%M"),
                "target_time_12h": target_dt.strftime("%I:%M %p"),
                "time_difference": time_diff_str,
                "time_difference_seconds": time_diff_seconds,
            }
        except pytz.exceptions.UnknownTimeZoneError as e:
            raise ValueError(f"Unknown timezone: {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Error converting time: {str(e)}") from e

    @redis_cache.cached("travel_time", 86400)  # Cache for 1 day
    async def calculate_travel_time(
        self,
        departure_timezone: str,
        departure_time: str,
        arrival_timezone: str,
        arrival_time: str,
    ) -> Dict[str, Any]:
        """Calculate travel time between departure and arrival points.

        Args:
            departure_timezone: Departure IANA timezone name
            departure_time: Departure time in format HH:MM
            arrival_timezone: Arrival IANA timezone name
            arrival_time: Arrival time in format HH:MM

        Returns:
            Travel time information

        Raises:
            ValueError: If timezone is invalid or time format is incorrect
        """
        try:
            # Parse departure time
            try:
                dep_hour, dep_minute = map(int, departure_time.split(":"))
                if not (0 <= dep_hour < 24 and 0 <= dep_minute < 60):
                    raise ValueError(
                        f"Invalid departure time: hours={dep_hour}, "
                        f"minutes={dep_minute}"
                    )
            except Exception as e:
                raise ValueError("Departure time must be in format HH:MM") from e

            # Parse arrival time
            try:
                arr_hour, arr_minute = map(int, arrival_time.split(":"))
                if not (0 <= arr_hour < 24 and 0 <= arr_minute < 60):
                    raise ValueError(
                        f"Invalid arrival time: hours={arr_hour}, minutes={arr_minute}"
                    )
            except Exception as e:
                raise ValueError("Arrival time must be in format HH:MM") from e

            # Get timezone objects
            dep_tz = pytz.timezone(departure_timezone)
            arr_tz = pytz.timezone(arrival_timezone)

            # Get current date in departure timezone
            now = datetime.datetime.now(dep_tz)
            dep_date = now.date()

            # Create datetime for departure
            dep_dt = dep_tz.localize(
                datetime.datetime.combine(dep_date, datetime.time(dep_hour, dep_minute))
            )

            # Create datetime for arrival
            # Assume arrival is on the same day in the arrival timezone
            # If the flight crosses the International Date Line,
            # this might be off by a day
            arr_dt = arr_tz.localize(
                datetime.datetime.combine(dep_date, datetime.time(arr_hour, arr_minute))
            )

            # If arrival time is earlier than departure time, assume it's the next day
            if arr_dt.astimezone(dep_tz) < dep_dt:
                next_day = dep_date + datetime.timedelta(days=1)
                arr_dt = arr_tz.localize(
                    datetime.datetime.combine(
                        next_day, datetime.time(arr_hour, arr_minute)
                    )
                )

            # Calculate travel time
            travel_time = arr_dt.astimezone(dep_tz) - dep_dt
            travel_hours = travel_time.total_seconds() / 3600

            # Format travel time
            travel_hours_int = int(travel_hours)
            travel_minutes = int((travel_hours - travel_hours_int) * 60)

            return {
                "departure_timezone": departure_timezone,
                "departure_time": departure_time,
                "arrival_timezone": arrival_timezone,
                "arrival_time": arrival_time,
                "travel_time_hours": round(travel_hours, 2),
                "travel_time_formatted": f"{travel_hours_int}h {travel_minutes}m",
                "arrival_local_date": arr_dt.strftime("%Y-%m-%d"),
                "next_day_arrival": arr_dt.date() > dep_dt.date(),
            }
        except pytz.exceptions.UnknownTimeZoneError as e:
            raise ValueError(f"Unknown timezone: {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Error calculating travel time: {str(e)}") from e

    @redis_cache.cached("date_format", 86400)  # Cache for 1 day
    async def format_date(
        self,
        date_str: str,
        timezone: str,
        format_type: TimeFormat = TimeFormat.FULL,
        locale: str = "en-US",
    ) -> Dict[str, Any]:
        """Format a date according to timezone and format type.

        Args:
            date_str: Date string in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
            timezone: IANA timezone name
            format_type: Format type
            locale: Locale code

        Returns:
            Formatted date information

        Raises:
            ValueError: If timezone is invalid or date format is incorrect
        """
        try:
            # Parse date
            try:
                if not date_str:
                    # Use current date if not provided
                    dt = datetime.datetime.now()
                else:
                    # Try to parse the date
                    try:
                        dt = datetime.datetime.fromisoformat(date_str)
                    except ValueError:
                        # Try just the date part
                        dt = datetime.datetime.fromisoformat(f"{date_str}T00:00:00")
            except Exception as e:
                raise ValueError(
                    "Date must be in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                ) from e

            # Get timezone
            tz = pytz.timezone(timezone)

            # Localize datetime to timezone
            if dt.tzinfo is None:
                dt = tz.localize(dt)
            else:
                dt = dt.astimezone(tz)

            # Format based on format_type
            if format_type == TimeFormat.FULL:
                formatted = dt.strftime("%A, %B %d, %Y %H:%M:%S")
            elif format_type == TimeFormat.SHORT:
                formatted = dt.strftime("%m/%d/%Y %H:%M")
            elif format_type == TimeFormat.DATE_ONLY:
                formatted = dt.strftime("%Y-%m-%d")
            elif format_type == TimeFormat.TIME_ONLY:
                formatted = dt.strftime("%H:%M:%S")
            elif format_type == TimeFormat.ISO:
                formatted = dt.isoformat()
            else:
                formatted = dt.strftime("%Y-%m-%d %H:%M:%S")

            return {
                "original_date": date_str,
                "timezone": timezone,
                "format_type": format_type,
                "locale": locale,
                "formatted_date": formatted,
                "utc_date": dt.astimezone(pytz.UTC).isoformat(),
            }
        except pytz.exceptions.UnknownTimeZoneError as e:
            raise ValueError(f"Unknown timezone: {timezone}") from e
        except Exception as e:
            raise ValueError(f"Error formatting date: {str(e)}") from e


def get_timezone_db() -> TimeZoneDatabase:
    """Get a timezone database instance.

    Returns:
        TimeZoneDatabase instance
    """
    return TimeZoneDatabase()
