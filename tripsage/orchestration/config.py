"""
Configuration management for LangGraph orchestration.

This module provides configuration classes and utilities for managing
the LangGraph-based orchestration system settings.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from tripsage.config.app_settings import settings


class CheckpointStorage(Enum):
    """Available checkpoint storage backends."""

    MEMORY = "memory"
    POSTGRES = "postgres"
    REDIS = "redis"


@dataclass
class LangGraphConfig:
    """
    Configuration for LangGraph orchestration system.

    This class encapsulates all configuration options for the LangGraph-based
    agent orchestration including models, checkpointing, and performance settings.
    """

    # Core LLM settings
    default_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096

    # Router-specific settings
    router_model: str = "gpt-4o-mini"
    router_temperature: float = 0.1

    # Checkpointing and state management
    checkpoint_storage: CheckpointStorage = CheckpointStorage.MEMORY
    checkpoint_connection_string: Optional[str] = None

    # Error handling and resilience
    max_retries: int = 3
    retry_delay: float = 1.0
    escalation_threshold: int = 5
    timeout_seconds: int = 30

    # Monitoring and observability
    enable_langsmith: bool = True
    langsmith_project: str = "tripsage-langgraph"
    langsmith_api_key: Optional[str] = None

    # Performance optimization
    parallel_execution: bool = True
    max_concurrent_tools: int = 5
    tool_timeout_seconds: int = 10

    # Memory and persistence
    session_timeout_hours: int = 24
    max_message_history: int = 100
    enable_conversation_memory: bool = True

    # Feature flags
    enable_human_in_loop: bool = False
    enable_advanced_routing: bool = True
    enable_memory_updates: bool = True
    enable_error_recovery: bool = True

    @classmethod
    def from_environment(cls) -> "LangGraphConfig":
        """
        Load configuration from environment variables.

        Returns:
            LangGraphConfig instance with values from environment
        """
        return cls(
            # Core LLM settings
            default_model=os.getenv("LANGGRAPH_DEFAULT_MODEL", "gpt-4o"),
            temperature=float(os.getenv("LANGGRAPH_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LANGGRAPH_MAX_TOKENS", "4096")),
            # Router settings
            router_model=os.getenv("LANGGRAPH_ROUTER_MODEL", "gpt-4o-mini"),
            router_temperature=float(os.getenv("LANGGRAPH_ROUTER_TEMPERATURE", "0.1")),
            # Checkpointing
            checkpoint_storage=CheckpointStorage(
                os.getenv("LANGGRAPH_CHECKPOINT_STORAGE", "memory")
            ),
            checkpoint_connection_string=os.getenv("LANGGRAPH_CHECKPOINT_CONNECTION"),
            # Error handling
            max_retries=int(os.getenv("LANGGRAPH_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("LANGGRAPH_RETRY_DELAY", "1.0")),
            escalation_threshold=int(os.getenv("LANGGRAPH_ESCALATION_THRESHOLD", "5")),
            timeout_seconds=int(os.getenv("LANGGRAPH_TIMEOUT_SECONDS", "30")),
            # Monitoring
            enable_langsmith=os.getenv("LANGGRAPH_ENABLE_LANGSMITH", "true").lower()
            == "true",
            langsmith_project=os.getenv("LANGSMITH_PROJECT", "tripsage-langgraph"),
            langsmith_api_key=os.getenv("LANGSMITH_API_KEY"),
            # Performance
            parallel_execution=os.getenv("LANGGRAPH_PARALLEL_EXECUTION", "true").lower()
            == "true",
            max_concurrent_tools=int(os.getenv("LANGGRAPH_MAX_CONCURRENT_TOOLS", "5")),
            tool_timeout_seconds=int(os.getenv("LANGGRAPH_TOOL_TIMEOUT_SECONDS", "10")),
            # Memory
            session_timeout_hours=int(
                os.getenv("LANGGRAPH_SESSION_TIMEOUT_HOURS", "24")
            ),
            max_message_history=int(os.getenv("LANGGRAPH_MAX_MESSAGE_HISTORY", "100")),
            enable_conversation_memory=os.getenv(
                "LANGGRAPH_ENABLE_CONVERSATION_MEMORY", "true"
            ).lower()
            == "true",
            # Feature flags
            enable_human_in_loop=os.getenv("LANGGRAPH_ENABLE_HITL", "false").lower()
            == "true",
            enable_advanced_routing=os.getenv(
                "LANGGRAPH_ENABLE_ADVANCED_ROUTING", "true"
            ).lower()
            == "true",
            enable_memory_updates=os.getenv(
                "LANGGRAPH_ENABLE_MEMORY_UPDATES", "true"
            ).lower()
            == "true",
            enable_error_recovery=os.getenv(
                "LANGGRAPH_ENABLE_ERROR_RECOVERY", "true"
            ).lower()
            == "true",
        )

    @classmethod
    def from_app_settings(cls) -> "LangGraphConfig":
        """
        Load configuration from existing app settings.

        Returns:
            LangGraphConfig instance derived from app settings
        """
        return cls(
            # Use existing agent settings
            default_model=settings.agent.model_name,
            temperature=settings.agent.temperature,
            max_tokens=settings.agent.max_tokens,
            # Use OpenAI API key from settings
            langsmith_api_key=settings.openai_api_key.get_secret_value(),
            # Database connection for checkpointing
            checkpoint_storage=CheckpointStorage.POSTGRES
            if settings.database.supabase_url
            else CheckpointStorage.MEMORY,
            checkpoint_connection_string=settings.database.supabase_url
            if settings.database.supabase_url
            else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "default_model": self.default_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "router_model": self.router_model,
            "router_temperature": self.router_temperature,
            "checkpoint_storage": self.checkpoint_storage.value,
            "checkpoint_connection_string": self.checkpoint_connection_string,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "escalation_threshold": self.escalation_threshold,
            "timeout_seconds": self.timeout_seconds,
            "enable_langsmith": self.enable_langsmith,
            "langsmith_project": self.langsmith_project,
            "parallel_execution": self.parallel_execution,
            "max_concurrent_tools": self.max_concurrent_tools,
            "tool_timeout_seconds": self.tool_timeout_seconds,
            "session_timeout_hours": self.session_timeout_hours,
            "max_message_history": self.max_message_history,
            "enable_conversation_memory": self.enable_conversation_memory,
            "enable_human_in_loop": self.enable_human_in_loop,
            "enable_advanced_routing": self.enable_advanced_routing,
            "enable_memory_updates": self.enable_memory_updates,
            "enable_error_recovery": self.enable_error_recovery,
        }

    def validate(self) -> None:
        """
        Validate configuration settings.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")

        if self.max_tokens < 1:
            raise ValueError("Max tokens must be positive")

        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")

        if self.retry_delay < 0:
            raise ValueError("Retry delay must be non-negative")

        if self.escalation_threshold < 1:
            raise ValueError("Escalation threshold must be positive")

        if self.timeout_seconds < 1:
            raise ValueError("Timeout must be positive")

        if self.max_concurrent_tools < 1:
            raise ValueError("Max concurrent tools must be positive")

        if self.session_timeout_hours < 1:
            raise ValueError("Session timeout must be positive")

        if self.max_message_history < 1:
            raise ValueError("Max message history must be positive")


def get_default_config() -> LangGraphConfig:
    """
    Get default configuration based on environment and app settings.

    Returns:
        Default LangGraphConfig instance
    """
    # Try to load from environment first, fallback to app settings
    try:
        return LangGraphConfig.from_environment()
    except (ValueError, KeyError):
        return LangGraphConfig.from_app_settings()
