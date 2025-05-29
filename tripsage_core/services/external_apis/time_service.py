"""
Time Service using Python datetime functionality with TripSage Core integration.

This service provides timezone-aware time operations, eliminating the need for
external MCP services for basic time and timezone calculations.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from tripsage_core.config.base_app_settings import CoreAppSettings, get_settings
from tripsage_core.exceptions.exceptions import CoreAPIError, CoreServiceError


class TimeServiceError(CoreAPIError):
    """Exception raised for time service errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="TIME_SERVICE_ERROR",
            service="TimeService",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


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
    """Service for timezone and time operations with Core integration."""

    def __init__(self, settings: Optional[CoreAppSettings] = None):
        """
        Initialize Time service.

        Args:
            settings: Core application settings
        """
        self.settings = settings or get_settings()
        self._connected = False

        # Get time service configuration from settings
        self.default_timezone = getattr(
            self.settings, "time_service_default_timezone", "UTC"
        )
        self.default_date_format = getattr(
            self.settings, "time_service_date_format", "%Y-%m-%d"
        )
        self.default_time_format = getattr(
            self.settings, "time_service_time_format", "%H:%M:%S"
        )
        self.default_datetime_format = getattr(
            self.settings, "time_service_datetime_format", "%Y-%m-%d %H:%M:%S"
        )

        # Business hours defaults from settings
        self.default_business_start = getattr(
            self.settings, "time_service_business_start", "09:00"
        )
        self.default_business_end = getattr(
            self.settings, "time_service_business_end", "17:00"
        )
        self.weekdays_only = getattr(self.settings, "time_service_weekdays_only", True)

        # Major timezone mappings (can be extended via settings)
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

        # Add custom timezone mappings from settings if available
        custom_timezones = getattr(self.settings, "time_service_custom_timezones", {})
        if custom_timezones:
            self._major_timezones.update(custom_timezones)

    async def connect(self) -> None:
        """Initialize the time service."""
        if self._connected:
            return

        try:
            # Test timezone functionality
            _ = datetime.now(timezone.utc)
            self._connected = True

        except Exception as e:
            raise CoreServiceError(
                message=f"Failed to connect time service: {str(e)}",
                code="CONNECTION_FAILED",
                service="TimeService",
                details={"error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """Clean up resources."""
        self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure service is connected."""
        if not self._connected:
            await self.connect()

    async def get_current_time(self, timezone_name: Optional[str] = None) -> datetime:
        """
        Get current time in specified timezone.

        Args:
            timezone_name: Timezone name (e.g., 'America/New_York') or None for default

        Returns:
            Current datetime in specified timezone

        Raises:
            TimeServiceError: When timezone is invalid
        """
        await self.ensure_connected()

        if timezone_name is None:
            timezone_name = self.default_timezone

        try:
            # Handle common timezone abbreviations
            if timezone_name.upper() in self._major_timezones:
                timezone_name = self._major_timezones[timezone_name.upper()]

            if timezone_name == "UTC":
                return datetime.now(timezone.utc)

            tz = ZoneInfo(timezone_name)
            return datetime.now(tz)

        except Exception as e:
            raise TimeServiceError(
                f"Error getting time for timezone {timezone_name}: {str(e)}",
                original_error=e,
            ) from e

    async def get_timezone_info(self, timezone_name: str) -> TimeZoneInfo:
        """
        Get detailed timezone information.

        Args:
            timezone_name: Timezone name

        Returns:
            Timezone information

        Raises:
            TimeServiceError: When timezone is invalid
        """
        await self.ensure_connected()

        try:
            # Handle common timezone abbreviations
            if timezone_name.upper() in self._major_timezones:
                timezone_name = self._major_timezones[timezone_name.upper()]

            if timezone_name == "UTC":
                tz = timezone.utc
            else:
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
            raise TimeServiceError(
                f"Error getting timezone info for {timezone_name}: {str(e)}",
                original_error=e,
            ) from e

    async def convert_time(
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

        Raises:
            TimeServiceError: When conversion fails
        """
        await self.ensure_connected()

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
                    for fmt in [
                        self.default_datetime_format,
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                        "%Y-%m-%d",
                        "%H:%M:%S",
                        "%H:%M",
                    ]:
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
                if source_timezone == "UTC":
                    source_tz = timezone.utc
                else:
                    source_tz = ZoneInfo(source_timezone)
                source_time = parsed_time.replace(tzinfo=source_tz)
            else:
                source_time = parsed_time

            # Convert to target timezone
            if target_timezone == "UTC":
                target_tz = timezone.utc
            else:
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
            raise TimeServiceError(
                f"Error converting time from {source_timezone} to "
                f"{target_timezone}: {str(e)}",
                original_error=e,
            ) from e

    async def get_world_clock(
        self, cities: Optional[List[str]] = None
    ) -> List[WorldClock]:
        """
        Get world clock for major cities.

        Args:
            cities: List of city/timezone names (optional)

        Returns:
            List of world clock entries

        Raises:
            TimeServiceError: When world clock retrieval fails
        """
        await self.ensure_connected()

        try:
            # Default major cities from settings or hardcoded
            if cities is None:
                cities = getattr(
                    self.settings,
                    "time_service_default_cities",
                    [
                        "UTC",
                        "New York",
                        "Los Angeles",
                        "London",
                        "Paris",
                        "Tokyo",
                        "Sydney",
                        "Mumbai",
                    ],
                )

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

            # Add custom city mappings from settings if available
            custom_cities = getattr(self.settings, "time_service_custom_cities", {})
            if custom_cities:
                city_timezones.update(custom_cities)

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

                    if timezone_name == "UTC":
                        tz = timezone.utc
                    else:
                        tz = ZoneInfo(timezone_name)

                    current_time = datetime.now(tz)

                    # Format offset
                    offset = current_time.strftime("%z")
                    formatted_offset = (
                        f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"
                    )

                    world_clock.append(
                        WorldClock(
                            city=city,
                            timezone=timezone_name,
                            current_time=current_time,
                            local_date=current_time.strftime(self.default_date_format),
                            local_time=current_time.strftime(self.default_time_format),
                            utc_offset=formatted_offset,
                        )
                    )

                except Exception:
                    # Skip problematic cities but don't fail the entire request
                    continue

            return world_clock

        except Exception as e:
            raise TimeServiceError(
                f"Error getting world clock: {str(e)}", original_error=e
            ) from e

    async def get_time_until(
        self, target_time: Union[datetime, str], timezone_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate time remaining until a target time.

        Args:
            target_time: Target datetime or ISO string
            timezone_name: Timezone for calculation (None for default)

        Returns:
            Dictionary with time remaining information

        Raises:
            TimeServiceError: When calculation fails
        """
        await self.ensure_connected()

        try:
            # Parse target time
            if isinstance(target_time, str):
                try:
                    parsed_time = datetime.fromisoformat(
                        target_time.replace("Z", "+00:00")
                    )
                except ValueError:
                    parsed_time = datetime.strptime(
                        target_time, self.default_datetime_format
                    )
            else:
                parsed_time = target_time

            # Get current time in specified timezone
            current_time = await self.get_current_time(timezone_name)

            # Ensure both times have timezone info
            if parsed_time.tzinfo is None:
                if timezone_name:
                    if timezone_name == "UTC":
                        tz = timezone.utc
                    else:
                        tz = ZoneInfo(timezone_name)
                    parsed_time = parsed_time.replace(tzinfo=tz)
                else:
                    if self.default_timezone == "UTC":
                        parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                    else:
                        tz = ZoneInfo(self.default_timezone)
                        parsed_time = parsed_time.replace(tzinfo=tz)

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
            raise TimeServiceError(
                f"Error calculating time until {target_time}: {str(e)}",
                original_error=e,
            ) from e

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

    async def get_business_hours_status(
        self,
        timezone_name: str,
        business_start: Optional[str] = None,
        business_end: Optional[str] = None,
        weekdays_only: Optional[bool] = None,
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

        Raises:
            TimeServiceError: When business hours check fails
        """
        await self.ensure_connected()

        try:
            # Use defaults from settings if not provided
            if business_start is None:
                business_start = self.default_business_start
            if business_end is None:
                business_end = self.default_business_end
            if weekdays_only is None:
                weekdays_only = self.weekdays_only

            current_time = await self.get_current_time(timezone_name)
            current_hour_min = current_time.strftime("%H:%M")
            current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday

            is_business_day = not weekdays_only or current_weekday < 5  # Monday-Friday
            is_business_hours = business_start <= current_hour_min <= business_end

            return {
                "is_business_hours": is_business_day and is_business_hours,
                "is_business_day": is_business_day,
                "current_time": current_hour_min,
                "current_day": current_time.strftime("%A"),
                "business_start": business_start,
                "business_end": business_end,
                "timezone": timezone_name,
                "weekdays_only": weekdays_only,
            }

        except Exception as e:
            raise TimeServiceError(
                f"Error checking business hours for {timezone_name}: {str(e)}",
                original_error=e,
            ) from e

    async def get_available_timezones(self, region: Optional[str] = None) -> List[str]:
        """
        Get list of available timezone names.

        Args:
            region: Optional region filter (e.g., 'America', 'Europe')

        Returns:
            List of timezone names

        Raises:
            TimeServiceError: When timezone list retrieval fails
        """
        await self.ensure_connected()

        try:
            import zoneinfo

            timezones = list(zoneinfo.available_timezones())

            if region:
                timezones = [tz for tz in timezones if tz.startswith(region)]

            return sorted(timezones)

        except Exception:
            # Fallback to major timezones
            return list(self._major_timezones.values())

    async def format_datetime(
        self,
        dt: datetime,
        format_string: Optional[str] = None,
        timezone_name: Optional[str] = None,
    ) -> str:
        """
        Format datetime according to settings or custom format.

        Args:
            dt: Datetime to format
            format_string: Custom format string (optional)
            timezone_name: Convert to timezone before formatting (optional)

        Returns:
            Formatted datetime string

        Raises:
            TimeServiceError: When formatting fails
        """
        await self.ensure_connected()

        try:
            target_dt = dt

            # Convert timezone if requested
            if timezone_name:
                if timezone_name == "UTC":
                    target_tz = timezone.utc
                else:
                    target_tz = ZoneInfo(timezone_name)
                target_dt = dt.astimezone(target_tz)

            # Use custom format or default from settings
            if format_string is None:
                format_string = self.default_datetime_format

            return target_dt.strftime(format_string)

        except Exception as e:
            raise TimeServiceError(
                f"Error formatting datetime: {str(e)}", original_error=e
            ) from e

    async def health_check(self) -> bool:
        """
        Perform a health check to verify the service is working.

        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            await self.ensure_connected()

            # Test basic functionality
            current_time = await self.get_current_time()
            timezone_info = await self.get_timezone_info("UTC")

            return (
                current_time is not None
                and timezone_info is not None
                and timezone_info.name == "UTC"
            )
        except Exception:
            return False

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.disconnect()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global service instance
_time_service: Optional[TimeService] = None


async def get_time_service() -> TimeService:
    """
    Get the global time service instance.

    Returns:
        TimeService instance
    """
    global _time_service

    if _time_service is None:
        _time_service = TimeService()
        await _time_service.connect()

    return _time_service


async def close_time_service() -> None:
    """Close the global time service instance."""
    global _time_service

    if _time_service:
        await _time_service.close()
        _time_service = None


# Convenience functions
async def get_current_time_utc() -> datetime:
    """Get current UTC time."""
    service = await get_time_service()
    return await service.get_current_time("UTC")


async def convert_timezone(time_str: str, from_tz: str, to_tz: str) -> TimeConversion:
    """Quick timezone conversion."""
    service = await get_time_service()
    return await service.convert_time(time_str, from_tz, to_tz)


async def get_world_time() -> List[WorldClock]:
    """Get world clock for major cities."""
    service = await get_time_service()
    return await service.get_world_clock()


__all__ = [
    "TimeService",
    "TimeServiceError",
    "TimeZoneInfo",
    "TimeConversion",
    "WorldClock",
    "get_time_service",
    "close_time_service",
    "get_current_time_utc",
    "convert_timezone",
    "get_world_time",
]
