"""Memory model classes for TripSage.

This module provides the memory-related model classes for interaction with
the knowledge graph and session memory in the TripSage application.
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from tripsage.models.mcp import MCPRequestBase, MCPResponseBase
from tripsage_core.models.domain.memory import (
    Entity,
    Relation,
    SessionMemory,
)


# Entity and Relation moved to tripsage_core.models.domain.memory


class CreateEntitiesRequest(MCPRequestBase):
    """Request to create entities in the knowledge graph."""

    entities: list[Entity] = Field(..., description="Entities to create")


class CreateEntitiesResponse(MCPResponseBase):
    """Response from creating entities in the knowledge graph."""

    created_count: int = Field(0, description="Number of entities created")
    entities: list[Entity] = Field([], description="Created entities")


class CreateRelationsRequest(MCPRequestBase):
    """Request to create relations in the knowledge graph."""

    relations: list[Relation] = Field(..., description="Relations to create")


class CreateRelationsResponse(MCPResponseBase):
    """Response from creating relations in the knowledge graph."""

    created_count: int = Field(0, description="Number of relations created")
    relations: list[Relation] = Field([], description="Created relations")


class AddObservationsRequest(MCPRequestBase):
    """Request to add observations to entities."""

    observations: list[dict[str, Any]] = Field(..., description="Observations to add")


class AddObservationsResponse(MCPResponseBase):
    """Response from adding observations to entities."""

    updated_count: int = Field(0, description="Number of entities updated")
    entities: list[str] = Field([], description="Updated entity names")


class SearchNodesRequest(MCPRequestBase):
    """Request to search for nodes in the knowledge graph."""

    query: str = Field(..., description="Search query")
    entity_types: list[str] | None = Field(
        None, description="Entity types to filter by"
    )
    limit: int = Field(10, description="Maximum number of results to return")


class SearchNodesResponse(MCPResponseBase):
    """Response from searching for nodes in the knowledge graph."""

    matches: list[Entity] = Field([], description="Matching entities")
    match_count: int = Field(0, description="Number of matching entities")


class OpenNodesRequest(MCPRequestBase):
    """Request to open specific nodes in the knowledge graph."""

    names: list[str] = Field(..., description="Entity names to open")


class OpenNodesResponse(MCPResponseBase):
    """Response from opening specific nodes in the knowledge graph."""

    entities: list[Entity] = Field([], description="Opened entities")
    found_count: int = Field(0, description="Number of entities found")


class ReadGraphRequest(MCPRequestBase):
    """Request to read the entire knowledge graph."""

    limit: int | None = Field(None, description="Maximum number of results to return")
    include_observations: bool = Field(
        True, description="Whether to include observations"
    )


class ReadGraphResponse(MCPResponseBase):
    """Response from reading the entire knowledge graph."""

    entities: list[Entity] = Field([], description="All entities")
    relations: list[Relation] = Field([], description="All relations")
    entity_count: int = Field(0, description="Number of entities")
    relation_count: int = Field(0, description="Number of relations")


# SessionMemory moved to tripsage_core.models.domain.memory


class StoreSessionMemoryRequest(MCPRequestBase):
    """Request to store session memory."""

    user_id: str | None = Field(None, description="User ID")
    session_id: str = Field(..., description="Session ID")
    memory_type: str = Field(..., description="Memory type")
    content: dict[str, Any] = Field(..., description="Memory content")
    ttl_seconds: int | None = Field(
        None, description="Time-to-live in seconds (optional)"
    )


class StoreSessionMemoryResponse(MCPResponseBase):
    """Response from storing session memory."""

    memory_id: str = Field(..., description="Memory ID")
    session_id: str = Field(..., description="Session ID")
    memory_type: str = Field(..., description="Memory type")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")


class GetSessionMemoryRequest(MCPRequestBase):
    """Request to get session memory."""

    user_id: str | None = Field(None, description="User ID")
    session_id: str | None = Field(None, description="Session ID")
    memory_type: str | None = Field(None, description="Memory type")


class GetSessionMemoryResponse(MCPResponseBase):
    """Response from getting session memory."""

    memories: list[SessionMemory] = Field([], description="Session memories")
    memory_count: int = Field(0, description="Number of memories")
