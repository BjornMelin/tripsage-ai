/**
 * @fileoverview Zod validation schemas for configuration management.
 *
 * Provides runtime type safety and validation for all configuration
 * data in the TripSage platform. Includes schemas for agent configurations,
 * performance metrics, version control, and API request/response validation
 * ensuring consistency between frontend and backend APIs.
 */

import { z } from "zod";

/**
 * Zod schema for agent type enumeration.
 *
 * Defines the supported AI agent types in the TripSage platform, matching
 * backend agent classifications for consistent configuration management.
 */
export const AgentTypeEnum = z.enum([
  "budget_agent",
  "destination_research_agent",
  "itinerary_agent",
] as const);

/** TypeScript type for agent types inferred from AgentTypeEnum schema. */
export type AgentType = z.infer<typeof AgentTypeEnum>;

/**
 * Zod schema for configuration scope enumeration.
 *
 * Defines the hierarchical scopes for configuration settings, allowing
 * global defaults, environment overrides, agent-specific settings, and
 * user-level customizations.
 */
export const ConfigurationScopeEnum = z.enum([
  "global",
  "environment",
  "agent_specific",
  "user_override",
] as const);

/** TypeScript type for configuration scopes inferred from ConfigurationScopeEnum schema. */
export type ConfigurationScope = z.infer<typeof ConfigurationScopeEnum>;

/**
 * Zod schema for supported AI model names.
 *
 * Validates model names against the list of supported AI models including
 * OpenAI GPT series and Anthropic Claude models for configuration validation.
 */
export const ModelNameSchema = z.enum([
  "gpt-4",
  "gpt-4-turbo",
  "gpt-4o",
  "gpt-4o-mini",
  "gpt-5",
  "gpt-5-mini",
  "gpt-5-nano",
  "claude-4.5-sonnet",
  "claude-4.5-haiku",
] as const);

/** TypeScript type for model names inferred from ModelNameSchema. */
export type ModelName = z.infer<typeof ModelNameSchema>;

/**
 * Zod schema for version ID validation.
 *
 * Validates version identifiers following the format v{timestamp}_{hash}
 * for consistent versioning across configuration changes and rollbacks.
 */
export const VersionIdSchema = z
  .string()
  .regex(/^v\d+_[a-f0-9]{8}$/, "Version ID must match format: v{timestamp}_{hash}");

/** TypeScript type for version IDs inferred from VersionIdSchema. */
export type VersionId = z.infer<typeof VersionIdSchema>;

/**
 * Zod schema for agent configuration request validation.
 *
 * Validates incoming configuration requests for AI agents with cross-field
 * validation ensuring model compatibility and parameter constraints. Includes
 * temperature, token limits, model selection, and timeout settings with
 * intelligent validation based on selected AI models.
 */
export const AgentConfigRequestSchema = z
  .object({
    temperature: z
      .number()
      .min(0.0, "Temperature must be at least 0.0")
      .max(2.0, "Temperature must be at most 2.0")
      .multipleOf(0.01, "Temperature must have at most 2 decimal places")
      .optional(),

    max_tokens: z
      .number()
      .int("Max tokens must be an integer")
      .min(1, "Max tokens must be at least 1")
      .max(8000, "Max tokens must be at most 8000")
      .optional(),

    top_p: z
      .number()
      .min(0.0, "Top-p must be at least 0.0")
      .max(1.0, "Top-p must be at most 1.0")
      .multipleOf(0.01, "Top-p must have at most 2 decimal places")
      .optional(),

    timeout_seconds: z
      .number()
      .int("Timeout must be an integer")
      .min(5, "Timeout must be at least 5 seconds")
      .max(300, "Timeout must be at most 300 seconds")
      .optional(),

    model: ModelNameSchema.optional(),

    description: z
      .string()
      .max(500, "Description must be at most 500 characters")
      .trim()
      .optional()
      .nullable(),
  })
  .refine(
    (data) => {
      // Cross-field validation for model compatibility
      if (data.model && data.temperature !== undefined) {
        // GPT-3.5 models work best with lower temperature
        if (data.model.includes("gpt-3.5") && data.temperature > 1.5) {
          return false;
        }

        // Claude models have different optimal ranges
        if (data.model.includes("claude") && data.temperature > 1.0) {
          return false;
        }
      }

      if (data.model && data.max_tokens !== undefined) {
        // Model-specific token limits
        const modelLimits: Record<string, number> = {
          "gpt-3.5-turbo": 4096,
          "gpt-4": 8192,
          "gpt-4-turbo": 8192,
          "gpt-4o": 8192,
          "claude-3-haiku": 4096,
          "claude-3-sonnet": 8192,
        };

        const maxLimit = modelLimits[data.model] || 8000;
        if (data.max_tokens > maxLimit) {
          return false;
        }
      }

      return true;
    },
    {
      message: "Configuration is not compatible with selected model",
      path: ["model"],
    }
  );

/** TypeScript type for agent configuration requests inferred from AgentConfigRequestSchema. */
export type AgentConfigRequest = z.infer<typeof AgentConfigRequestSchema>;

/**
 * Zod schema for agent configuration response validation.
 *
 * Validates complete agent configuration responses from the backend including
 * computed fields like cost estimates, performance metrics, and metadata.
 * Ensures all required fields are present and properly typed.
 */
export const AgentConfigResponseSchema = z.object({
  agent_type: AgentTypeEnum,
  temperature: z.number().min(0.0).max(2.0),
  max_tokens: z.number().int().min(1).max(8000),
  top_p: z.number().min(0.0).max(1.0),
  timeout_seconds: z.number().int().min(5).max(300),
  model: ModelNameSchema,
  scope: ConfigurationScopeEnum,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  updated_by: z.string().nullable().optional(),
  description: z.string().max(500).nullable().optional(),
  is_active: z.boolean().default(true),

  // Computed fields from backend
  estimated_cost_per_1k_tokens: z.string().optional(), // Decimal as string
  creativity_level: z.string().optional(),
  response_size_category: z.string().optional(),
  performance_tier: z.string().optional(),
});

/** TypeScript type for agent configuration responses inferred from AgentConfigResponseSchema. */
export type AgentConfigResponse = z.infer<typeof AgentConfigResponseSchema>;

/**
 * Zod schema for configuration version validation.
 *
 * Validates configuration version objects for version control and rollback
 * functionality. Tracks changes over time with metadata about who created
 * versions and when they were created.
 */
export const ConfigurationVersionSchema = z.object({
  version_id: VersionIdSchema,
  agent_type: AgentTypeEnum,
  configuration: z.record(z.string(), z.any()),
  scope: ConfigurationScopeEnum,
  created_at: z.string().datetime(),
  created_by: z.string(),
  description: z.string().max(500).nullable().optional(),
  is_current: z.boolean().default(false),

  // Computed fields
  age_in_days: z.number().int().min(0).optional(),
  is_recent: z.boolean().optional(),
});

/** TypeScript type for configuration versions inferred from ConfigurationVersionSchema. */
export type ConfigurationVersion = z.infer<typeof ConfigurationVersionSchema>;

/**
 * Zod schema for performance metrics validation.
 *
 * Validates performance tracking data for AI agents including response times,
 * success rates, token usage, and cost estimates. Used for monitoring agent
 * performance and optimizing configurations.
 */
export const PerformanceMetricsSchema = z.object({
  agent_type: AgentTypeEnum,
  average_response_time: z.number().min(0),
  success_rate: z.number().min(0).max(1),
  error_rate: z.number().min(0).max(1),
  token_usage: z.record(z.string(), z.number().int()),
  cost_estimate: z.string(), // Decimal as string
  measured_at: z.string().datetime(),
  sample_size: z.number().int().min(1),

  // Computed fields
  performance_grade: z.string().optional(),
  tokens_per_second: z.number().min(0).optional(),
});

/** TypeScript type for performance metrics inferred from PerformanceMetricsSchema. */
export type PerformanceMetrics = z.infer<typeof PerformanceMetricsSchema>;

/**
 * Zod schema for configuration validation error details.
 *
 * Defines the structure for individual validation errors including field names,
 * error messages, current and suggested values, and severity levels.
 */
export const ConfigurationValidationErrorSchema = z.object({
  field: z.string(),
  error: z.string(),
  current_value: z.union([z.string(), z.number(), z.boolean(), z.null()]),
  suggested_value: z.union([z.string(), z.number(), z.boolean(), z.null()]).optional(),
  severity: z.enum(["error", "warning", "info"]).default("error"),
  error_code: z.string().optional(),
});

/** TypeScript type for configuration validation errors. */
export type ConfigurationValidationError = z.infer<
  typeof ConfigurationValidationErrorSchema
>;

/**
 * Zod schema for configuration validation response.
 *
 * Validates complete validation responses including validity status, error lists,
 * warnings, suggestions, and summary information for comprehensive validation feedback.
 */
export const ConfigurationValidationResponseSchema = z.object({
  is_valid: z.boolean(),
  errors: z.array(ConfigurationValidationErrorSchema).default([]),
  warnings: z.array(ConfigurationValidationErrorSchema).default([]),
  suggestions: z.array(z.string()).default([]),
  validation_summary: z.string().optional(),
});

/** TypeScript type for configuration validation responses. */
export type ConfigurationValidationResponse = z.infer<
  typeof ConfigurationValidationResponseSchema
>;

// Deprecated: legacy WebSocket config messages removed with Realtime migration

/**
 * Zod schema for configuration form validation in UI components.
 *
 * Validates form data from configuration management UI with agent-specific
 * recommendations and warnings for optimal parameter settings.
 */
export const ConfigurationFormSchema = z
  .object({
    agent_type: AgentTypeEnum,
    temperature: z.number().optional(),
    max_tokens: z.number().optional(),
    top_p: z.number().optional(),
    timeout_seconds: z.number().optional(),
    model: z.string().optional(),
    description: z.string().optional().nullable(),
  })
  .refine((data: any) => {
    // Agent-specific validation rules
    const recommendedTemperatures: Record<AgentType, number> = {
      budget_agent: 0.2,
      destination_research_agent: 0.5,
      itinerary_agent: 0.4,
    };

    if (data.temperature !== undefined && data.agent_type) {
      const recommended = recommendedTemperatures[data.agent_type as AgentType];
      const diff = Math.abs(data.temperature - recommended);

      // Warning for temperatures too far from recommended
      if (diff > 0.3) {
        return {
          warning: `Temperature ${data.temperature} may not be optimal for ${data.agent_type}. Recommended: ${recommended}`,
        };
      }
    }

    return true;
  });

/** TypeScript type for configuration forms inferred from ConfigurationFormSchema. */
export type ConfigurationForm = z.infer<typeof ConfigurationFormSchema>;

/**
 * Generic Zod schema factory for API response validation.
 *
 * Creates standardized API response schemas with consistent structure including
 * success status, optional messages, and error arrays for all API endpoints.
 *
 * @template T - The Zod schema type for the response data
 * @param dataSchema - The schema to validate the response data against
 * @returns A Zod schema for validating API responses
 */
export const ApiResponseSchema = <T extends z.ZodType>(dataSchema: T) =>
  z.object({
    data: dataSchema,
    success: z.boolean(),
    message: z.string().optional(),
    errors: z.array(z.string()).optional(),
  });

/** Zod schema for agent configuration API responses. */
export const AgentConfigApiResponseSchema = ApiResponseSchema(
  AgentConfigResponseSchema
);

/** Zod schema for configuration list API responses. */
export const ConfigurationListApiResponseSchema = ApiResponseSchema(
  z.record(AgentTypeEnum, AgentConfigResponseSchema)
);

/** Zod schema for version history API responses. */
export const VersionHistoryApiResponseSchema = ApiResponseSchema(
  z.array(ConfigurationVersionSchema)
);

/**
 * Zod schema for agent selection form validation.
 *
 * Simple schema for validating agent type selection in UI forms and dropdowns.
 */
export const AgentSelectSchema = z.object({
  agent_type: AgentTypeEnum,
});

/**
 * Zod schema for environment selection validation.
 *
 * Validates environment selection for configuration scoping and deployment targeting.
 */
export const EnvironmentSelectSchema = z.object({
  environment: z.enum(["development", "production", "staging", "test"]),
});

/**
 * Zod schema for configuration export validation.
 *
 * Validates complete configuration exports including agent configurations,
 * feature flags, global defaults, and export metadata for backup and migration purposes.
 */
export const ConfigurationExportSchema = z.object({
  export_id: z.string(),
  environment: z.string(),
  agent_configurations: z.record(AgentTypeEnum, AgentConfigResponseSchema),
  feature_flags: z.record(z.string(), z.boolean()),
  global_defaults: z.record(z.string(), z.any()),
  exported_at: z.string().datetime(),
  exported_by: z.string(),
  format: z.enum(["json", "yaml"]).default("json"),

  // Computed fields
  total_configurations: z.number().int().min(0).optional(),
  export_size_estimate_kb: z.number().min(0).optional(),
});

/** TypeScript type for configuration exports inferred from ConfigurationExportSchema. */
export type ConfigurationExport = z.infer<typeof ConfigurationExportSchema>;

/**
 * Validates agent configuration request data.
 *
 * Parses and validates unknown data against the AgentConfigRequestSchema,
 * throwing an error if validation fails.
 *
 * @param data - The data to validate
 * @returns The validated agent configuration request
 * @throws {z.ZodError} If validation fails
 */
export const validateAgentConfig = (data: unknown): AgentConfigRequest => {
  return AgentConfigRequestSchema.parse(data);
};

/**
 * Validates agent configuration response data.
 *
 * Parses and validates unknown data against the AgentConfigResponseSchema,
 * throwing an error if validation fails.
 *
 * @param data - The data to validate
 * @returns The validated agent configuration response
 * @throws {z.ZodError} If validation fails
 */
export const validateConfigurationResponse = (data: unknown): AgentConfigResponse => {
  return AgentConfigResponseSchema.parse(data);
};

/**
 * Generic API response validator.
 *
 * Validates API response data against a provided Zod schema with proper typing.
 *
 * @template T - The expected return type
 * @param schema - The Zod schema to validate against
 * @param data - The data to validate
 * @returns The validated data with proper typing
 * @throws {z.ZodError} If validation fails
 */
export const validateApiResponse = <T>(schema: z.ZodType<T>, data: unknown): T => {
  return schema.parse(data);
};

/**
 * Extracts field-specific error message from Zod validation error.
 *
 * Searches through Zod error issues to find the first error message for a specific field.
 *
 * @param error - The Zod validation error
 * @param fieldName - The field name to find errors for
 * @returns The error message for the field, or undefined if not found
 */
export const getFieldErrorMessage = (
  error: z.ZodError,
  fieldName: string
): string | undefined => {
  const fieldError = error.issues.find((err) => err.path.includes(fieldName));
  return fieldError?.message;
};

/**
 * Converts Zod validation errors to a field-error mapping.
 *
 * Transforms Zod error issues into a record mapping field paths to error messages
 * for easy form error handling.
 *
 * @param error - The Zod validation error
 * @returns A record mapping field paths to error messages
 */
export const getFormErrors = (error: z.ZodError): Record<string, string> => {
  const errors: Record<string, string> = {};

  error.issues.forEach((err) => {
    const field = err.path.join(".");
    errors[field] = err.message;
  });

  return errors;
};

/**
 * Returns default configuration values for a specific agent type.
 *
 * Provides optimized default settings for each agent type based on their use case,
 * ensuring good performance and appropriate behavior out of the box.
 *
 * @param agentType - The type of agent to get defaults for
 * @returns The default configuration for the specified agent type
 */
export const getDefaultConfigForAgent = (agentType: AgentType): AgentConfigRequest => {
  const defaults: Record<AgentType, AgentConfigRequest> = {
    budget_agent: {
      temperature: 0.2,
      max_tokens: 1000,
      top_p: 0.9,
      timeout_seconds: 30,
      model: "gpt-4",
      description: "Budget optimization agent - low creativity, high accuracy",
    },
    destination_research_agent: {
      temperature: 0.5,
      max_tokens: 1000,
      top_p: 0.9,
      timeout_seconds: 30,
      model: "gpt-4",
      description: "Destination research agent - moderate creativity for research",
    },
    itinerary_agent: {
      temperature: 0.4,
      max_tokens: 1000,
      top_p: 0.9,
      timeout_seconds: 30,
      model: "gpt-4",
      description:
        "Itinerary planning agent - structured creativity for logical planning",
    },
  };

  return defaults[agentType];
};
