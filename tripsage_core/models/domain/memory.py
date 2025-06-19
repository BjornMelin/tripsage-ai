"""
Core memory and knowledge graph domain models for TripSage.

This module contains the core business domain models for memory, knowledge graph,
and session management entities. These models represent the essential memory
data structures independent of storage implementation or API specifics.
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageDomainModel


class Entity(TripSageDomainModel):
    """Core knowledge graph entity business model.

    This represents a canonical entity in the TripSage knowledge graph system.
    Entities are the fundamental building blocks of the knowledge representation.
    """

    name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Entity type")
    observations: list[str] = Field([], description="Observations about the entity")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    # Additional domain-specific fields for enhanced functionality
    aliases: list[str] | None = Field(
        [], description="Alternative names for the entity"
    )
    confidence_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Confidence score for entity accuracy"
    )
    source: str | None = Field(None, description="Source of the entity information")
    tags: list[str] | None = Field([], description="Tags for categorization")
    metadata: dict[str, Any] | None = Field(
        {}, description="Additional metadata about the entity"
    )


class Relation(TripSageDomainModel):
    """Core knowledge graph relation business model.

    This represents a canonical relation between entities in the TripSage
    knowledge graph system.
    """

    from_entity: str = Field(..., description="Source entity name")
    to_entity: str = Field(..., description="Target entity name")
    relation_type: str = Field(..., description="Relation type")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    # Additional domain-specific fields for enhanced functionality
    confidence_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Confidence score for relation accuracy"
    )
    weight: float | None = Field(
        None, description="Relation weight for graph algorithms"
    )
    properties: dict[str, Any] | None = Field(
        {}, description="Additional properties of the relation"
    )
    source: str | None = Field(None, description="Source of the relation information")
    bidirectional: bool = Field(
        False, description="Whether the relation is bidirectional"
    )


class TravelMemory(TripSageDomainModel):
    """Core travel memory business entity.

    This represents canonical travel-specific memory information that enhances
    the user's travel planning and experience.
    """

    id: str | None = Field(None, description="Memory ID")
    user_id: str = Field(..., description="User ID")
    memory_type: str = Field(..., description="Type of travel memory")
    content: str = Field(..., description="Memory content")

    # Travel-specific fields
    travel_context: dict[str, Any] | None = Field(
        {}, description="Travel-related context (dates, locations, etc.)"
    )
    destinations: list[str] | None = Field([], description="Associated destinations")
    travel_dates: dict[str, str] | None = Field(
        {}, description="Associated travel dates"
    )
    preferences: dict[str, Any] | None = Field(
        {}, description="User preferences extracted from memory"
    )

    # Standard memory fields
    importance_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Importance score for memory ranking"
    )
    tags: list[str] | None = Field([], description="Memory tags")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")


class SessionMemory(TripSageDomainModel):
    """Core session memory business entity.

    This represents canonical session-specific memory for agent conversations
    and user interactions.
    """

    user_id: str | None = Field(None, description="User ID")
    session_id: str = Field(..., description="Session ID")
    memory_type: str = Field(..., description="Memory type")
    content: dict[str, Any] = Field(..., description="Memory content")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    expires_at: datetime | None = Field(None, description="Expiration timestamp")

    # Enhanced session memory fields
    conversation_context: dict[str, Any] | None = Field(
        {}, description="Conversation context and history"
    )
    agent_state: dict[str, Any] | None = Field(
        {}, description="Agent state information"
    )
    user_preferences: dict[str, Any] | None = Field(
        {}, description="Session-specific user preferences"
    )
    interaction_count: int = Field(0, description="Number of interactions in session")
    last_activity: datetime | None = Field(None, description="Last activity timestamp")
