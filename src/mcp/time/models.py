"""
Pydantic models for Time MCP client.

This module defines the parameter and response models for the Time MCP Client,
providing proper validation and type safety.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseParams(BaseModel):
    """Base model for all parameter models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class BaseResponse(BaseModel):
    """Base model for all response models."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class GetCurrentTimeParams(BaseParams):
    """Parameters for the get_current_time method."""

    timezone: str = Field(
        ...,
        description="IANA timezone name (e.g., 'America/New_York', 'Europe/London')",
    )

    @model_validator(mode="after")
    def validate_timezone(self) -> "GetCurrentTimeParams":
        """Validate timezone format."""
        if not self.timezone or "/" not in self.timezone:
            raise ValueError(
                "Timezone must be a valid IANA timezone name (e.g., 'America/New_York')"
            )
        return self


class TimeResponse(BaseResponse):
    """Response model for current time information."""

    timezone: str = Field(..., description="The timezone name")
    current_time: str = Field(
        ..., description="The current time in the timezone (HH:MM:SS)"
    )
    current_date: str = Field(
        ..., description="The current date in the timezone (YYYY-MM-DD)"
    )
    utc_offset: str = Field(..., description="UTC offset in hours:minutes")
    is_dst: bool = Field(False, description="Whether daylight saving time is in effect")


class ConvertTimeParams(BaseParams):
    """Parameters for the convert_time method."""

    time: str = Field(..., description="Time to convert in 24-hour format (HH:MM)")
    source_timezone: str = Field(..., description="Source IANA timezone name")
    target_timezone: str = Field(..., description="Target IANA timezone name")

    @model_validator(mode="after")
    def validate_time_format(self) -> "ConvertTimeParams":
        """Validate time format."""
        if not self.time or ":" not in self.time:
            raise ValueError("Time must be in 24-hour format (HH:MM)")
        try:
            hours, minutes = map(int, self.time.split(":"))
            if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                raise ValueError("Invalid hours or minutes")
        except ValueError as e:
            raise ValueError("Time must be in 24-hour format (HH:MM)") from e
        return self

    @model_validator(mode="after")
    def validate_timezones(self) -> "ConvertTimeParams":
        """Validate timezone formats."""
        if not self.source_timezone or "/" not in self.source_timezone:
            raise ValueError(
                "Source timezone must be a valid IANA timezone name (e.g., "
                "'America/New_York')"
            )
        if not self.target_timezone or "/" not in self.target_timezone:
            raise ValueError(
                "Target timezone must be a valid IANA timezone name (e.g., "
                "'Europe/London')"
            )
        return self


class TimeInfo(BaseModel):
    """Model for time information in a particular timezone."""

    timezone: str = Field(..., description="The timezone name")
    datetime: str = Field(..., description="The date and time in ISO 8601 format")
    is_dst: bool = Field(False, description="Whether daylight saving time is in effect")

    model_config = ConfigDict(extra="allow")


class TimeConversionResponse(BaseResponse):
    """Response model for time conversion information."""

    source: TimeInfo = Field(..., description="Source time information")
    target: TimeInfo = Field(..., description="Target time information")
    time_difference: str = Field(
        ..., description="Time difference between the two timezones"
    )


class ItineraryItem(BaseModel):
    """Model for an itinerary item."""

    location: str = Field(..., description="The location name")
    activity: str = Field(..., description="The activity description")
    time: Optional[str] = Field(None, description="The time in format HH:MM")
    time_format: str = Field("UTC", description="The time format (UTC or local)")

    model_config = ConfigDict(extra="allow")


class TimezoneAwareItineraryItem(ItineraryItem):
    """Model for a timezone-aware itinerary item."""

    timezone: str = Field(..., description="The timezone of the location")
    local_time: str = Field(..., description="The local time at the location")
    utc_offset: str = Field(..., description="UTC offset of the location")


class FlightArrivalResponse(BaseResponse):
    """Response model for flight arrival calculation."""

    departure_time: str = Field(..., description="Departure time")
    departure_timezone: str = Field(..., description="Departure timezone")
    flight_duration: str = Field(..., description="Flight duration")
    arrival_time_departure_tz: str = Field(
        ..., description="Arrival time in departure timezone"
    )
    arrival_time_local: str = Field(..., description="Arrival time in local timezone")
    arrival_timezone: str = Field(..., description="Arrival timezone")
    time_difference: str = Field(..., description="Time difference between timezones")
    day_offset: int = Field(..., description="Number of days offset")
    error: Optional[str] = Field(None, description="Error message if any")


class MeetingTimeResponse(BaseResponse):
    """Response model for suitable meeting times."""

    first_timezone: str = Field(..., description="First timezone")
    first_time: str = Field(..., description="Time in first timezone")
    second_timezone: str = Field(..., description="Second timezone")
    second_time: str = Field(..., description="Time in second timezone")
    time_difference: str = Field(..., description="Time difference between timezones")
