"""Configuration Service for dynamic agent configuration management.

Provides database-backed configuration management with caching, versioning,
and real-time updates following 2025 best practices.
"""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage_core.config import get_settings
from tripsage_core.database.connection import get_database_session
from tripsage_core.utils.cache_utils import (
    delete_cache,
    generate_cache_key,
    get_cache,
    set_cache,
)
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class ConfigurationService:
    """Service for managing agent configurations with database persistence."""

    def __init__(self):
        self.settings = get_settings()
        self._cache_ttl = 300  # 5 minutes cache TTL for config data

    async def get_agent_config(
        self, agent_type: str, environment: str | None = None, **overrides
    ) -> dict[str, Any]:
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
        cached_config = await get_cache(cache_key_str)
        if cached_config and not overrides:
            logger.debug(f"Using cached config for {agent_type} in {environment}")
            return cached_config

        try:
            # Get from database
            db_config = await self._get_agent_config_from_db(agent_type, environment)

            if db_config:
                # Merge with runtime overrides
                final_config = {**db_config, **overrides}

                # Cache the database result (without overrides)
                await set_cache(cache_key_str, db_config, ttl=self._cache_ttl)

                logger.debug(f"Using database config for {agent_type} in {environment}")
                return final_config
            else:
                # Fallback to settings-based config
                fallback_config = self.settings.get_agent_config(
                    agent_type, **overrides
                )
                logger.warning(
                    f"No database config found for {agent_type}, using fallback"
                )
                return fallback_config

        except Exception as e:
            logger.error(f"Error getting agent config from database: {e}")
            # Fallback to settings-based config
            return self.settings.get_agent_config(agent_type, **overrides)

    async def _get_agent_config_from_db(
        self, agent_type: str, environment: str
    ) -> dict[str, Any] | None:
        """Get agent configuration from database."""
        async with get_database_session() as session:
            result = await session.execute(
                text("""
                    SELECT temperature, max_tokens, top_p, timeout_seconds, model,
                           description, updated_at, updated_by
                    FROM configuration_profiles 
                    WHERE agent_type = :agent_type 
                      AND environment = :environment 
                      AND is_active = true
                    LIMIT 1
                """),
                {"agent_type": agent_type, "environment": environment},
            )

            row = result.fetchone()
            if row:
                return {
                    "model": row.model,
                    "temperature": float(row.temperature),
                    "max_tokens": row.max_tokens,
                    "top_p": float(row.top_p),
                    "timeout_seconds": row.timeout_seconds,
                    "api_key": self.settings.openai_api_key.get_secret_value(),
                    "description": row.description,
                    "updated_at": row.updated_at,
                    "updated_by": row.updated_by,
                }
            return None

    async def update_agent_config(
        self,
        agent_type: str,
        config_updates: dict[str, Any],
        updated_by: str,
        environment: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update agent configuration in database with versioning."""
        if environment is None:
            environment = self.settings.environment

        try:
            async with get_database_session() as session:
                # Get current configuration
                current_config = await self._get_agent_config_from_db(
                    agent_type, environment
                )

                if not current_config:
                    # Create new configuration profile
                    await self._create_new_config_profile(
                        session,
                        agent_type,
                        config_updates,
                        updated_by,
                        environment,
                        description,
                    )
                else:
                    # Update existing configuration
                    await self._update_existing_config_profile(
                        session,
                        agent_type,
                        config_updates,
                        updated_by,
                        environment,
                        description,
                    )

                await session.commit()

                # Clear cache
                cache_key_str = generate_cache_key(
                    "agent_config", f"{agent_type}:{environment}"
                )
                await delete_cache(cache_key_str)

                # Get updated configuration
                updated_config = await self.get_agent_config(agent_type, environment)

                logger.info(
                    f"Agent config updated for {agent_type} in {environment} "
                    f"by {updated_by}"
                )
                return updated_config

        except Exception as e:
            logger.error(f"Error updating agent config: {e}")
            raise

    async def _create_new_config_profile(
        self,
        session: AsyncSession,
        agent_type: str,
        config_updates: dict[str, Any],
        updated_by: str,
        environment: str,
        description: str | None,
    ) -> UUID:
        """Create a new configuration profile."""
        # Get defaults from settings
        defaults = self.settings.get_agent_config(agent_type)

        # Merge with updates
        final_config = {**defaults, **config_updates}

        # Insert new profile
        result = await session.execute(
            text("""
                INSERT INTO configuration_profiles (
                    agent_type, temperature, max_tokens, top_p, timeout_seconds, 
                    model, environment, description, created_by, updated_by
                ) VALUES (
                    :agent_type, :temperature, :max_tokens, :top_p, :timeout_seconds,
                    :model, :environment, :description, :created_by, :updated_by
                ) RETURNING id
            """),
            {
                "agent_type": agent_type,
                "temperature": final_config["temperature"],
                "max_tokens": final_config["max_tokens"],
                "top_p": final_config["top_p"],
                "timeout_seconds": final_config["timeout_seconds"],
                "model": final_config["model"],
                "environment": environment,
                "description": description,
                "created_by": updated_by,
                "updated_by": updated_by,
            },
        )

        config_id = result.fetchone()[0]
        return config_id

    async def _update_existing_config_profile(
        self,
        session: AsyncSession,
        agent_type: str,
        config_updates: dict[str, Any],
        updated_by: str,
        environment: str,
        description: str | None,
    ) -> UUID:
        """Update existing configuration profile."""
        # Build update clauses
        update_fields = []
        params = {
            "agent_type": agent_type,
            "environment": environment,
            "updated_by": updated_by,
        }

        for field, value in config_updates.items():
            if field in [
                "temperature",
                "max_tokens",
                "top_p",
                "timeout_seconds",
                "model",
            ]:
                update_fields.append(f"{field} = :{field}")
                params[field] = value

        if description:
            update_fields.append("description = :description")
            params["description"] = description

        if not update_fields:
            raise ValueError("No valid configuration fields to update")

        # Execute update
        query = f"""
            UPDATE configuration_profiles 
            SET {", ".join(update_fields)}, updated_by = :updated_by, updated_at = NOW()
            WHERE agent_type = :agent_type 
              AND environment = :environment 
              AND is_active = true
            RETURNING id
        """

        result = await session.execute(text(query), params)
        row = result.fetchone()

        if not row:
            raise ValueError(
                f"No active configuration found for {agent_type} in {environment}"
            )

        return row[0]

    async def get_configuration_versions(
        self, agent_type: str, environment: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get configuration version history."""
        if environment is None:
            environment = self.settings.environment

        async with get_database_session() as session:
            result = await session.execute(
                text("""
                    SELECT cv.version_id, cv.config_snapshot, cv.description,
                           cv.created_at, cv.created_by, cv.is_current
                    FROM configuration_versions cv
                    JOIN configuration_profiles cp 
                        ON cv.configuration_profile_id = cp.id
                    WHERE cp.agent_type = :agent_type 
                      AND cp.environment = :environment
                    ORDER BY cv.created_at DESC
                    LIMIT :limit
                """),
                {"agent_type": agent_type, "environment": environment, "limit": limit},
            )

            versions = []
            for row in result:
                versions.append(
                    {
                        "version_id": row.version_id,
                        "configuration": row.config_snapshot,
                        "description": row.description,
                        "created_at": row.created_at,
                        "created_by": row.created_by,
                        "is_current": row.is_current,
                    }
                )

            return versions

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

        try:
            async with get_database_session() as session:
                # Get version configuration
                result = await session.execute(
                    text("""
                        SELECT cv.config_snapshot, cp.id as profile_id
                        FROM configuration_versions cv
                        JOIN configuration_profiles cp 
                            ON cv.configuration_profile_id = cp.id
                        WHERE cv.version_id = :version_id
                          AND cp.agent_type = :agent_type
                          AND cp.environment = :environment
                    """),
                    {
                        "version_id": version_id,
                        "agent_type": agent_type,
                        "environment": environment,
                    },
                )

                row = result.fetchone()
                if not row:
                    raise ValueError(f"Version {version_id} not found for {agent_type}")

                config_snapshot = row.config_snapshot
                profile_id = row.profile_id

                # Update configuration profile with snapshot data
                await session.execute(
                    text("""
                        UPDATE configuration_profiles
                        SET temperature = :temperature,
                            max_tokens = :max_tokens,
                            top_p = :top_p,
                            timeout_seconds = :timeout_seconds,
                            model = :model,
                            description = :description,
                            updated_by = :updated_by,
                            updated_at = NOW()
                        WHERE id = :profile_id
                    """),
                    {
                        "temperature": config_snapshot["temperature"],
                        "max_tokens": config_snapshot["max_tokens"],
                        "top_p": config_snapshot["top_p"],
                        "timeout_seconds": config_snapshot["timeout_seconds"],
                        "model": config_snapshot["model"],
                        "description": f"Rolled back to version {version_id}",
                        "updated_by": rolled_back_by,
                        "profile_id": profile_id,
                    },
                )

                await session.commit()

                # Clear cache
                cache_key_str = generate_cache_key(
                    "agent_config", f"{agent_type}:{environment}"
                )
                await delete_cache(cache_key_str)

                logger.info(
                    f"Configuration rolled back to {version_id} for {agent_type} "
                    f"by {rolled_back_by}"
                )

                # Return updated configuration
                return await self.get_agent_config(agent_type, environment)

        except Exception as e:
            logger.error(f"Error rolling back configuration: {e}")
            raise

    async def get_all_agent_configs(
        self, environment: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """Get all agent configurations for an environment."""
        if environment is None:
            environment = self.settings.environment

        agent_types = ["budget_agent", "destination_research_agent", "itinerary_agent"]
        configs = {}

        for agent_type in agent_types:
            try:
                configs[agent_type] = await self.get_agent_config(
                    agent_type, environment
                )
            except Exception as e:
                logger.error(f"Error getting config for {agent_type}: {e}")
                # Use fallback
                configs[agent_type] = self.settings.get_agent_config(agent_type)

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

        try:
            async with get_database_session() as session:
                # Get configuration profile ID
                result = await session.execute(
                    text("""
                        SELECT id FROM configuration_profiles
                        WHERE agent_type = :agent_type 
                          AND environment = :environment 
                          AND is_active = true
                    """),
                    {"agent_type": agent_type, "environment": environment},
                )

                row = result.fetchone()
                if not row:
                    logger.warning(
                        f"No configuration profile found for metrics recording: "
                        f"{agent_type}"
                    )
                    return

                profile_id = row[0]

                # Insert performance metrics
                await session.execute(
                    text("""
                        INSERT INTO configuration_performance_metrics (
                            configuration_profile_id, average_response_time, 
                            success_rate,
                            error_rate, token_usage, cost_estimate, sample_size,
                            measurement_period_start, measurement_period_end
                        ) VALUES (
                            :profile_id, :avg_response_time, :success_rate, 
                            :error_rate, :token_usage, :cost_estimate, 
                            :sample_size, :period_start, :period_end
                        )
                    """),
                    {
                        "profile_id": profile_id,
                        "avg_response_time": metrics.get("average_response_time", 0.0),
                        "success_rate": metrics.get("success_rate", 1.0),
                        "error_rate": metrics.get("error_rate", 0.0),
                        "token_usage": json.dumps(metrics.get("token_usage", {})),
                        "cost_estimate": metrics.get("cost_estimate", 0.0),
                        "sample_size": metrics.get("sample_size", 1),
                        "period_start": metrics.get("period_start", datetime.now(UTC)),
                        "period_end": metrics.get("period_end", datetime.now(UTC)),
                    },
                )

                await session.commit()

                logger.debug(f"Performance metrics recorded for {agent_type}")

        except Exception as e:
            logger.error(f"Error recording performance metrics: {e}")


# Global service instance
_configuration_service: ConfigurationService | None = None


def get_configuration_service() -> ConfigurationService:
    """Get the global configuration service instance."""
    global _configuration_service
    if _configuration_service is None:
        _configuration_service = ConfigurationService()
    return _configuration_service
