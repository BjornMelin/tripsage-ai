"""
Core memory and knowledge graph domain models for TripSage.

This module contains the core business domain models for memory, knowledge graph,
and session management entities. These models represent the essential memory
data structures independent of storage implementation or API specifics.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageDomainModel


class Entity(TripSageDomainModel):
    """Core knowledge graph entity business model.

    This represents a canonical entity in the TripSage knowledge graph system.
    Entities are the fundamental building blocks of the knowledge representation.
    """

    name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Entity type")
    observations: List[str] = Field([], description="Observations about the entity")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Additional domain-specific fields for enhanced functionality
    aliases: Optional[List[str]] = Field(
        [], description="Alternative names for the entity"
    )
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score for entity accuracy"
    )
    source: Optional[str] = Field(None, description="Source of the entity information")
    tags: Optional[List[str]] = Field([], description="Tags for categorization")
    metadata: Optional[Dict[str, Any]] = Field(
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
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    # Additional domain-specific fields for enhanced functionality
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score for relation accuracy"
    )
    weight: Optional[float] = Field(
        None, description="Relation weight for graph algorithms"
    )
    properties: Optional[Dict[str, Any]] = Field(
        {}, description="Additional properties of the relation"
    )
    source: Optional[str] = Field(
        None, description="Source of the relation information"
    )
    bidirectional: bool = Field(
        False, description="Whether the relation is bidirectional"
    )


class TravelMemory(TripSageDomainModel):
    """Core travel memory business entity.

    This represents canonical travel-specific memory information that enhances
    the user's travel planning and experience.
    """

    id: Optional[str] = Field(None, description="Memory ID")
    user_id: str = Field(..., description="User ID")
    memory_type: str = Field(..., description="Type of travel memory")
    content: str = Field(..., description="Memory content")

    # Travel-specific fields
    travel_context: Optional[Dict[str, Any]] = Field(
        {}, description="Travel-related context (dates, locations, etc.)"
    )
    destinations: Optional[List[str]] = Field([], description="Associated destinations")
    travel_dates: Optional[Dict[str, str]] = Field(
        {}, description="Associated travel dates"
    )
    preferences: Optional[Dict[str, Any]] = Field(
        {}, description="User preferences extracted from memory"
    )

    # Standard memory fields
    importance_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Importance score for memory ranking"
    )
    tags: Optional[List[str]] = Field([], description="Memory tags")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")


class SessionMemory(TripSageDomainModel):
    """Core session memory business entity.

    This represents canonical session-specific memory for agent conversations
    and user interactions.
    """

    user_id: Optional[str] = Field(None, description="User ID")
    session_id: str = Field(..., description="Session ID")
    memory_type: str = Field(..., description="Memory type")
    content: Dict[str, Any] = Field(..., description="Memory content")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")

    # Enhanced session memory fields
    conversation_context: Optional[Dict[str, Any]] = Field(
        {}, description="Conversation context and history"
    )
    agent_state: Optional[Dict[str, Any]] = Field(
        {}, description="Agent state information"
    )
    user_preferences: Optional[Dict[str, Any]] = Field(
        {}, description="Session-specific user preferences"
    )
    interaction_count: int = Field(0, description="Number of interactions in session")
    last_activity: Optional[datetime] = Field(
        None, description="Last activity timestamp"
    )
