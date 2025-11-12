"""Configuration management API endpoints.

Provides RESTful endpoints for managing agent configurations with validation,
versioning, and environment summaries. This router depends only on schema
models and simple in-memory defaults; persistence is stubbed for tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from tripsage.api.core.dependencies import AdminPrincipalDep, get_principal_id
from tripsage.api.schemas.config import (
    AgentConfigRequest,
    AgentConfigResponse,
    AgentType,
    ConfigurationScope,
    ConfigurationVersion,
    ModelName,
)
from tripsage_core.config import get_settings


router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/agents", response_model=list[str])
async def list_agent_types(principal: AdminPrincipalDep) -> list[str]:
    """List available agent types (admin-only)."""
    _ = principal
    return [
        AgentType.BUDGET_AGENT.value,
        AgentType.ITINERARY_AGENT.value,
    ]


@router.get("/agents/{agent_type}", response_model=AgentConfigResponse)
async def get_agent_config(
    agent_type: str, principal: AdminPrincipalDep
) -> AgentConfigResponse:
    """Return current configuration for an agent type (admin-only)."""
    _ = principal
    valid = {a.value for a in AgentType}
    if agent_type not in valid:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Agent type '{agent_type}' not found. Valid types: {sorted(valid)}"
            ),
        )

    # Minimal defaults for tests
    defaults: dict[str, Any] = {
        "budget_agent": {
            "temperature": 0.1,
            "max_tokens": 1000,
            "top_p": 0.9,
            "timeout_seconds": 30,
            "model": cast(ModelName, "gpt-4o-mini"),
        },
        "itinerary_agent": {
            "temperature": 0.2,
            "max_tokens": 3000,
            "top_p": 0.9,
            "timeout_seconds": 120,
            "model": cast(ModelName, "gpt-4o"),
        },
    }
    cfg = defaults[agent_type]
    return AgentConfigResponse(
        agent_type=AgentType(agent_type),
        temperature=float(cfg["temperature"]),
        max_tokens=int(cfg["max_tokens"]),
        top_p=float(cfg["top_p"]),
        timeout_seconds=int(cfg["timeout_seconds"]),
        model=cast(ModelName, cfg["model"]),
        scope=ConfigurationScope.AGENT_SPECIFIC,
        updated_at=datetime.now(UTC),
    )


@router.put("/agents/{agent_type}", response_model=AgentConfigResponse)
async def update_agent_config(
    agent_type: str, config_update: AgentConfigRequest, principal: AdminPrincipalDep
) -> AgentConfigResponse:
    """Update configuration for an agent type (admin-only)."""
    _ = principal
    # Validate type
    valid = {a.value for a in AgentType}
    if agent_type not in valid:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Agent type '{agent_type}' not found. Valid types: {sorted(valid)}"
            ),
        )

    # Start from current defaults and overlay update
    current = await get_agent_config(agent_type, principal)
    updates: dict[str, Any] = {}
    if config_update.temperature is not None:
        updates["temperature"] = float(config_update.temperature)
    if config_update.max_tokens is not None:
        updates["max_tokens"] = int(config_update.max_tokens)
    if config_update.top_p is not None:
        updates["top_p"] = float(config_update.top_p)
    if config_update.timeout_seconds is not None:
        updates["timeout_seconds"] = int(config_update.timeout_seconds)
    if config_update.model is not None:
        updates["model"] = config_update.model

    return AgentConfigResponse(
        agent_type=current.agent_type,
        temperature=cast(float, updates.get("temperature", current.temperature)),
        max_tokens=cast(int, updates.get("max_tokens", current.max_tokens)),
        top_p=cast(float, updates.get("top_p", current.top_p)),
        timeout_seconds=cast(
            int, updates.get("timeout_seconds", current.timeout_seconds)
        ),
        model=cast(ModelName, updates.get("model", current.model)),
        scope=ConfigurationScope.AGENT_SPECIFIC,
        updated_at=datetime.now(UTC),
        updated_by=get_principal_id(principal),
    )


@router.get("/agents/{agent_type}/versions", response_model=list[ConfigurationVersion])
async def get_agent_config_versions(
    agent_type: str, principal: AdminPrincipalDep, limit: int = 10
) -> list[ConfigurationVersion]:
    """Return placeholder config version history (admin-only)."""
    _ = (agent_type, principal, limit)
    return []


@router.post("/agents/{agent_type}/rollback/{version_id}")
async def rollback_agent_config(
    agent_type: str, version_id: str, principal: AdminPrincipalDep
) -> JSONResponse:
    """Queue a rollback to a specific version (admin-only)."""
    valid = {a.value for a in AgentType}
    if agent_type not in valid:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Agent type '{agent_type}' not found. Valid types: {sorted(valid)}"
            ),
        )
    _ = principal
    return JSONResponse(
        content={
            "message": f"Configuration rolled back to version {version_id}",
            "agent_type": agent_type,
            "version_id": version_id,
        }
    )


@router.get("/environment", response_model=dict[str, Any])
async def get_environment_config() -> dict[str, Any]:
    """Get current environment configuration summary."""
    settings = get_settings()
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "feature_flags": {
            "enable_advanced_agents": True,
            "enable_memory_system": True,
            # Supabase Realtime is the only realtime transport; no custom WS
            "enable_real_time": True,
            "enable_vector_search": True,
            "enable_monitoring": True,
        },
        "global_defaults": {
            "temperature": settings.model_temperature,
            "max_tokens": 2000,
            "top_p": 0.9,
            "timeout_seconds": 60,
            "model": getattr(settings, "openai_model", "gpt-4o"),
        },
    }
