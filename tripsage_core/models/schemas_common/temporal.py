"""
Temporal models and schemas for TripSage AI.

This module contains date, time, and duration-related models used
across the application for consistent time handling.
"""

from datetime import date, datetime, time, timedelta
from typing import Optional

from pydantic import Field, model_validator

from tripsage_core.models.base_core_model import TripSageModel


class DateRange(TripSageModel):
    """Date range with validation."""

    start_date: date = Field(description="Start date")
    end_date: date = Field(description="End date")

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRange":
        """Validate that end date is after start date."""
        if self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self

    def duration_days(self) -> int:
        """Calculate the duration in days."""
        return (self.end_date - self.start_date).days

    def contains(self, check_date: date) -> bool:
        """Check if a date falls within this range."""
        return self.start_date <= check_date <= self.end_date

    def overlaps(self, other: "DateRange") -> bool:
        """Check if this range overlaps with another range."""
        return not (self.end_date < other.start_date or other.end_date < self.start_date)


class TimeRange(TripSageModel):
    """Time range within a day."""

    start_time: time = Field(description="Start time")
    end_time: time = Field(description="End time")

    @model_validator(mode="after")
    def validate_time_range(self) -> "TimeRange":
        """Validate that end time is after start time (same day)."""
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")
        return self

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

    @model_validator(mode="after")
    def validate_datetime_range(self) -> "DateTimeRange":
        """Validate that end datetime is after start datetime."""
        if self.end_datetime <= self.start_datetime:
            raise ValueError("End datetime must be after start datetime")
        return self

    def duration(self) -> timedelta:
        """Calculate the duration as a timedelta."""
        return self.end_datetime - self.start_datetime

    def contains(self, check_datetime: datetime) -> bool:
        """Check if a datetime falls within this range."""
        return self.start_datetime <= check_datetime <= self.end_datetime

    def overlaps(self, other: "DateTimeRange") -> bool:
        """Check if this range overlaps with another range."""
        return not (self.end_datetime <= other.start_datetime or other.end_datetime <= self.start_datetime)


class RecurrenceRule(TripSageModel):
    """Recurrence rule for repeating events."""

    frequency: str = Field(description="Frequency (DAILY, WEEKLY, MONTHLY, YEARLY)")
    interval: int = Field(1, ge=1, description="Interval between occurrences")
    count: Optional[int] = Field(None, ge=1, description="Number of occurrences")
    until: Optional[date] = Field(None, description="End date for recurrence")
    by_day: Optional[list[str]] = Field(None, description="Days of week (MO, TU, WE, etc.)")
    by_month_day: Optional[list[int]] = Field(None, description="Days of month (1-31)")
    by_month: Optional[list[int]] = Field(None, description="Months (1-12)")

    @model_validator(mode="after")
    def validate_recurrence(self) -> "RecurrenceRule":
        """Validate recurrence rule fields."""
        # Validate frequency
        valid_frequencies = {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}
        if self.frequency.upper() not in valid_frequencies:
            raise ValueError(f"Frequency must be one of: {', '.join(valid_frequencies)}")
        self.frequency = self.frequency.upper()

        # Validate by_day
        if self.by_day:
            valid_days = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
            for i, day in enumerate(self.by_day):
                if day.upper() not in valid_days:
                    raise ValueError(f"Invalid day abbreviation: {day}")
                self.by_day[i] = day.upper()

        # Validate by_month_day
        if self.by_month_day:
            for day in self.by_month_day:
                if not 1 <= day <= 31:
                    raise ValueError(f"Month day must be between 1 and 31: {day}")

        # Validate by_month
        if self.by_month:
            for month in self.by_month:
                if not 1 <= month <= 12:
                    raise ValueError(f"Month must be between 1 and 12: {month}")

        return self


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
    from_datetime: Optional[datetime] = Field(None, description="Available from this datetime")
    to_datetime: Optional[datetime] = Field(None, description="Available until this datetime")
    capacity: Optional[int] = Field(None, ge=0, description="Available capacity")
    restrictions: Optional[list[str]] = Field(None, description="Availability restrictions")

    @model_validator(mode="after")
    def validate_availability_range(self) -> "Availability":
        """Validate that to_datetime is after from_datetime."""
        if self.from_datetime and self.to_datetime:
            if self.to_datetime <= self.from_datetime:
                raise ValueError("to_datetime must be after from_datetime")
        return self
