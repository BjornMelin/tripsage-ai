"""Configuration Service for dynamic agent configuration management (Supabase-only)."""

from collections.abc import Callable
from functools import lru_cache
from typing import Any, cast

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.types import JSONObject
from tripsage_core.utils.cache_utils import (
    delete_cache,
    generate_cache_key,
    get_cache,
    set_cache,
)
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)

AgentConfig = dict[str, Any]


def _coerce_optional_float(value: Any, *, default: float | None = None) -> float | None:
    """Convert arbitrary value to float when possible."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _coerce_optional_int(value: Any) -> int | None:
    """Convert arbitrary value to int when possible."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _coerce_optional_str(value: Any) -> str | None:
    """Convert arbitrary value to string when possible."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


class ConfigurationService:
    """Service for managing agent configurations with database persistence."""

    def __init__(self):
        """Initialize configuration service with settings and DB client."""
        self.settings = get_settings()
        self._cache_ttl = 300  # 5 minutes cache TTL for config data
        self._db = DatabaseService()

    async def get_agent_config(
        self,
        agent_type: str,
        environment: str | None = None,
        **overrides: Any,
    ) -> AgentConfig:
        """Get configuration for an agent with caching and fallback logic.

        Priority order:
        1. Runtime overrides (highest)
        2. Database-stored agent-specific config
        3. Environment defaults from settings
        4. Global defaults (lowest)
        """
        if environment is None:
            environment = self.settings.environment

        # Check cache first
        cache_key_str = generate_cache_key(
            "agent_config", f"{agent_type}:{environment}"
        )
        cached_config = cast(AgentConfig | None, await get_cache(cache_key_str))
        if cached_config and not overrides:
            logger.debug("Using cached config for %s in %s", agent_type, environment)
            return cached_config
        runtime_overrides: AgentConfig = dict(overrides)

        try:
            db_config = await self._get_agent_config_from_db(agent_type, environment)

            if db_config:
                final_config: AgentConfig = {**db_config, **runtime_overrides}
                await set_cache(cache_key_str, db_config, ttl=self._cache_ttl)

                logger.debug(
                    "Using database config for %s in %s", agent_type, environment
                )
                return final_config

            default_fn = self._resolve_default_config_fn()
            fallback_config = default_fn(agent_type, **runtime_overrides)
            logger.warning(
                "No database config found for %s, using fallback", agent_type
            )
            return fallback_config

        except Exception:
            logger.exception("Error getting agent config from database")
            default_fn = self._resolve_default_config_fn()
            return default_fn(agent_type, **runtime_overrides)

    def _resolve_default_config_fn(self) -> Callable[..., AgentConfig]:
        """Resolve the default configuration factory from settings."""
        default_fn = getattr(self.settings, "default_agent_config", None)
        if callable(default_fn):
            return cast(Callable[..., AgentConfig], default_fn)
        return lambda *_args, **_kwargs: {}

    async def _get_agent_config_from_db(
        self, agent_type: str, environment: str
    ) -> dict[str, Any] | None:
        """Get agent configuration from database via Supabase."""
        await self._db.ensure_connected()
        rows = await self._db.select(
            "configuration_profiles",
            "temperature,max_tokens,top_p,timeout_seconds,model,description,updated_at,updated_by",
            filters={
                "agent_type": agent_type,
                "environment": environment,
                "is_active": True,
            },
            limit=1,
        )
        if not rows:
            return None
        row = rows[0]
        temperature = _coerce_optional_float(row.get("temperature"), default=0.0)
        top_p = _coerce_optional_float(row.get("top_p"), default=1.0)
        max_tokens = _coerce_optional_int(row.get("max_tokens"))
        timeout_seconds = _coerce_optional_int(row.get("timeout_seconds"))

        config: AgentConfig = {
            "model": _coerce_optional_str(row.get("model")),
            "temperature": temperature if temperature is not None else 0.0,
            "max_tokens": max_tokens,
            "top_p": top_p if top_p is not None else 1.0,
            "timeout_seconds": timeout_seconds,
            # pylint: disable=no-member
            "api_key": self.settings.openai_api_key.get_secret_value(),
            "description": _coerce_optional_str(row.get("description")),
            "updated_at": row.get("updated_at"),
            "updated_by": _coerce_optional_str(row.get("updated_by")),
        }
        return config

    async def update_agent_config(
        self,
        agent_type: str,
        *,
        config_updates: dict[str, Any],
        updated_by: str,
        environment: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create or update an agent configuration profile in Supabase.

        Args:
            agent_type: Logical agent type key.
            config_updates: Fields to update (temperature, max_tokens, top_p,
                timeout_seconds, model).
            updated_by: User identifier performing the change.
            environment: Target environment, defaults to settings.environment.
            description: Optional description to set.

        Returns:
            The resolved configuration after update.
        """
        if environment is None:
            environment = self.settings.environment

        await self._db.ensure_connected()

        current = await self._get_agent_config_from_db(agent_type, environment)
        default_fn = self._resolve_default_config_fn()
        defaults = default_fn(agent_type)

        if not current:
            final_config: AgentConfig = {**defaults, **config_updates}
            payload: JSONObject = {
                "agent_type": agent_type,
                "temperature": _coerce_optional_float(final_config.get("temperature")),
                "max_tokens": _coerce_optional_int(final_config.get("max_tokens")),
                "top_p": _coerce_optional_float(final_config.get("top_p")),
                "timeout_seconds": _coerce_optional_int(
                    final_config.get("timeout_seconds")
                ),
                "model": _coerce_optional_str(final_config.get("model")),
                "environment": environment,
                "description": _coerce_optional_str(description),
                "created_by": updated_by,
                "updated_by": updated_by,
                "is_active": True,
            }
            await self._db.insert("configuration_profiles", payload)
        else:
            update_fields: JSONObject = {}
            if "temperature" in config_updates:
                update_fields["temperature"] = _coerce_optional_float(
                    config_updates["temperature"]
                )
            if "max_tokens" in config_updates:
                update_fields["max_tokens"] = _coerce_optional_int(
                    config_updates["max_tokens"]
                )
            if "top_p" in config_updates:
                update_fields["top_p"] = _coerce_optional_float(config_updates["top_p"])
            if "timeout_seconds" in config_updates:
                update_fields["timeout_seconds"] = _coerce_optional_int(
                    config_updates["timeout_seconds"]
                )
            if "model" in config_updates:
                update_fields["model"] = _coerce_optional_str(config_updates["model"])
            if description is not None:
                update_fields["description"] = _coerce_optional_str(description)
            update_fields["updated_by"] = updated_by
            if not update_fields:
                raise ValueError("No valid configuration fields to update")
            await self._db.update(
                "configuration_profiles",
                update_fields,
                filters={
                    "agent_type": agent_type,
                    "environment": environment,
                    "is_active": True,
                },
            )

        # Clear cache and return the new effective configuration
        cache_key_str = generate_cache_key(
            "agent_config", f"{agent_type}:{environment}"
        )
        await delete_cache(cache_key_str)
        updated_config = await self.get_agent_config(agent_type, environment)
        logger.info(
            "Agent config updated for %s in %s by %s",
            agent_type,
            environment,
            updated_by,
        )
        return updated_config

    # Legacy SQL paths removed; Supabase-only implementation above.

    async def get_configuration_versions(
        self, agent_type: str, environment: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get configuration version history."""
        if environment is None:
            environment = self.settings.environment

        # Not implemented in Supabase mode; versioning handled externally.
        return []

    async def rollback_to_version(
        self,
        agent_type: str,
        version_id: str,
        rolled_back_by: str,
        environment: str | None = None,
    ) -> dict[str, Any]:
        """Rollback configuration to a specific version."""
        if environment is None:
            environment = self.settings.environment

        raise NotImplementedError("Rollback not implemented in Supabase mode")

    async def get_all_agent_configs(
        self, environment: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """Get all agent configurations for an environment."""
        if environment is None:
            environment = self.settings.environment

        agent_types = [
            "budget_agent",
            "itinerary_agent",
        ]
        configs: dict[str, AgentConfig] = {}

        for agent_type in agent_types:
            try:
                configs[agent_type] = await self.get_agent_config(
                    agent_type, environment
                )
            except Exception:
                logger.exception("Error getting config for %s", agent_type)
                # Use fallback
                default_fn = self._resolve_default_config_fn()
                configs[agent_type] = default_fn(agent_type)

        return configs

    async def record_performance_metrics(
        self,
        agent_type: str,
        metrics: dict[str, Any],
        environment: str | None = None,
    ) -> None:
        """Record performance metrics for configuration optimization."""
        if environment is None:
            environment = self.settings.environment

        # Not implemented in Supabase mode.


@lru_cache(maxsize=1)
def get_configuration_service() -> ConfigurationService:
    """Return a cached singleton ConfigurationService instance."""
    return ConfigurationService()
