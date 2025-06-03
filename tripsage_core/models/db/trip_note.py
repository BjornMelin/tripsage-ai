"""TripNote model for TripSage.

This module provides the TripNote model for storing notes
and comments associated with trips.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageModel


class TripNote(TripSageModel):
    """TripNote model for TripSage.

    Attributes:
        id: Unique identifier for the note
        trip_id: Reference to the associated trip
        timestamp: When the note was created
        content: The note content
    """

    id: Optional[int] = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    timestamp: datetime = Field(..., description="When the note was created")
    content: str = Field(..., description="The note content")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate that content is not empty."""
        if not v or not v.strip():
            raise ValueError("ensure this value has at least 1 character")
        return v

    @property
    def is_recent(self) -> bool:
        """Check if the note was created recently (within 24 hours)."""
        from datetime import datetime as datetime_type
        from datetime import timedelta

        return datetime_type.now() - self.timestamp < timedelta(hours=24)

    @property
    def formatted_timestamp(self) -> str:
        """Get the formatted timestamp for display."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M")

    @property
    def content_snippet(self) -> str:
        """Get a snippet of the note content."""
        # Return the first 100 characters or the full content if it's shorter
        max_length = 100
        if len(self.content) <= max_length:
            return self.content
        # Account for the "..." when truncating
        return self.content[: max_length - 3] + "..."

    @property
    def summary(self) -> str:
        """Get a summary of the note content."""
        # Return the first 50 characters or the full content if it's shorter
        max_length = 50
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."

    @property
    def word_count(self) -> int:
        """Get the word count of the note content."""
        return len(self.content.split())

    def update_content(self, new_content: str) -> bool:
        """Update the note content with validation.

        Args:
            new_content: The new content to set

        Returns:
            True if the content was updated, False if invalid
        """
        if not new_content or not new_content.strip():
            return False

        self.content = new_content
        return True
