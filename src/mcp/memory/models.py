"""
Pydantic models for Memory MCP client.

This module defines the parameter and response models for the Memory MCP Client,
providing proper validation and type safety.
"""

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseParams(BaseModel):
    """Base model for all parameter models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class BaseResponse(BaseModel):
    """Base model for all response models."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Entity(BaseModel):
    """Model for an entity in the knowledge graph."""

    name: str = Field(..., description="Entity name (unique identifier)")
    entityType: str = Field(..., description="Entity type")
    observations: List[str] = Field(
        [], description="List of observations about the entity"
    )

    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate entity name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Entity name cannot be empty")
        return v

    @field_validator("entityType")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity type."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Entity type cannot be empty")
        return v


class Relation(BaseModel):
    """Model for a relation in the knowledge graph."""

    from_: str = Field(..., alias="from", description="Source entity name")
    relationType: str = Field(..., description="Relation type")
    to: str = Field(..., description="Target entity name")

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @field_validator("from_")
    @classmethod
    def validate_from(cls, v: str) -> str:
        """Validate source entity name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Source entity name cannot be empty")
        return v

    @field_validator("relationType")
    @classmethod
    def validate_relation_type(cls, v: str) -> str:
        """Validate relation type."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Relation type cannot be empty")
        return v

    @field_validator("to")
    @classmethod
    def validate_to(cls, v: str) -> str:
        """Validate target entity name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Target entity name cannot be empty")
        return v


class Observation(BaseModel):
    """Model for an observation to add to an entity."""

    entityName: str = Field(..., description="Entity name to add observations to")
    contents: List[str] = Field(..., description="List of observation contents to add")

    model_config = ConfigDict(extra="allow")

    @field_validator("entityName")
    @classmethod
    def validate_entity_name(cls, v: str) -> str:
        """Validate entity name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Entity name cannot be empty")
        return v

    @field_validator("contents")
    @classmethod
    def validate_contents(cls, v: List[str]) -> List[str]:
        """Validate observation contents."""
        if not v:
            raise ValueError("Observation contents cannot be empty")
        return v


class CreateEntitiesParams(BaseParams):
    """Parameters for creating entities."""

    entities: List[Entity] = Field(..., description="List of entities to create")

    @field_validator("entities")
    @classmethod
    def validate_entities(cls, v: List[Entity]) -> List[Entity]:
        """Validate entities list."""
        if not v:
            raise ValueError("Entities list cannot be empty")
        return v


class CreateRelationsParams(BaseParams):
    """Parameters for creating relations."""

    relations: List[Relation] = Field(..., description="List of relations to create")

    @field_validator("relations")
    @classmethod
    def validate_relations(cls, v: List[Relation]) -> List[Relation]:
        """Validate relations list."""
        if not v:
            raise ValueError("Relations list cannot be empty")
        return v


class AddObservationsParams(BaseParams):
    """Parameters for adding observations."""

    observations: List[Observation] = Field(
        ..., description="List of observations to add"
    )

    @field_validator("observations")
    @classmethod
    def validate_observations(cls, v: List[Observation]) -> List[Observation]:
        """Validate observations list."""
        if not v:
            raise ValueError("Observations list cannot be empty")
        return v


class DeleteEntitiesParams(BaseParams):
    """Parameters for deleting entities."""

    entityNames: List[str] = Field(..., description="List of entity names to delete")

    @field_validator("entityNames")
    @classmethod
    def validate_entity_names(cls, v: List[str]) -> List[str]:
        """Validate entity names list."""
        if not v:
            raise ValueError("Entity names list cannot be empty")

        for name in v:
            if not name or len(name.strip()) == 0:
                raise ValueError("Entity name cannot be empty")

        return v


class DeleteObservationsParams(BaseParams):
    """Parameters for deleting observations."""

    deletions: List[Observation] = Field(
        ..., description="List of observations to delete"
    )

    @field_validator("deletions")
    @classmethod
    def validate_deletions(cls, v: List[Observation]) -> List[Observation]:
        """Validate deletions list."""
        if not v:
            raise ValueError("Deletions list cannot be empty")
        return v


class DeleteRelationsParams(BaseParams):
    """Parameters for deleting relations."""

    relations: List[Relation] = Field(..., description="List of relations to delete")

    @field_validator("relations")
    @classmethod
    def validate_relations(cls, v: List[Relation]) -> List[Relation]:
        """Validate relations list."""
        if not v:
            raise ValueError("Relations list cannot be empty")
        return v


class SearchNodesParams(BaseParams):
    """Parameters for searching nodes."""

    query: str = Field(
        ..., description="Search query to match against entity properties"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Search query cannot be empty")
        return v


class OpenNodesParams(BaseParams):
    """Parameters for opening specific nodes."""

    names: List[str] = Field(..., description="List of entity names to open")

    @field_validator("names")
    @classmethod
    def validate_names(cls, v: List[str]) -> List[str]:
        """Validate names list."""
        if not v:
            raise ValueError("Names list cannot be empty")

        for name in v:
            if not name or len(name.strip()) == 0:
                raise ValueError("Entity name cannot be empty")

        return v


class EntityResponse(BaseResponse):
    """Response model for an entity."""

    id: str = Field(..., description="Entity ID")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type")
    observations: List[str] = Field(
        [], description="List of observations about the entity"
    )
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class RelationResponse(BaseResponse):
    """Response model for a relation."""

    id: str = Field(..., description="Relation ID")
    from_entity: str = Field(..., description="Source entity name")
    to_entity: str = Field(..., description="Target entity name")
    type: str = Field(..., description="Relation type")
    created_at: str = Field(..., description="Creation timestamp")


class GraphResponse(BaseResponse):
    """Response model for the entire knowledge graph."""

    entities: List[EntityResponse] = Field(
        [], description="List of entities in the graph"
    )
    relations: List[RelationResponse] = Field(
        [], description="List of relations in the graph"
    )


class CreateEntitiesResponse(BaseResponse):
    """Response for entity creation."""

    entities: List[EntityResponse] = Field([], description="List of created entities")
    message: str = Field(..., description="Success or error message")


class CreateRelationsResponse(BaseResponse):
    """Response for relation creation."""

    relations: List[RelationResponse] = Field(
        [], description="List of created relations"
    )
    message: str = Field(..., description="Success or error message")


class AddObservationsResponse(BaseResponse):
    """Response for adding observations."""

    updated_entities: List[EntityResponse] = Field(
        [], description="List of updated entities"
    )
    message: str = Field(..., description="Success or error message")


class DeleteEntitiesResponse(BaseResponse):
    """Response for deleting entities."""

    deleted_count: int = Field(0, description="Number of entities deleted")
    message: str = Field(..., description="Success or error message")


class DeleteObservationsResponse(BaseResponse):
    """Response for deleting observations."""

    updated_entities: List[EntityResponse] = Field(
        [], description="List of updated entities"
    )
    message: str = Field(..., description="Success or error message")


class DeleteRelationsResponse(BaseResponse):
    """Response for deleting relations."""

    deleted_count: int = Field(0, description="Number of relations deleted")
    message: str = Field(..., description="Success or error message")


class SearchNodesResponse(BaseResponse):
    """Response for searching nodes."""

    results: List[EntityResponse] = Field([], description="List of matching entities")
    count: int = Field(0, description="Number of results found")


class OpenNodesResponse(BaseResponse):
    """Response for opening specific nodes."""

    entities: List[EntityResponse] = Field([], description="List of opened entities")
    count: int = Field(0, description="Number of entities opened")
