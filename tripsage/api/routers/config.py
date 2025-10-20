"""Configuration management API endpoints.

Provides RESTful endpoints for managing agent configurations with validation,
versioning, and real-time updates following 2025 best practices.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from tripsage.api.core.auth import get_current_user_id
from tripsage.api.schemas.config import (
    AgentConfigRequest,
    AgentConfigResponse,
    AgentType,
    ConfigurationVersion,
    WebSocketConfigMessage,
)
from tripsage_core.config import get_settings
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/config", tags=["configuration"])


# WebSocket connection manager
class ConfigurationWebSocketManager:
    """Manages WebSocket connections for real-time configuration updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_update(self, message: WebSocketConfigMessage):
        """Broadcast configuration update to all connected clients."""
        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message.model_dump())
            except Exception:
                self.disconnect(connection)


# Global WebSocket manager using the imported schema
ws_manager = ConfigurationWebSocketManager()


@router.get("/agents", response_model=list[str])
async def list_agent_types():
    """List all available agent types."""
    return ["budget_agent", "destination_research_agent", "itinerary_agent"]


@router.get("/agents/{agent_type}", response_model=AgentConfigResponse)
async def get_agent_config(agent_type: str):
    """Get current configuration for a specific agent type."""
    settings = get_settings()

    # Validate agent type
    valid_agents = ["budget_agent", "destination_research_agent", "itinerary_agent"]
    if agent_type not in valid_agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{agent_type}' not found. Valid types: {valid_agents}",
        )

    try:
        config = settings.get_agent_config(agent_type)

        return AgentConfigResponse(
            agent_type=agent_type,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            top_p=config["top_p"],
            timeout_seconds=config["timeout_seconds"],
            model=config["model"],
            updated_at=datetime.now(UTC),
        )
    except Exception as e:
        logger.exception("Error getting agent config for %s", agent_type)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/agents/{agent_type}", response_model=AgentConfigResponse)
async def update_agent_config(
    agent_type: str,
    config_update: AgentConfigRequest,
    current_user: str = Depends(get_current_user_id),
):
    """Update configuration for a specific agent type."""
    settings = get_settings()

    # Validate agent type
    valid_agents = ["budget_agent", "destination_research_agent", "itinerary_agent"]
    if agent_type not in valid_agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{agent_type}' not found. Valid types: {valid_agents}",
        )

    try:
        # Get current config for validation
        settings.get_agent_config(agent_type)

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
        updated_config = settings.get_agent_config(agent_type, **updates)

        # TODO: Persist to database here
        # await _persist_agent_config(agent_type, updated_config, current_user)

        # Create version record
        # TODO: Save version to database
        # await _create_config_version(agent_type, updated_config, current_user)

        # Broadcast update to connected clients
        message = WebSocketConfigMessage(
            type="agent_config_updated",
            agent_type=AgentType(agent_type),
            configuration=updated_config,
            updated_by=current_user,
        )
        await ws_manager.broadcast_update(message)

        logger.info("Agent config updated for %s by %s", agent_type, current_user)

        return AgentConfigResponse(
            agent_type=agent_type,
            temperature=updated_config["temperature"],
            max_tokens=updated_config["max_tokens"],
            top_p=updated_config["top_p"],
            timeout_seconds=updated_config["timeout_seconds"],
            model=updated_config["model"],
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
    agent_type: str, limit: int = 10, current_user: str = Depends(get_current_user_id)
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
        # TODO: Implement database query for version history
        # versions = await _get_config_versions(agent_type, limit)

        # Placeholder response
        return []

    except Exception as e:
        logger.exception("Error getting config versions for %s", agent_type)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/agents/{agent_type}/rollback/{version_id}")
async def rollback_agent_config(
    agent_type: str, version_id: str, current_user: str = Depends(get_current_user_id)
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
            "enable_advanced_agents": settings.enable_advanced_agents,
            "enable_memory_system": settings.enable_memory_system,
            "enable_real_time": settings.enable_real_time,
            "enable_vector_search": settings.enable_vector_search,
            "enable_monitoring": settings.enable_monitoring,
        },
        "global_defaults": {
            "temperature": settings.agent_default_temperature,
            "max_tokens": settings.agent_default_max_tokens,
            "top_p": settings.agent_default_top_p,
            "timeout_seconds": settings.agent_timeout_seconds,
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
