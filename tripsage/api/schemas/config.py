"""
Configuration management schemas for API endpoints.

Defines Pydantic v2 models for configuration validation and serialization
following 2025 best practices with comprehensive type safety, computed fields,
and advanced validation patterns.
"""

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)
from typing_extensions import Self

# Type aliases for better type safety
ModelName = Annotated[
    str,
    StringConstraints(pattern=r"^(gpt-4|gpt-4-turbo|gpt-4o|gpt-4o-mini|gpt-3.5-turbo|claude-3-sonnet|claude-3-haiku)$"),
]

VersionId = Annotated[str, StringConstraints(pattern=r"^v\d+_[a-f0-9]{8}$", min_length=10, max_length=20)]

DescriptionText = Annotated[str, StringConstraints(max_length=500, strip_whitespace=True)]


class AgentType(str, Enum):
    """Enumeration of available agent types with metadata."""

    BUDGET_AGENT = "budget_agent"
    DESTINATION_RESEARCH_AGENT = "destination_research_agent"
    ITINERARY_AGENT = "itinerary_agent"

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return {
            "budget_agent": "Budget Optimization Agent",
            "destination_research_agent": "Destination Research Agent",
            "itinerary_agent": "Itinerary Planning Agent",
        }[self.value]

    @property
    def recommended_temperature(self) -> float:
        """Get recommended temperature for this agent type."""
        return {
            "budget_agent": 0.2,  # Low creativity for accuracy
            "destination_research_agent": 0.5,  # Moderate for research
            "itinerary_agent": 0.4,  # Structured creativity
        }[self.value]


class ConfigurationScope(str, Enum):
    """Enumeration of configuration scopes."""

    GLOBAL = "global"
    ENVIRONMENT = "environment"
    AGENT_SPECIFIC = "agent_specific"
    USER_OVERRIDE = "user_override"


class BaseConfigModel(BaseModel):
    """Base configuration model with common settings."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        validate_default=True,
        extra="forbid",
        frozen=False,
        use_enum_values=True,
        populate_by_name=True,
    )


class AgentConfigRequest(BaseConfigModel):
    """Request schema for agent configuration updates with advanced validation."""

    temperature: Optional[
        Annotated[
            float,
            Field(
                ge=0.0,
                le=2.0,
                description="Controls randomness in responses (0.0=deterministic, 2.0=very creative)",
            ),
        ]
    ] = None

    max_tokens: Optional[
        Annotated[
            int,
            Field(
                ge=1,
                le=8000,
                description="Maximum tokens in response (affects cost and response length)",
            ),
        ]
    ] = None

    top_p: Optional[
        Annotated[
            float,
            Field(
                ge=0.0,
                le=1.0,
                description="Nucleus sampling parameter (0.1=focused, 1.0=diverse)",
            ),
        ]
    ] = None

    timeout_seconds: Optional[Annotated[int, Field(ge=5, le=300, description="Request timeout in seconds")]] = None

    model: Optional[ModelName] = Field(None, description="AI model to use for this agent")

    description: Optional[DescriptionText] = Field(None, description="Description of configuration changes")

    @field_validator("temperature")
    @classmethod
    def validate_temperature_precision(cls, v: Optional[float]) -> Optional[float]:
        """Validate temperature with precision control."""
        if v is not None:
            # Round to 2 decimal places for consistency
            return round(v, 2)
        return v

    @model_validator(mode="after")
    def validate_model_compatibility(self) -> Self:
        """Cross-field validation for model-specific constraints."""
        if self.model and self.temperature is not None:
            # GPT-3.5 models work best with lower temperature
            if "gpt-3.5" in self.model and self.temperature > 1.5:
                raise ValueError("GPT-3.5 models work best with temperature ≤ 1.5 for optimal performance")

            # Claude models have different optimal ranges
            if "claude" in self.model and self.temperature > 1.0:
                raise ValueError("Claude models work best with temperature ≤ 1.0")

        if self.model and self.max_tokens is not None:
            # Model-specific token limits
            model_limits = {
                "gpt-3.5-turbo": 4096,
                "gpt-4": 8192,
                "gpt-4-turbo": 8192,
                "gpt-4o": 8192,
                "claude-3-haiku": 4096,
                "claude-3-sonnet": 8192,
            }

            max_limit = model_limits.get(self.model, 8000)
            if self.max_tokens > max_limit:
                raise ValueError(f"Model {self.model} supports maximum {max_limit} tokens")

        return self

    @computed_field
    @property
    def configuration_hash(self) -> str:
        """Generate a hash of the configuration for change detection."""
        config_str = f"{self.temperature}_{self.max_tokens}_{self.top_p}_{self.timeout_seconds}_{self.model}"
        # Using MD5 for non-security purpose (configuration change detection)
        # Python 3.9+ usedforsecurity=False parameter indicates this is not for security
        return hashlib.md5(config_str.encode(), usedforsecurity=False).hexdigest()[:8]

    def get_changed_fields(self, other: "AgentConfigRequest") -> List[str]:
        """Get list of fields that changed compared to another configuration."""
        changed = []
        for field_name in self.model_fields:
            if getattr(self, field_name) != getattr(other, field_name):
                changed.append(field_name)
        return changed


class AgentConfigResponse(BaseConfigModel):
    """Response schema for agent configuration with computed metrics."""

    agent_type: AgentType
    temperature: Annotated[float, Field(ge=0.0, le=2.0)]
    max_tokens: Annotated[int, Field(ge=1, le=8000)]
    top_p: Annotated[float, Field(ge=0.0, le=1.0)]
    timeout_seconds: Annotated[int, Field(ge=5, le=300)]
    model: ModelName
    scope: ConfigurationScope
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None
    description: Optional[DescriptionText] = None
    is_active: bool = True

    @computed_field
    @property
    def estimated_cost_per_1k_tokens(self) -> Decimal:
        """Calculate estimated cost per 1000 tokens for this configuration."""
        # Current pricing as of 2025 (subject to change)
        model_costs = {
            "gpt-4": Decimal("0.030"),
            "gpt-4-turbo": Decimal("0.010"),
            "gpt-4o": Decimal("0.005"),
            "gpt-4o-mini": Decimal("0.002"),
            "gpt-3.5-turbo": Decimal("0.0015"),
            "claude-3-sonnet": Decimal("0.015"),
            "claude-3-haiku": Decimal("0.0025"),
        }
        return model_costs.get(self.model, Decimal("0.010"))

    @computed_field
    @property
    def creativity_level(self) -> str:
        """Categorize the creativity level based on temperature."""
        if self.temperature <= 0.3:
            return "Conservative (Focused, Deterministic)"
        elif self.temperature <= 0.7:
            return "Balanced (Moderate Creativity)"
        elif self.temperature <= 1.2:
            return "Creative (High Variation)"
        else:
            return "Very Creative (Maximum Randomness)"

    @computed_field
    @property
    def response_size_category(self) -> str:
        """Categorize response size based on max_tokens."""
        if self.max_tokens <= 500:
            return "Short (Concise responses)"
        elif self.max_tokens <= 1500:
            return "Medium (Detailed responses)"
        elif self.max_tokens <= 4000:
            return "Long (Comprehensive responses)"
        else:
            return "Very Long (Extensive responses)"

    @computed_field
    @property
    def performance_tier(self) -> str:
        """Determine performance tier based on model and settings."""
        if self.model in ["gpt-4o", "gpt-4-turbo"]:
            return "High Performance"
        elif self.model in ["gpt-4", "claude-3-sonnet"]:
            return "Premium"
        elif self.model in ["gpt-4o-mini", "gpt-3.5-turbo", "claude-3-haiku"]:
            return "Efficient"
        else:
            return "Standard"

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format with timezone."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    def is_optimal_for_agent_type(self) -> bool:
        """Check if configuration is optimal for the agent type."""
        recommended_temp = self.agent_type.recommended_temperature
        temp_diff = abs(self.temperature - recommended_temp)
        return temp_diff <= 0.1  # Within 10% of recommended

    def get_optimization_suggestions(self) -> List[str]:
        """Get suggestions for optimizing this configuration."""
        suggestions = []

        recommended_temp = self.agent_type.recommended_temperature
        if abs(self.temperature - recommended_temp) > 0.2:
            suggestions.append(
                f"Consider temperature {recommended_temp} for optimal {self.agent_type.display_name} performance"
            )

        if self.agent_type == AgentType.BUDGET_AGENT and self.temperature > 0.5:
            suggestions.append("Budget agents work best with lower temperature (≤0.3) for consistent calculations")

        if self.max_tokens > 2000 and self.agent_type == AgentType.BUDGET_AGENT:
            suggestions.append(
                "Budget responses are typically concise; consider reducing max_tokens for cost efficiency"
            )

        return suggestions


class ConfigurationVersion(BaseConfigModel):
    """Schema for configuration version history with enhanced metadata."""

    version_id: VersionId = Field(description="Unique version identifier")
    agent_type: AgentType
    configuration: Dict[str, Any] = Field(description="Configuration snapshot")
    scope: ConfigurationScope
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    description: Optional[DescriptionText] = None
    is_current: bool = False

    @computed_field
    @property
    def age_in_days(self) -> int:
        """Calculate age of this version in days."""
        now = datetime.now(timezone.utc)
        if self.created_at.tzinfo is None:
            created_at = self.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = self.created_at
        return (now - created_at).days

    @computed_field
    @property
    def is_recent(self) -> bool:
        """Check if this version was created recently (within 7 days)."""
        return self.age_in_days <= 7


class ConfigurationDiff(BaseConfigModel):
    """Schema for configuration differences."""

    field: str
    old_value: Union[str, int, float, bool, None]
    new_value: Union[str, int, float, bool, None]
    change_type: str = Field(description="added, modified, or removed")

    @computed_field
    @property
    def impact_level(self) -> str:
        """Assess the impact level of this change."""
        critical_fields = ["model", "temperature"]
        if self.field in critical_fields:
            return "High"
        elif self.field in ["max_tokens", "timeout_seconds"]:
            return "Medium"
        else:
            return "Low"


class PerformanceMetrics(BaseConfigModel):
    """Schema for configuration performance metrics with trends."""

    agent_type: AgentType
    average_response_time: Annotated[float, Field(ge=0.0, description="Average response time in seconds")]
    success_rate: Annotated[float, Field(ge=0.0, le=1.0, description="Success rate (0.0-1.0)")]
    error_rate: Annotated[float, Field(ge=0.0, le=1.0, description="Error rate (0.0-1.0)")]
    token_usage: Dict[str, int] = Field(description="Token usage statistics")
    cost_estimate: Annotated[Decimal, Field(ge=0, description="Estimated cost in USD")]
    measured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sample_size: Annotated[int, Field(ge=1, description="Number of requests measured")]

    @computed_field
    @property
    def performance_grade(self) -> str:
        """Calculate overall performance grade."""
        if self.success_rate >= 0.95 and self.average_response_time <= 2.0:
            return "A+ (Excellent)"
        elif self.success_rate >= 0.90 and self.average_response_time <= 5.0:
            return "A (Very Good)"
        elif self.success_rate >= 0.85 and self.average_response_time <= 10.0:
            return "B (Good)"
        elif self.success_rate >= 0.75:
            return "C (Fair)"
        else:
            return "D (Needs Improvement)"

    @computed_field
    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens processed per second."""
        total_tokens = self.token_usage.get("total", 0)
        if self.average_response_time > 0:
            return total_tokens / self.average_response_time
        return 0.0


class ConfigurationRecommendation(BaseConfigModel):
    """Schema for AI-driven configuration optimization recommendations."""

    agent_type: AgentType
    current_config: Dict[str, Any]
    recommended_config: Dict[str, Any]
    reasoning: str
    expected_improvement: str
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)]
    metrics_basis: PerformanceMetrics
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def recommendation_priority(self) -> str:
        """Determine priority level of this recommendation."""
        if self.confidence_score >= 0.8:
            return "High Priority"
        elif self.confidence_score >= 0.6:
            return "Medium Priority"
        else:
            return "Low Priority"

    @model_validator(mode="after")
    def validate_recommendation_logic(self) -> Self:
        """Validate that recommendations make logical sense."""
        current_temp = self.current_config.get("temperature", 0.7)
        recommended_temp = self.recommended_config.get("temperature", 0.7)

        # Ensure temperature recommendations are within reasonable bounds
        if abs(recommended_temp - current_temp) > 0.5:
            if self.confidence_score > 0.9:
                raise ValueError("High confidence recommendations should not suggest dramatic temperature changes")

        return self


class WebSocketConfigMessage(BaseConfigModel):
    """Schema for real-time WebSocket configuration messages."""

    type: str = Field(description="Message type (update, rollback, validation, etc.)")
    agent_type: Optional[AgentType] = None
    configuration: Optional[Dict[str, Any]] = None
    version_id: Optional[VersionId] = None
    updated_by: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: Optional[str] = None

    @model_validator(mode="after")
    def validate_message_consistency(self) -> Self:
        """Validate that message fields are consistent with message type."""
        if self.type == "update" and not self.configuration:
            raise ValueError("Update messages must include configuration data")

        if self.type == "rollback" and not self.version_id:
            raise ValueError("Rollback messages must include version_id")

        return self


class ConfigurationExport(BaseConfigModel):
    """Schema for configuration export with metadata."""

    export_id: str
    environment: str
    agent_configurations: Dict[str, AgentConfigResponse]
    feature_flags: Dict[str, bool]
    global_defaults: Dict[str, Any]
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    exported_by: str
    format: str = "json"

    @computed_field
    @property
    def total_configurations(self) -> int:
        """Count total number of configurations exported."""
        return len(self.agent_configurations)

    @computed_field
    @property
    def export_size_estimate_kb(self) -> float:
        """Estimate export file size in KB."""
        # Rough estimation based on typical configuration sizes
        return len(self.model_dump_json().encode()) / 1024


class ConfigurationImport(BaseConfigModel):
    """Schema for configuration import with validation."""

    source_environment: str
    agent_configurations: Dict[str, AgentConfigRequest]
    feature_flags: Optional[Dict[str, bool]] = None
    global_defaults: Optional[Dict[str, Any]] = None
    description: Optional[DescriptionText] = None
    dry_run: bool = False

    @model_validator(mode="after")
    def validate_import_data(self) -> Self:
        """Validate import data integrity."""
        if not self.agent_configurations:
            raise ValueError("Import must contain at least one agent configuration")

        # Validate agent types
        valid_agent_types = [e.value for e in AgentType]
        for agent_type in self.agent_configurations.keys():
            if agent_type not in valid_agent_types:
                raise ValueError(f"Invalid agent type: {agent_type}")

        return self


class ConfigurationValidationError(BaseConfigModel):
    """Schema for detailed configuration validation errors."""

    field: str
    error: str
    current_value: Union[str, int, float, bool, None]
    suggested_value: Union[str, int, float, bool, None] = None
    severity: str = Field(default="error", description="error, warning, or info")

    @computed_field
    @property
    def error_code(self) -> str:
        """Generate standardized error code."""
        field_code = self.field.upper().replace("_", "")
        severity_code = self.severity.upper()[:1]
        return f"CFG{severity_code}{field_code}"


class ConfigurationValidationResponse(BaseConfigModel):
    """Response schema for comprehensive configuration validation."""

    is_valid: bool
    errors: List[ConfigurationValidationError] = []
    warnings: List[ConfigurationValidationError] = []
    suggestions: List[str] = []

    @computed_field
    @property
    def validation_summary(self) -> str:
        """Generate human-readable validation summary."""
        if self.is_valid:
            return f"✅ Valid configuration ({len(self.warnings)} warnings)"
        else:
            return f"❌ Invalid configuration ({len(self.errors)} errors, {len(self.warnings)} warnings)"


class ConfigurationImportResult(BaseConfigModel):
    """Schema for configuration import operation results."""

    import_id: str
    success: bool
    imported_configurations: List[str] = []
    failed_configurations: List[str] = []
    validation_errors: List[ConfigurationValidationError] = []
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    imported_by: str

    @computed_field
    @property
    def success_rate(self) -> float:
        """Calculate import success rate."""
        total = len(self.imported_configurations) + len(self.failed_configurations)
        if total == 0:
            return 0.0
        return len(self.imported_configurations) / total

    @computed_field
    @property
    def import_summary(self) -> str:
        """Generate import operation summary."""
        total = len(self.imported_configurations) + len(self.failed_configurations)
        success_count = len(self.imported_configurations)
        return f"Imported {success_count}/{total} configurations ({self.success_rate:.1%} success rate)"
