"""
Time Service using Python datetime functionality.

This service provides timezone-aware time operations, eliminating the need for
external MCP services for basic time and timezone calculations.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class TimeZoneInfo(BaseModel):
    """Timezone information."""

    name: str = Field(..., description="Timezone name (e.g., 'America/New_York')")
    abbreviation: str = Field(..., description="Timezone abbreviation (e.g., 'EST')")
    offset: str = Field(..., description="UTC offset (e.g., '-05:00')")
    dst_active: bool = Field(..., description="Whether daylight saving time is active")
    current_time: datetime = Field(..., description="Current time in this timezone")


class TimeConversion(BaseModel):
    """Time conversion result."""

    source_time: datetime = Field(..., description="Original time")
    source_timezone: str = Field(..., description="Source timezone")
    target_time: datetime = Field(..., description="Converted time")
    target_timezone: str = Field(..., description="Target timezone")
    time_difference: str = Field(..., description="Time difference description")


class WorldClock(BaseModel):
    """World clock entry."""

    city: str = Field(..., description="City name")
    timezone: str = Field(..., description="Timezone name")
    current_time: datetime = Field(..., description="Current time")
    local_date: str = Field(..., description="Local date string")
    local_time: str = Field(..., description="Local time string")
    utc_offset: str = Field(..., description="UTC offset")


class TimeService:
    """Service for timezone and time operations using Python datetime."""

    def __init__(self):
        """Initialize Time service."""
        self._major_timezones = {
            "UTC": "UTC",
            "EST": "America/New_York",
            "PST": "America/Los_Angeles",
            "CST": "America/Chicago",
            "MST": "America/Denver",
            "GMT": "Europe/London",
            "CET": "Europe/Paris",
            "JST": "Asia/Tokyo",
            "IST": "Asia/Kolkata",
            "AEST": "Australia/Sydney",
            "CEST": "Europe/Berlin",
            "BST": "Europe/London",
        }

    def get_current_time(self, timezone_name: Optional[str] = None) -> datetime:
        """
        Get current time in specified timezone.

        Args:
            timezone_name: Timezone name (e.g., 'America/New_York') or None for UTC

        Returns:
            Current datetime in specified timezone
        """
        if timezone_name is None:
            return datetime.now(timezone.utc)

        try:
            # Handle common timezone abbreviations
            if timezone_name.upper() in self._major_timezones:
                timezone_name = self._major_timezones[timezone_name.upper()]

            tz = ZoneInfo(timezone_name)
            return datetime.now(tz)

        except Exception as e:
            logger.error(f"Error getting time for timezone {timezone_name}: {e}")
            # Fallback to UTC
            return datetime.now(timezone.utc)

    def get_timezone_info(self, timezone_name: str) -> TimeZoneInfo:
        """
        Get detailed timezone information.

        Args:
            timezone_name: Timezone name

        Returns:
            Timezone information
        """
        try:
            # Handle common timezone abbreviations
            # original_name = timezone_name
            if timezone_name.upper() in self._major_timezones:
                timezone_name = self._major_timezones[timezone_name.upper()]

            tz = ZoneInfo(timezone_name)
            current_time = datetime.now(tz)

            # Get timezone offset
            offset = current_time.strftime("%z")
            formatted_offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"

            # Get timezone abbreviation
            abbreviation = current_time.strftime("%Z")

            # Check if DST is active
            dst_active = bool(
                current_time.dst() and current_time.dst().total_seconds() > 0
            )

            return TimeZoneInfo(
                name=timezone_name,
                abbreviation=abbreviation,
                offset=formatted_offset,
                dst_active=dst_active,
                current_time=current_time,
            )

        except Exception as e:
            logger.error(f"Error getting timezone info for {timezone_name}: {e}")
            # Fallback to UTC
            utc_time = datetime.now(timezone.utc)
            return TimeZoneInfo(
                name="UTC",
                abbreviation="UTC",
                offset="+00:00",
                dst_active=False,
                current_time=utc_time,
            )

    def convert_time(
        self,
        time_to_convert: Union[datetime, str],
        source_timezone: str,
        target_timezone: str,
    ) -> TimeConversion:
        """
        Convert time between timezones.

        Args:
            time_to_convert: Time to convert (datetime or ISO string)
            source_timezone: Source timezone name
            target_timezone: Target timezone name

        Returns:
            Time conversion result
        """
        try:
            # Parse input time
            if isinstance(time_to_convert, str):
                # Try to parse ISO format
                try:
                    parsed_time = datetime.fromisoformat(
                        time_to_convert.replace("Z", "+00:00")
                    )
                except ValueError:
                    # Try other common formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                        try:
                            parsed_time = datetime.strptime(time_to_convert, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(
                            f"Unable to parse time format: {time_to_convert}"
                        )
            else:
                parsed_time = time_to_convert

            # Handle timezone abbreviations
            if source_timezone.upper() in self._major_timezones:
                source_timezone = self._major_timezones[source_timezone.upper()]
            if target_timezone.upper() in self._major_timezones:
                target_timezone = self._major_timezones[target_timezone.upper()]

            # Convert to source timezone if naive
            if parsed_time.tzinfo is None:
                source_tz = ZoneInfo(source_timezone)
                source_time = parsed_time.replace(tzinfo=source_tz)
            else:
                source_time = parsed_time

            # Convert to target timezone
            target_tz = ZoneInfo(target_timezone)
            target_time = source_time.astimezone(target_tz)

            # Calculate time difference
            time_diff = target_time.utcoffset() - source_time.utcoffset()
            hours_diff = time_diff.total_seconds() / 3600

            if hours_diff == 0:
                diff_description = "Same time"
            elif hours_diff > 0:
                diff_description = f"{hours_diff:+.1f} hours ahead"
            else:
                diff_description = f"{abs(hours_diff):.1f} hours behind"

            return TimeConversion(
                source_time=source_time,
                source_timezone=source_timezone,
                target_time=target_time,
                target_timezone=target_timezone,
                time_difference=diff_description,
            )

        except Exception as e:
            logger.error(f"Error converting time: {e}")
            raise

    def get_world_clock(self, cities: Optional[List[str]] = None) -> List[WorldClock]:
        """
        Get world clock for major cities.

        Args:
            cities: List of city/timezone names (optional)

        Returns:
            List of world clock entries
        """
        # Default major cities
        if cities is None:
            cities = [
                "UTC",
                "New York",
                "Los Angeles",
                "London",
                "Paris",
                "Tokyo",
                "Sydney",
                "Mumbai",
            ]

        city_timezones = {
            "UTC": "UTC",
            "New York": "America/New_York",
            "Los Angeles": "America/Los_Angeles",
            "Chicago": "America/Chicago",
            "Denver": "America/Denver",
            "London": "Europe/London",
            "Paris": "Europe/Paris",
            "Berlin": "Europe/Berlin",
            "Tokyo": "Asia/Tokyo",
            "Mumbai": "Asia/Kolkata",
            "Sydney": "Australia/Sydney",
            "Shanghai": "Asia/Shanghai",
            "Dubai": "Asia/Dubai",
        }

        world_clock = []

        for city in cities:
            try:
                # Get timezone for city
                if city in city_timezones:
                    timezone_name = city_timezones[city]
                elif city.upper() in self._major_timezones:
                    timezone_name = self._major_timezones[city.upper()]
                    city = city.upper()  # Use abbreviation as city name
                else:
                    # Assume it's already a timezone name
                    timezone_name = city

                tz = ZoneInfo(timezone_name)
                current_time = datetime.now(tz)

                # Format offset
                offset = current_time.strftime("%z")
                formatted_offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"

                world_clock.append(
                    WorldClock(
                        city=city,
                        timezone=timezone_name,
                        current_time=current_time,
                        local_date=current_time.strftime("%Y-%m-%d"),
                        local_time=current_time.strftime("%H:%M:%S"),
                        utc_offset=formatted_offset,
                    )
                )

            except Exception as e:
                logger.warning(f"Error getting time for {city}: {e}")
                continue

        return world_clock

    def get_time_until(
        self, target_time: Union[datetime, str], timezone_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate time remaining until a target time.

        Args:
            target_time: Target datetime or ISO string
            timezone_name: Timezone for calculation (None for UTC)

        Returns:
            Dictionary with time remaining information
        """
        try:
            # Parse target time
            if isinstance(target_time, str):
                try:
                    parsed_time = datetime.fromisoformat(
                        target_time.replace("Z", "+00:00")
                    )
                except ValueError:
                    parsed_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
            else:
                parsed_time = target_time

            # Get current time in specified timezone
            current_time = self.get_current_time(timezone_name)

            # Ensure both times have timezone info
            if parsed_time.tzinfo is None:
                if timezone_name:
                    tz = ZoneInfo(timezone_name)
                    parsed_time = parsed_time.replace(tzinfo=tz)
                else:
                    parsed_time = parsed_time.replace(tzinfo=timezone.utc)

            # Calculate difference
            time_diff = parsed_time - current_time

            if time_diff.total_seconds() < 0:
                return {
                    "status": "past",
                    "message": "Target time has already passed",
                    "time_ago": self._format_timedelta(abs(time_diff)),
                    "total_seconds": time_diff.total_seconds(),
                }
            else:
                return {
                    "status": "future",
                    "message": "Time remaining until target",
                    "time_remaining": self._format_timedelta(time_diff),
                    "total_seconds": time_diff.total_seconds(),
                }

        except Exception as e:
            logger.error(f"Error calculating time until {target_time}: {e}")
            return {
                "status": "error",
                "message": f"Error calculating time: {e}",
                "time_remaining": None,
                "total_seconds": 0,
            }

    def _format_timedelta(self, td: timedelta) -> str:
        """Format timedelta into human-readable string."""
        total_seconds = int(td.total_seconds())

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 and len(parts) < 2:  # Only show seconds if less than hours
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        if not parts:
            return "0 seconds"

        return ", ".join(parts)

    def get_business_hours_status(
        self,
        timezone_name: str,
        business_start: str = "09:00",
        business_end: str = "17:00",
        weekdays_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Check if current time is within business hours.

        Args:
            timezone_name: Timezone to check
            business_start: Business start time (HH:MM format)
            business_end: Business end time (HH:MM format)
            weekdays_only: Only consider Monday-Friday as business days

        Returns:
            Business hours status information
        """
        try:
            current_time = self.get_current_time(timezone_name)
            current_hour_min = current_time.strftime("%H:%M")
            current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday

            is_business_day = not weekdays_only or current_weekday < 5  # Monday-Friday
            is_business_hours = business_start <= current_hour_min <= business_end

            return {
                "is_business_hours": is_business_day and is_business_hours,
                "is_business_day": is_business_day,
                "current_time": current_time.strftime("%H:%M"),
                "current_day": current_time.strftime("%A"),
                "business_start": business_start,
                "business_end": business_end,
                "timezone": timezone_name,
            }

        except Exception as e:
            logger.error(f"Error checking business hours: {e}")
            return {"is_business_hours": False, "error": str(e)}

    def get_available_timezones(self, region: Optional[str] = None) -> List[str]:
        """
        Get list of available timezone names.

        Args:
            region: Optional region filter (e.g., 'America', 'Europe')

        Returns:
            List of timezone names
        """
        try:
            import zoneinfo

            timezones = list(zoneinfo.available_timezones())

            if region:
                timezones = [tz for tz in timezones if tz.startswith(region)]

            return sorted(timezones)

        except Exception as e:
            logger.error(f"Error getting available timezones: {e}")
            return list(self._major_timezones.values())


# Convenience functions
def get_current_time_utc() -> datetime:
    """Get current UTC time."""
    service = TimeService()
    return service.get_current_time()


def convert_timezone(time_str: str, from_tz: str, to_tz: str) -> TimeConversion:
    """Quick timezone conversion."""
    service = TimeService()
    return service.convert_time(time_str, from_tz, to_tz)


def get_world_time() -> List[WorldClock]:
    """Get world clock for major cities."""
    service = TimeService()
    return service.get_world_clock()


__all__ = [
    "TimeService",
    "TimeZoneInfo",
    "TimeConversion",
    "WorldClock",
    "get_current_time_utc",
    "convert_timezone",
    "get_world_time",
]
