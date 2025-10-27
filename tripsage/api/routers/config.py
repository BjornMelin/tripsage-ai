"""Configuration management API endpoints.

Provides RESTful endpoints for managing agent configurations with validation,
versioning, and real-time updates following 2025 best practices.

"""
# pyright: reportUnknownVariableType=false

from datetime import UTC, datetime
from typing import Any, TypedDict, cast

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from tripsage.api.core.dependencies import (
    RequiredPrincipalDep,
    get_principal_id,
)
from tripsage.api.schemas.config import (
    AgentConfigRequest,
    AgentConfigResponse,
    AgentType,
    ConfigurationScope,
    ConfigurationVersion,
    ModelName,
    WebSocketConfigMessage,
)
from tripsage_core.config import get_settings
from tripsage_core.observability.otel import record_histogram, trace_span
from tripsage_core.utils.logging_utils import get_logger


# Strongly-typed default agent configuration
class AgentConfig(TypedDict):
    """Typed shape for agent configuration defaults used in this router."""

    temperature: float
    max_tokens: int
    top_p: float
    timeout_seconds: int
    model: ModelName


# Default agent configurations
DEFAULT_AGENT_CONFIGS: dict[AgentType, AgentConfig] = {
    AgentType.BUDGET_AGENT: {
        "temperature": 0.1,
        "max_tokens": 1000,
        "top_p": 0.9,
        "timeout_seconds": 30,
        "model": "gpt-4o-mini",
    },
    AgentType.DESTINATION_RESEARCH_AGENT: {
        "temperature": 0.3,
        "max_tokens": 2000,
        "top_p": 0.95,
        "timeout_seconds": 60,
        "model": "gpt-4o",
    },
    AgentType.ITINERARY_AGENT: {
        "temperature": 0.2,
        "max_tokens": 3000,
        "top_p": 0.9,
        "timeout_seconds": 120,
        "model": "gpt-4o",
    },
}


logger: Any = get_logger(__name__)

router = APIRouter(prefix="/config", tags=["configuration"])


# WebSocket connection manager
class ConfigurationWebSocketManager:
    """Manages WebSocket connections for real-time configuration updates."""

    def __init__(self):
        """Initialize Config."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and track WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket from tracking."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_update(self, message: WebSocketConfigMessage):
        """Broadcast configuration update to all connected clients."""
        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message.model_dump())
            except (OSError, RuntimeError):
                # Network/connection errors during WebSocket send
                self.disconnect(connection)


# Global WebSocket manager using the imported schema
ws_manager = ConfigurationWebSocketManager()


@router.get("/agents", response_model=list[str])
@trace_span(name="api.config.agents.list")
@record_histogram("api.op.duration", unit="s")
async def list_agent_types():
    """List all available agent types."""
    return ["budget_agent", "destination_research_agent", "itinerary_agent"]


@router.get("/agents/{agent_type}", response_model=AgentConfigResponse)
@trace_span(name="api.config.agents.get")
@record_histogram("api.op.duration", unit="s")
async def get_agent_config(agent_type: str):
    """Get current configuration for a specific agent type."""
    # Validate agent type
    valid_agents = ["budget_agent", "destination_research_agent", "itinerary_agent"]
    if agent_type not in valid_agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{agent_type}' not found. Valid types: {valid_agents}",
        )

    try:
        agent_type_enum = AgentType(agent_type)
        config = DEFAULT_AGENT_CONFIGS.get(agent_type_enum)
        if not config:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return AgentConfigResponse(
            agent_type=agent_type_enum,
            temperature=float(config["temperature"]),
            max_tokens=int(config["max_tokens"]),
            top_p=float(config["top_p"]),
            timeout_seconds=int(config["timeout_seconds"]),
            model=config["model"],
            scope=ConfigurationScope.AGENT_SPECIFIC,
            updated_at=datetime.now(UTC),
        )
    except Exception as e:
        logger.exception("Error getting agent config for %s", agent_type)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/agents/{agent_type}", response_model=AgentConfigResponse)
@trace_span(name="api.config.agents.update")
@record_histogram("api.op.duration", unit="s")
async def update_agent_config(
    agent_type: str,
    config_update: AgentConfigRequest,
    principal: RequiredPrincipalDep,
):
    """Update configuration for a specific agent type."""
    # Validate agent type
    valid_agents = ["budget_agent", "destination_research_agent", "itinerary_agent"]
    if agent_type not in valid_agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{agent_type}' not found. Valid types: {valid_agents}",
        )

    try:
        # Get current config
        agent_type_enum = AgentType(agent_type)
        current_config = DEFAULT_AGENT_CONFIGS.get(agent_type_enum)
        if not current_config:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Create update dict with only provided values
        updates = {}
        if config_update.temperature is not None:
            updates["temperature"] = config_update.temperature
        if config_update.max_tokens is not None:
            updates["max_tokens"] = config_update.max_tokens
        if config_update.top_p is not None:
            updates["top_p"] = config_update.top_p
        if config_update.timeout_seconds is not None:
            updates["timeout_seconds"] = config_update.timeout_seconds
        if config_update.model is not None:
            updates["model"] = config_update.model

        # Apply updates to get new config
        updated_config = cast(AgentConfig, {**current_config, **updates})

        current_user = get_principal_id(principal)
        # TODO: Persist to database here
        # await _persist_agent_config(agent_type, updated_config, current_user)

        # Create version record
        # TODO: Save version to database
        # await _create_config_version(agent_type, updated_config, current_user)

        # Broadcast update to connected clients
        message = WebSocketConfigMessage(
            type="agent_config_updated",
            agent_type=AgentType(agent_type),
            configuration=dict(updated_config),
            updated_by=current_user,
        )
        await ws_manager.broadcast_update(message)

        logger.info("Agent config updated for %s by %s", agent_type, current_user)

        return AgentConfigResponse(
            agent_type=AgentType(agent_type),
            temperature=float(updated_config["temperature"]),
            max_tokens=int(updated_config["max_tokens"]),
            top_p=float(updated_config["top_p"]),
            timeout_seconds=int(updated_config["timeout_seconds"]),
            model=updated_config["model"],
            scope=ConfigurationScope.AGENT_SPECIFIC,
            updated_at=datetime.now(UTC),
            updated_by=current_user,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error updating agent config for %s", agent_type)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/agents/{agent_type}/versions", response_model=list[ConfigurationVersion])
async def get_agent_config_versions(
    agent_type: str,
    principal: RequiredPrincipalDep,
    limit: int = 10,
):
    """Get configuration version history for an agent type."""
    # Validate agent type
    valid_agents = ["budget_agent", "destination_research_agent", "itinerary_agent"]
    if agent_type not in valid_agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{agent_type}' not found. Valid types: {valid_agents}",
        )

    try:
        _ = get_principal_id(principal)
        # TODO: Implement database query for version history (user id available)
        # versions = await _get_config_versions(agent_type, limit)

        # Placeholder response
        return cast(list[ConfigurationVersion], [])

    except Exception as e:
        logger.exception("Error getting config versions for %s", agent_type)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/agents/{agent_type}/rollback/{version_id}")
async def rollback_agent_config(
    agent_type: str, version_id: str, principal: RequiredPrincipalDep
):
    """Rollback agent configuration to a specific version."""
    # Validate agent type
    valid_agents = ["budget_agent", "destination_research_agent", "itinerary_agent"]
    if agent_type not in valid_agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{agent_type}' not found. Valid types: {valid_agents}",
        )

    try:
        current_user = get_principal_id(principal)
        # TODO: Implement version rollback
        # config = await _rollback_to_version(agent_type, version_id, current_user)

        # Broadcast rollback to connected clients
        message = WebSocketConfigMessage(
            type="agent_config_rolled_back",
            agent_type=AgentType(agent_type),
            version_id=version_id,
            updated_by=current_user,
        )
        await ws_manager.broadcast_update(message)

        return JSONResponse(
            content={
                "message": f"Configuration rolled back to version {version_id}",
                "agent_type": agent_type,
                "version_id": version_id,
            }
        )

    except Exception as e:
        logger.exception("Error rolling back config for %s", agent_type)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/environment")
async def get_environment_config():
    """Get current environment configuration summary."""
    settings = get_settings()

    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "feature_flags": {
            "enable_advanced_agents": True,
            "enable_memory_system": True,
            "enable_real_time": settings.enable_websockets,
            "enable_vector_search": True,
            "enable_monitoring": True,
        },
        "global_defaults": {
            "temperature": settings.model_temperature,
            "max_tokens": 2000,  # Default max tokens
            "top_p": 0.9,  # Default top_p
            "timeout_seconds": 60,  # Default timeout
            "model": settings.openai_model,
        },
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time configuration updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        logger.exception("Configuration WebSocket error")
        ws_manager.disconnect(websocket)
