"""Utilities for booking status transitions.

This module provides shared logic for validating booking status transitions
across different booking types (accommodations, flights, transportation, etc.)
to avoid code duplication.
"""

from enum import Enum
from typing import TypeVar

from tripsage_core.models.db.accommodation import BookingStatus


T = TypeVar("T", bound=Enum)


def validate_booking_status_transition(
    current_status: T, new_status: T, valid_transitions: dict[T, list[T]]
) -> bool:
    """Validate if a booking status transition is allowed.

    Args:
        current_status: The current booking status
        new_status: The new status to transition to
        valid_transitions: Dictionary mapping current status to list of allowed
            next statuses

    Returns:
        True if transition is valid, False otherwise
    """
    allowed_next_statuses = valid_transitions.get(current_status, [])
    return new_status in allowed_next_statuses


def get_standard_booking_transitions() -> dict[BookingStatus, list[BookingStatus]]:
    """Get standard booking status transition rules.

    Returns:
        Dictionary with standard transition rules that can be used with
        validate_booking_status_transition
    """
    return {
        BookingStatus.VIEWED: [
            BookingStatus.SAVED,
            BookingStatus.BOOKED,
            BookingStatus.CANCELLED,
        ],
        BookingStatus.SAVED: [
            BookingStatus.BOOKED,
            BookingStatus.CANCELLED,
            BookingStatus.VIEWED,
        ],
        BookingStatus.BOOKED: [BookingStatus.CANCELLED],
        BookingStatus.CANCELLED: [],  # Cannot change from cancelled
    }
