"""Time Service using Python datetime functionality with TripSage Core integration.

This service provides timezone-aware time operations, eliminating the need for
external MCP services for basic time and timezone calculations.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreExternalAPIError as CoreAPIError,
    CoreServiceError,
)
from tripsage_core.services.external_apis.base_service import (
    AsyncServiceLifecycle,
    AsyncServiceProvider,
)


class TimeServiceError(CoreAPIError):
    """Exception raised for time service errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        """Initialize TimeServiceError."""
        super().__init__(
            message=message,
            code="TIME_SERVICE_ERROR",
            api_service="TimeService",
            details={
                "additional_context": {
                    "original_error": str(original_error) if original_error else None
                }
            },
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


@dataclass(frozen=True)
class TimeServiceConfig:
    """Immutable configuration for the time service."""

    default_timezone: str
    default_date_format: str
    default_time_format: str
    default_datetime_format: str
    default_business_start: str
    default_business_end: str
    weekdays_only: bool
    custom_timezones: dict[str, str]


class TimeService(AsyncServiceLifecycle):
    """Service for timezone and time operations with Core integration."""

    def __init__(self, settings: Settings | None = None):
        """Initialize Time service.

        Args:
            settings: Core application settings
        """
        self.settings = settings or get_settings()
        self._connected = False

        settings_obj = self.settings
        self.config = TimeServiceConfig(
            default_timezone=getattr(
                settings_obj, "time_service_default_timezone", "UTC"
            ),
            default_date_format=getattr(
                settings_obj, "time_service_date_format", "%Y-%m-%d"
            ),
            default_time_format=getattr(
                settings_obj, "time_service_time_format", "%H:%M:%S"
            ),
            default_datetime_format=getattr(
                settings_obj, "time_service_datetime_format", "%Y-%m-%d %H:%M:%S"
            ),
            default_business_start=getattr(
                settings_obj, "time_service_business_start", "09:00"
            ),
            default_business_end=getattr(
                settings_obj, "time_service_business_end", "17:00"
            ),
            weekdays_only=getattr(settings_obj, "time_service_weekdays_only", True),
            custom_timezones=getattr(settings_obj, "time_service_custom_timezones", {})
            or {},
        )

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
        if self.config.custom_timezones:
            self._major_timezones.update(self.config.custom_timezones)

        self._recoverable_errors = (
            CoreServiceError,
            TimeServiceError,
            ZoneInfoNotFoundError,
            ValueError,
            OSError,
            RuntimeError,
            ConnectionError,
        )

    async def connect(self) -> None:
        """Initialize the time service."""
        if self._connected:
            return

        try:
            # Test timezone functionality
            _ = datetime.now(UTC)
            self._connected = True

        except self._recoverable_errors as error:
            raise CoreServiceError(
                message=f"Failed to connect time service: {error!s}",
                code="CONNECTION_FAILED",
                service="TimeService",
                details={"error": str(error)},
            ) from error

    async def disconnect(self) -> None:
        """Clean up resources."""
        self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure service is connected."""
        if not self._connected:
            await self.connect()

    async def get_current_time(self, timezone_name: str | None = None) -> datetime:
        """Get current time in specified timezone.

        Args:
            timezone_name: Timezone name (e.g., 'America/New_York') or None for default

        Returns:
            Current datetime in specified timezone

        Raises:
            TimeServiceError: When timezone is invalid
        """
        await self.ensure_connected()

        resolved_timezone = timezone_name or self.config.default_timezone
        if resolved_timezone is None:
            raise TimeServiceError("No timezone configured for current time lookup.")

        try:
            # Handle common timezone abbreviations
            timezone_key = resolved_timezone.upper()
            if timezone_key in self._major_timezones:
                resolved_timezone = self._major_timezones[timezone_key]

            if resolved_timezone == "UTC":
                return datetime.now(UTC)

            tz = ZoneInfo(resolved_timezone)
            return datetime.now(tz)

        except self._recoverable_errors as error:
            raise TimeServiceError(
                f"Error getting time for timezone {resolved_timezone}: {error!s}",
                original_error=error,
            ) from error

    async def get_timezone_info(self, timezone_name: str) -> TimeZoneInfo:
        """Get detailed timezone information.

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
            timezone_key = timezone_name.upper()
            if timezone_key in self._major_timezones:
                timezone_name = self._major_timezones[timezone_key]

            tz = UTC if timezone_name == "UTC" else ZoneInfo(timezone_name)

            current_time = datetime.now(tz)

            # Get timezone offset
            offset = current_time.strftime("%z")
            formatted_offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"

            # Get timezone abbreviation
            abbreviation = current_time.strftime("%Z")

            # Check if DST is active
            dst_delta = current_time.dst()
            dst_active = bool(dst_delta is not None and dst_delta.total_seconds() > 0)

            return TimeZoneInfo(
                name=timezone_name,
                abbreviation=abbreviation,
                offset=formatted_offset,
                dst_active=dst_active,
                current_time=current_time,
            )

        except self._recoverable_errors as error:
            raise TimeServiceError(
                f"Error getting timezone info for {timezone_name}: {error!s}",
                original_error=error,
            ) from error

    async def convert_time(
        self,
        time_to_convert: datetime | str,
        source_timezone: str,
        target_timezone: str,
    ) -> TimeConversion:
        """Convert time between timezones.

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
                    parsed_time = datetime.fromisoformat(time_to_convert)
                except ValueError as exc:
                    # Try other common formats
                    for fmt in [
                        self.config.default_datetime_format,
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
                        ) from exc
            else:
                parsed_time = time_to_convert

            # Handle timezone abbreviations
            source_key = source_timezone.upper()
            target_key = target_timezone.upper()
            if source_key in self._major_timezones:
                source_timezone = self._major_timezones[source_key]
            if target_key in self._major_timezones:
                target_timezone = self._major_timezones[target_key]

            # Convert to source timezone if naive
            if parsed_time.tzinfo is None:
                if source_timezone == "UTC":
                    source_tz = UTC
                else:
                    source_tz = ZoneInfo(source_timezone)
                source_time = parsed_time.replace(tzinfo=source_tz)
            else:
                source_time = parsed_time

            # Convert to target timezone
            target_tz = UTC if target_timezone == "UTC" else ZoneInfo(target_timezone)
            target_time = source_time.astimezone(target_tz)

            # Calculate time difference
            source_offset = source_time.utcoffset()
            target_offset = target_time.utcoffset()
            if source_offset is None or target_offset is None:
                raise TimeServiceError(
                    "Unable to determine timezone offsets for conversion."
                )
            time_diff = target_offset - source_offset
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

        except self._recoverable_errors as error:
            raise TimeServiceError(
                f"Error converting time from {source_timezone} to {target_timezone}: "
                f"{error!s}",
                original_error=error,
            ) from error

    async def get_world_clock(
        self, cities: list[str] | None = None
    ) -> list[WorldClock]:
        """Get world clock for major cities.

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

            for city in cities:  # pyright: ignore[reportOptionalIterable]
                try:
                    # Get timezone for city
                    display_city = city
                    if city in city_timezones:
                        timezone_name = city_timezones[city]
                    elif city.upper() in self._major_timezones:
                        timezone_name = self._major_timezones[city.upper()]
                        display_city = city.upper()  # Use abbreviation as city name
                    else:
                        # Assume it's already a timezone name
                        timezone_name = city

                    tz = UTC if timezone_name == "UTC" else ZoneInfo(timezone_name)

                    current_time = datetime.now(tz)

                    # Format offset
                    offset = current_time.strftime("%z")
                    formatted_offset = (
                        f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"
                    )

                    world_clock.append(
                        WorldClock(
                            city=display_city,
                            timezone=timezone_name,
                            current_time=current_time,
                            local_date=current_time.strftime(
                                self.config.default_date_format
                            ),
                            local_time=current_time.strftime(
                                self.config.default_time_format
                            ),
                            utc_offset=formatted_offset,
                        )
                    )

                except self._recoverable_errors:
                    # Skip problematic cities but don't fail the entire request
                    continue

            return world_clock

        except self._recoverable_errors as error:
            raise TimeServiceError(
                f"Error getting world clock: {error!s}", original_error=error
            ) from error

    async def get_time_until(
        self, target_time: datetime | str, timezone_name: str | None = None
    ) -> dict[str, Any]:
        """Calculate time remaining until a target time.

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
                    parsed_time = datetime.fromisoformat(target_time)
                except ValueError:
                    parsed_time = datetime.strptime(
                        target_time, self.config.default_datetime_format
                    )
            else:
                parsed_time = target_time

            # Get current time in specified timezone
            current_time = await self.get_current_time(timezone_name)

            # Ensure both times have timezone info
            if parsed_time.tzinfo is None:
                if timezone_name:
                    tz = UTC if timezone_name == "UTC" else ZoneInfo(timezone_name)
                    parsed_time = parsed_time.replace(tzinfo=tz)
                elif self.config.default_timezone == "UTC":
                    parsed_time = parsed_time.replace(tzinfo=UTC)
                else:
                    tz = ZoneInfo(self.config.default_timezone)
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

            return {
                "status": "future",
                "message": "Time remaining until target",
                "time_remaining": self._format_timedelta(time_diff),
                "total_seconds": time_diff.total_seconds(),
            }

        except self._recoverable_errors as error:
            raise TimeServiceError(
                f"Error calculating time until {target_time}: {error!s}",
                original_error=error,
            ) from error

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
        business_start: str | None = None,
        business_end: str | None = None,
        weekdays_only: bool | None = None,
    ) -> dict[str, Any]:
        """Check if current time is within business hours.

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
                business_start = self.config.default_business_start
            if business_end is None:
                business_end = self.config.default_business_end
            if weekdays_only is None:
                weekdays_only = self.config.weekdays_only

            if business_start is None or business_end is None:
                raise TimeServiceError("Business hours configuration is incomplete.")

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

        except self._recoverable_errors as error:
            raise TimeServiceError(
                f"Error checking business hours for {timezone_name}: {error!s}",
                original_error=error,
            ) from error

    async def get_available_timezones(self, region: str | None = None) -> list[str]:
        """Get list of available timezone names.

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

        except ValueError:
            # Fallback to major timezones
            return list(self._major_timezones.values())

    async def format_datetime(
        self,
        dt: datetime,
        format_string: str | None = None,
        timezone_name: str | None = None,
    ) -> str:
        """Format datetime according to settings or custom format.

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
                target_tz = UTC if timezone_name == "UTC" else ZoneInfo(timezone_name)
                target_dt = dt.astimezone(target_tz)

            # Use custom format or default from settings
            format_to_use = format_string or self.config.default_datetime_format

            return target_dt.strftime(format_to_use)

        except self._recoverable_errors as error:
            raise TimeServiceError(
                f"Error formatting datetime: {error!s}", original_error=error
            ) from error

    async def health_check(self) -> bool:
        """Perform a health check to verify the service is working.

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
        except CoreServiceError:
            return False


_time_service_provider = AsyncServiceProvider(
    factory=TimeService,
    initializer=lambda service: service.connect(),
    finalizer=lambda service: service.close(),
)


async def get_time_service() -> TimeService:
    """Return the shared time service instance."""
    return await _time_service_provider.get()


async def close_time_service() -> None:
    """Dispose of the shared time service instance."""
    await _time_service_provider.close()


# Convenience functions
async def get_current_time_utc() -> datetime:
    """Get current UTC time."""
    service = await get_time_service()
    return await service.get_current_time("UTC")


async def convert_timezone(time_str: str, from_tz: str, to_tz: str) -> TimeConversion:
    """Quick timezone conversion."""
    service = await get_time_service()
    return await service.convert_time(time_str, from_tz, to_tz)


async def get_world_time() -> list[WorldClock]:
    """Get world clock for major cities."""
    service = await get_time_service()
    return await service.get_world_clock()


__all__ = [
    "TimeConversion",
    "TimeService",
    "TimeServiceError",
    "TimeZoneInfo",
    "WorldClock",
    "close_time_service",
    "convert_timezone",
    "get_current_time_utc",
    "get_time_service",
    "get_world_time",
]
