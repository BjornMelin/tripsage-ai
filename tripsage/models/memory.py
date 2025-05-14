"""
Memory model classes for TripSage.

This module provides the memory-related model classes for interaction with
the knowledge graph and session memory in the TripSage application.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from tripsage.models.base import TripSageModel
from tripsage.models.mcp import MCPRequestBase, MCPResponseBase


class Entity(TripSageModel):
    """An entity in the knowledge graph."""

    name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Entity type")
    observations: List[str] = Field([], description="Observations about the entity")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class Relation(TripSageModel):
    """A relation between entities in the knowledge graph."""

    from_entity: str = Field(..., description="Source entity name")
    to_entity: str = Field(..., description="Target entity name")
    relation_type: str = Field(..., description="Relation type")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class CreateEntitiesRequest(MCPRequestBase):
    """Request to create entities in the knowledge graph."""

    entities: List[Entity] = Field(..., description="Entities to create")


class CreateEntitiesResponse(MCPResponseBase):
    """Response from creating entities in the knowledge graph."""

    created_count: int = Field(0, description="Number of entities created")
    entities: List[Entity] = Field([], description="Created entities")


class CreateRelationsRequest(MCPRequestBase):
    """Request to create relations in the knowledge graph."""

    relations: List[Relation] = Field(..., description="Relations to create")


class CreateRelationsResponse(MCPResponseBase):
    """Response from creating relations in the knowledge graph."""

    created_count: int = Field(0, description="Number of relations created")
    relations: List[Relation] = Field([], description="Created relations")


class AddObservationsRequest(MCPRequestBase):
    """Request to add observations to entities."""

    observations: List[Dict[str, Any]] = Field(..., description="Observations to add")


class AddObservationsResponse(MCPResponseBase):
    """Response from adding observations to entities."""

    updated_count: int = Field(0, description="Number of entities updated")
    entities: List[str] = Field([], description="Updated entity names")


class SearchNodesRequest(MCPRequestBase):
    """Request to search for nodes in the knowledge graph."""

    query: str = Field(..., description="Search query")
    entity_types: Optional[List[str]] = Field(
        None, description="Entity types to filter by"
    )
    limit: int = Field(10, description="Maximum number of results to return")


class SearchNodesResponse(MCPResponseBase):
    """Response from searching for nodes in the knowledge graph."""

    matches: List[Entity] = Field([], description="Matching entities")
    match_count: int = Field(0, description="Number of matching entities")


class OpenNodesRequest(MCPRequestBase):
    """Request to open specific nodes in the knowledge graph."""

    names: List[str] = Field(..., description="Entity names to open")


class OpenNodesResponse(MCPResponseBase):
    """Response from opening specific nodes in the knowledge graph."""

    entities: List[Entity] = Field([], description="Opened entities")
    found_count: int = Field(0, description="Number of entities found")


class ReadGraphRequest(MCPRequestBase):
    """Request to read the entire knowledge graph."""

    limit: Optional[int] = Field(
        None, description="Maximum number of results to return"
    )
    include_observations: bool = Field(
        True, description="Whether to include observations"
    )


class ReadGraphResponse(MCPResponseBase):
    """Response from reading the entire knowledge graph."""

    entities: List[Entity] = Field([], description="All entities")
    relations: List[Relation] = Field([], description="All relations")
    entity_count: int = Field(0, description="Number of entities")
    relation_count: int = Field(0, description="Number of relations")


class SessionMemory(TripSageModel):
    """Session memory for an agent."""

    user_id: Optional[str] = Field(None, description="User ID")
    session_id: str = Field(..., description="Session ID")
    memory_type: str = Field(..., description="Memory type")
    content: Dict[str, Any] = Field(..., description="Memory content")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")


class StoreSessionMemoryRequest(MCPRequestBase):
    """Request to store session memory."""

    user_id: Optional[str] = Field(None, description="User ID")
    session_id: str = Field(..., description="Session ID")
    memory_type: str = Field(..., description="Memory type")
    content: Dict[str, Any] = Field(..., description="Memory content")
    ttl_seconds: Optional[int] = Field(
        None, description="Time-to-live in seconds (optional)"
    )


class StoreSessionMemoryResponse(MCPResponseBase):
    """Response from storing session memory."""

    memory_id: str = Field(..., description="Memory ID")
    session_id: str = Field(..., description="Session ID")
    memory_type: str = Field(..., description="Memory type")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")


class GetSessionMemoryRequest(MCPRequestBase):
    """Request to get session memory."""

    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    memory_type: Optional[str] = Field(None, description="Memory type")


class GetSessionMemoryResponse(MCPResponseBase):
    """Response from getting session memory."""

    memories: List[SessionMemory] = Field([], description="Session memories")
    memory_count: int = Field(0, description="Number of memories")
