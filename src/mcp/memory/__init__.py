"""
Memory MCP module for the TripSage travel planning system.

This module provides a client for the Memory MCP server, which enables
storage and retrieval of travel knowledge in a persistent knowledge graph.
"""

from .client import MemoryMCPClient, memory_client
from .models import (
    AddObservationsParams,
    AddObservationsResponse,
    CreateEntitiesParams,
    CreateEntitiesResponse,
    CreateRelationsParams,
    CreateRelationsResponse,
    DeleteEntitiesParams,
    DeleteEntitiesResponse,
    DeleteObservationsParams,
    DeleteObservationsResponse,
    DeleteRelationsParams,
    DeleteRelationsResponse,
    Entity,
    EntityResponse,
    GraphResponse,
    Observation,
    OpenNodesParams,
    OpenNodesResponse,
    Relation,
    RelationResponse,
    SearchNodesParams,
    SearchNodesResponse,
)

# Import server conditionally to avoid errors in testing
try:
    from .server import create_memory_server  # noqa: F401
    __has_server = True
except ImportError:
    __has_server = False

# Define __all__ based on available modules
__all__ = [
    # Client
    "MemoryMCPClient",
    "memory_client",
    # Basic models
    "Entity",
    "Relation",
    "Observation",
    # Parameter models
    "CreateEntitiesParams",
    "CreateRelationsParams",
    "AddObservationsParams",
    "DeleteEntitiesParams",
    "DeleteObservationsParams",
    "DeleteRelationsParams",
    "SearchNodesParams",
    "OpenNodesParams",
    # Response models
    "EntityResponse",
    "RelationResponse",
    "GraphResponse",
    "CreateEntitiesResponse",
    "CreateRelationsResponse",
    "AddObservationsResponse",
    "DeleteEntitiesResponse",
    "DeleteObservationsResponse",
    "DeleteRelationsResponse",
    "SearchNodesResponse",
    "OpenNodesResponse",
]

# Add server if available
if __has_server:
    __all__.append("create_memory_server")
