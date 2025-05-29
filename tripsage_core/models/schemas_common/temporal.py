"""
Temporal models and schemas for TripSage AI.

This module contains date, time, and duration-related models used
across the application for consistent time handling.
"""

from datetime import date, datetime, time, timedelta
from typing import Optional

from pydantic import Field, field_validator

from tripsage_core.models.base import TripSageModel


class DateRange(TripSageModel):
    """Date range with validation."""

    start_date: date = Field(description="Start date")
    end_date: date = Field(description="End date")

    @field_validator("end_date")
    @classmethod
    def validate_end_after_start(cls, v: date, info) -> date:
        """Validate that end date is after start date."""
        if "start_date" in info.data:
            start_date = info.data["start_date"]
            if v < start_date:
                raise ValueError("End date must be after start date")
        return v

    def duration_days(self) -> int:
        """Calculate the duration in days."""
        return (self.end_date - self.start_date).days

    def contains(self, check_date: date) -> bool:
        """Check if a date falls within this range."""
        return self.start_date <= check_date <= self.end_date

    def overlaps(self, other: "DateRange") -> bool:
        """Check if this range overlaps with another range."""
        return not (
            self.end_date < other.start_date or other.end_date < self.start_date
        )


class TimeRange(TripSageModel):
    """Time range within a day."""

    start_time: time = Field(description="Start time")
    end_time: time = Field(description="End time")

    @field_validator("end_time")
    @classmethod
    def validate_end_after_start(cls, v: time, info) -> time:
        """Validate that end time is after start time (same day)."""
        if "start_time" in info.data:
            start_time = info.data["start_time"]
            if v <= start_time:
                raise ValueError("End time must be after start time")
        return v

    def duration_minutes(self) -> int:
        """Calculate the duration in minutes."""
        start_dt = datetime.combine(date.today(), self.start_time)
        end_dt = datetime.combine(date.today(), self.end_time)
        return int((end_dt - start_dt).total_seconds() / 60)

    def contains(self, check_time: time) -> bool:
        """Check if a time falls within this range."""
        return self.start_time <= check_time <= self.end_time


class Duration(TripSageModel):
    """Duration with multiple representations."""

    days: int = Field(0, ge=0, description="Number of days")
    hours: int = Field(0, ge=0, lt=24, description="Number of hours")
    minutes: int = Field(0, ge=0, lt=60, description="Number of minutes")

    @field_validator("hours")
    @classmethod
    def validate_hours(cls, v: int) -> int:
        """Validate hours are within 0-23."""
        if not 0 <= v < 24:
            raise ValueError("Hours must be between 0 and 23")
        return v

    @field_validator("minutes")
    @classmethod
    def validate_minutes(cls, v: int) -> int:
        """Validate minutes are within 0-59."""
        if not 0 <= v < 60:
            raise ValueError("Minutes must be between 0 and 59")
        return v

    def total_minutes(self) -> int:
        """Convert duration to total minutes."""
        return self.days * 24 * 60 + self.hours * 60 + self.minutes

    def total_hours(self) -> float:
        """Convert duration to total hours."""
        return self.total_minutes() / 60

    def to_timedelta(self) -> timedelta:
        """Convert to Python timedelta object."""
        return timedelta(days=self.days, hours=self.hours, minutes=self.minutes)

    @classmethod
    def from_minutes(cls, total_minutes: int) -> "Duration":
        """Create Duration from total minutes."""
        days = total_minutes // (24 * 60)
        remaining_minutes = total_minutes % (24 * 60)
        hours = remaining_minutes // 60
        minutes = remaining_minutes % 60

        return cls(days=days, hours=hours, minutes=minutes)

    @classmethod
    def from_timedelta(cls, td: timedelta) -> "Duration":
        """Create Duration from timedelta object."""
        total_seconds = int(td.total_seconds())
        days = total_seconds // (24 * 3600)
        remaining_seconds = total_seconds % (24 * 3600)
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60

        return cls(days=days, hours=hours, minutes=minutes)


class DateTimeRange(TripSageModel):
    """DateTime range with timezone awareness."""

    start_datetime: datetime = Field(description="Start datetime")
    end_datetime: datetime = Field(description="End datetime")
    timezone: Optional[str] = Field(None, description="IANA timezone identifier")

    @field_validator("end_datetime")
    @classmethod
    def validate_end_after_start(cls, v: datetime, info) -> datetime:
        """Validate that end datetime is after start datetime."""
        if "start_datetime" in info.data:
            start_datetime = info.data["start_datetime"]
            if v <= start_datetime:
                raise ValueError("End datetime must be after start datetime")
        return v

    def duration(self) -> timedelta:
        """Calculate the duration as a timedelta."""
        return self.end_datetime - self.start_datetime

    def contains(self, check_datetime: datetime) -> bool:
        """Check if a datetime falls within this range."""
        return self.start_datetime <= check_datetime <= self.end_datetime

    def overlaps(self, other: "DateTimeRange") -> bool:
        """Check if this range overlaps with another range."""
        return not (
            self.end_datetime <= other.start_datetime
            or other.end_datetime <= self.start_datetime
        )


class RecurrenceRule(TripSageModel):
    """Recurrence rule for repeating events."""

    frequency: str = Field(description="Frequency (DAILY, WEEKLY, MONTHLY, YEARLY)")
    interval: int = Field(1, ge=1, description="Interval between occurrences")
    count: Optional[int] = Field(None, ge=1, description="Number of occurrences")
    until: Optional[date] = Field(None, description="End date for recurrence")
    by_day: Optional[list[str]] = Field(
        None, description="Days of week (MO, TU, WE, etc.)"
    )
    by_month_day: Optional[list[int]] = Field(None, description="Days of month (1-31)")
    by_month: Optional[list[int]] = Field(None, description="Months (1-12)")

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        """Validate frequency is a valid option."""
        valid_frequencies = {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}
        if v.upper() not in valid_frequencies:
            raise ValueError(
                f"Frequency must be one of: {', '.join(valid_frequencies)}"
            )
        return v.upper()

    @field_validator("by_day")
    @classmethod
    def validate_by_day(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate day abbreviations."""
        if v is None:
            return v

        valid_days = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
        for day in v:
            if day.upper() not in valid_days:
                raise ValueError(f"Invalid day abbreviation: {day}")

        return [day.upper() for day in v]

    @field_validator("by_month_day")
    @classmethod
    def validate_by_month_day(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        """Validate month days are valid."""
        if v is None:
            return v

        for day in v:
            if not 1 <= day <= 31:
                raise ValueError(f"Month day must be between 1 and 31: {day}")

        return v

    @field_validator("by_month")
    @classmethod
    def validate_by_month(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        """Validate months are valid."""
        if v is None:
            return v

        for month in v:
            if not 1 <= month <= 12:
                raise ValueError(f"Month must be between 1 and 12: {month}")

        return v


class BusinessHours(TripSageModel):
    """Business hours for a location or service."""

    monday: Optional[TimeRange] = Field(None, description="Monday hours")
    tuesday: Optional[TimeRange] = Field(None, description="Tuesday hours")
    wednesday: Optional[TimeRange] = Field(None, description="Wednesday hours")
    thursday: Optional[TimeRange] = Field(None, description="Thursday hours")
    friday: Optional[TimeRange] = Field(None, description="Friday hours")
    saturday: Optional[TimeRange] = Field(None, description="Saturday hours")
    sunday: Optional[TimeRange] = Field(None, description="Sunday hours")
    timezone: Optional[str] = Field(None, description="IANA timezone identifier")

    def is_open_at(self, check_datetime: datetime) -> bool:
        """Check if open at a specific datetime."""
        weekday = check_datetime.weekday()  # 0 = Monday
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]

        if weekday >= len(day_names):
            return False

        day_hours = getattr(self, day_names[weekday])
        if day_hours is None:
            return False

        return day_hours.contains(check_datetime.time())


class Availability(TripSageModel):
    """Availability information for a resource."""

    available: bool = Field(description="Whether the resource is available")
    from_datetime: Optional[datetime] = Field(
        None, description="Available from this datetime"
    )
    to_datetime: Optional[datetime] = Field(
        None, description="Available until this datetime"
    )
    capacity: Optional[int] = Field(None, ge=0, description="Available capacity")
    restrictions: Optional[list[str]] = Field(
        None, description="Availability restrictions"
    )

    @field_validator("to_datetime")
    @classmethod
    def validate_to_after_from(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate that to_datetime is after from_datetime."""
        if v is None:
            return v

        if "from_datetime" in info.data:
            from_datetime = info.data["from_datetime"]
            if from_datetime and v <= from_datetime:
                raise ValueError("to_datetime must be after from_datetime")

        return v
