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
export const AGENT_TYPE_ENUM = z.enum([
  "budgetAgent",
  "destinationResearchAgent",
  "itineraryAgent",
] as const);

/** TypeScript type for agent types inferred from AGENT_TYPE_ENUM schema. */
export type AgentType = z.infer<typeof AGENT_TYPE_ENUM>;

/**
 * Zod schema for configuration scope enumeration.
 *
 * Defines the hierarchical scopes for configuration settings, allowing
 * global defaults, environment overrides, agent-specific settings, and
 * user-level customizations.
 */
export const CONFIGURATION_SCOPE_ENUM = z.enum([
  "global",
  "environment",
  "agentSpecific",
  "userOverride",
] as const);

/** TypeScript type for configuration scopes inferred from CONFIGURATION_SCOPE_ENUM schema. */
export type ConfigurationScope = z.infer<typeof CONFIGURATION_SCOPE_ENUM>;

/**
 * Zod schema for supported AI model names.
 *
 * Validates model names against the list of supported AI models including
 * OpenAI GPT series and Anthropic Claude models for configuration validation.
 */
export const MODEL_NAME_SCHEMA = z.enum([
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

/** TypeScript type for model names inferred from MODEL_NAME_SCHEMA. */
export type ModelName = z.infer<typeof MODEL_NAME_SCHEMA>;

/**
 * Zod schema for version ID validation.
 *
 * Validates version identifiers following the format v{timestamp}_{hash}
 * for consistent versioning across configuration changes and rollbacks.
 */
export const VERSION_ID_SCHEMA = z
  .string()
  .regex(/^v\d+_[a-f0-9]{8}$/, "Version ID must match format: v{timestamp}_{hash}");

/** TypeScript type for version IDs inferred from VERSION_ID_SCHEMA. */
export type VersionId = z.infer<typeof VERSION_ID_SCHEMA>;

/**
 * Zod schema for agent configuration request validation.
 *
 * Validates incoming configuration requests for AI agents with cross-field
 * validation ensuring model compatibility and parameter constraints. Includes
 * temperature, token limits, model selection, and timeout settings with
 * intelligent validation based on selected AI models.
 */
export const AGENT_CONFIG_REQUEST_SCHEMA = z
  .object({
    description: z
      .string()
      .max(500, "Description must be at most 500 characters")
      .trim()
      .optional()
      .nullable(),

    maxTokens: z
      .number()
      .int("Max tokens must be an integer")
      .min(1, "Max tokens must be at least 1")
      .max(8000, "Max tokens must be at most 8000")
      .optional(),

    model: MODEL_NAME_SCHEMA.optional(),
    temperature: z
      .number()
      .min(0.0, "Temperature must be at least 0.0")
      .max(2.0, "Temperature must be at most 2.0")
      .multipleOf(0.01, "Temperature must have at most 2 decimal places")
      .optional(),

    timeoutSeconds: z
      .number()
      .int("Timeout must be an integer")
      .min(5, "Timeout must be at least 5 seconds")
      .max(300, "Timeout must be at most 300 seconds")
      .optional(),

    topP: z
      .number()
      .min(0.0, "Top-p must be at least 0.0")
      .max(1.0, "Top-p must be at most 1.0")
      .multipleOf(0.01, "Top-p must have at most 2 decimal places")
      .optional(),
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

      if (data.model && data.maxTokens !== undefined) {
        // Model-specific token limits
        const modelLimits: Record<string, number> = {
          "claude-3-haiku": 4096,
          "claude-3-sonnet": 8192,
          "gpt-3.5-turbo": 4096,
          "gpt-4": 8192,
          "gpt-4-turbo": 8192,
          "gpt-4o": 8192,
        };

        const maxLimit = modelLimits[data.model] || 8000;
        if (data.maxTokens > maxLimit) {
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

/** TypeScript type for agent configuration requests inferred from AGENT_CONFIG_REQUEST_SCHEMA. */
export type AgentConfigRequest = z.infer<typeof AGENT_CONFIG_REQUEST_SCHEMA>;

/**
 * Zod schema for agent configuration response validation.
 *
 * Validates complete agent configuration responses from the backend including
 * computed fields like cost estimates, performance metrics, and metadata.
 * Ensures all required fields are present and properly typed.
 */
export const AGENT_CONFIG_RESPONSE_SCHEMA = z.object({
  agentType: AGENT_TYPE_ENUM,
  createdAt: z.string().datetime(),
  creativityLevel: z.string().optional(),
  description: z.string().max(500).nullable().optional(),

  // Computed fields from backend
  estimatedCostPer1kTokens: z.string().optional(), // Decimal as string
  isActive: z.boolean().default(true),
  maxTokens: z.number().int().min(1).max(8000),
  model: MODEL_NAME_SCHEMA,
  performanceTier: z.string().optional(),
  responseSizeCategory: z.string().optional(),
  scope: CONFIGURATION_SCOPE_ENUM,
  temperature: z.number().min(0.0).max(2.0),
  timeoutSeconds: z.number().int().min(5).max(300),
  topP: z.number().min(0.0).max(1.0),
  updatedAt: z.string().datetime(),
  updatedBy: z.string().nullable().optional(),
});

/** TypeScript type for agent configuration responses inferred from AGENT_CONFIG_RESPONSE_SCHEMA. */
export type AgentConfigResponse = z.infer<typeof AGENT_CONFIG_RESPONSE_SCHEMA>;

/**
 * Zod schema for configuration version validation.
 *
 * Validates configuration version objects for version control and rollback
 * functionality. Tracks changes over time with metadata about who created
 * versions and when they were created.
 */
export const CONFIGURATION_VERSION_SCHEMA = z.object({
  // Computed fields
  ageInDays: z.number().int().min(0).optional(),
  agentType: AGENT_TYPE_ENUM,
  configuration: z.record(z.string(), z.any()),
  createdAt: z.string().datetime(),
  createdBy: z.string(),
  description: z.string().max(500).nullable().optional(),
  isCurrent: z.boolean().default(false),
  isRecent: z.boolean().optional(),
  scope: CONFIGURATION_SCOPE_ENUM,
  versionId: VERSION_ID_SCHEMA,
});

/** TypeScript type for configuration versions inferred from CONFIGURATION_VERSION_SCHEMA. */
export type ConfigurationVersion = z.infer<typeof CONFIGURATION_VERSION_SCHEMA>;

/**
 * Zod schema for performance metrics validation.
 *
 * Validates performance tracking data for AI agents including response times,
 * success rates, token usage, and cost estimates. Used for monitoring agent
 * performance and optimizing configurations.
 */
export const PERFORMANCE_METRICS_SCHEMA = z.object({
  agentType: AGENT_TYPE_ENUM,
  averageResponseTime: z.number().min(0),
  costEstimate: z.string(), // Decimal as string
  errorRate: z.number().min(0).max(1),
  measuredAt: z.string().datetime(),

  // Computed fields
  performanceGrade: z.string().optional(),
  sampleSize: z.number().int().min(1),
  successRate: z.number().min(0).max(1),
  tokensPerSecond: z.number().min(0).optional(),
  tokenUsage: z.record(z.string(), z.number().int()),
});

/** TypeScript type for performance metrics inferred from PERFORMANCE_METRICS_SCHEMA. */
export type PerformanceMetrics = z.infer<typeof PERFORMANCE_METRICS_SCHEMA>;

/**
 * Zod schema for configuration validation error details.
 *
 * Defines the structure for individual validation errors including field names,
 * error messages, current and suggested values, and severity levels.
 */
export const CONFIGURATION_VALIDATION_ERROR_SCHEMA = z.object({
  currentValue: z.union([z.string(), z.number(), z.boolean(), z.null()]),
  error: z.string(),
  errorCode: z.string().optional(),
  field: z.string(),
  severity: z.enum(["error", "warning", "info"]).default("error"),
  suggestedValue: z.union([z.string(), z.number(), z.boolean(), z.null()]).optional(),
});

/** TypeScript type for configuration validation errors. */
export type ConfigurationValidationError = z.infer<
  typeof CONFIGURATION_VALIDATION_ERROR_SCHEMA
>;

/**
 * Zod schema for configuration validation response.
 *
 * Validates complete validation responses including validity status, error lists,
 * warnings, suggestions, and summary information for comprehensive validation feedback.
 */
export const CONFIGURATION_VALIDATION_RESPONSE_SCHEMA = z.object({
  errors: z.array(CONFIGURATION_VALIDATION_ERROR_SCHEMA).default([]),
  isValid: z.boolean(),
  suggestions: z.array(z.string()).default([]),
  validationSummary: z.string().optional(),
  warnings: z.array(CONFIGURATION_VALIDATION_ERROR_SCHEMA).default([]),
});

/** TypeScript type for configuration validation responses. */
export type ConfigurationValidationResponse = z.infer<
  typeof CONFIGURATION_VALIDATION_RESPONSE_SCHEMA
>;

// Deprecated: legacy WebSocket config messages removed with Realtime migration

/**
 * Zod schema for configuration form validation in UI components.
 *
 * Validates form data from configuration management UI with agent-specific
 * recommendations and warnings for optimal parameter settings.
 */
export const CONFIGURATION_FORM_SCHEMA = z
  .object({
    agentType: AGENT_TYPE_ENUM,
    description: z.string().optional().nullable(),
    maxTokens: z.number().optional(),
    model: z.string().optional(),
    temperature: z.number().optional(),
    timeoutSeconds: z.number().optional(),
    topP: z.number().optional(),
  })
  .refine((data: z.infer<typeof CONFIGURATION_FORM_SCHEMA>) => {
    // Agent-specific validation rules
    const recommendedTemperatures: Record<AgentType, number> = {
      budgetAgent: 0.2,
      destinationResearchAgent: 0.5,
      itineraryAgent: 0.4,
    };

    if (data.temperature !== undefined && data.agentType) {
      const recommended = recommendedTemperatures[data.agentType];
      const diff = Math.abs(data.temperature - recommended);

      // Warning for temperatures too far from recommended
      if (diff > 0.3) {
        return {
          warning: `Temperature ${data.temperature} may not be optimal for ${data.agentType}. Recommended: ${recommended}`,
        };
      }
    }

    return true;
  });

/** TypeScript type for configuration forms inferred from CONFIGURATION_FORM_SCHEMA. */
export type ConfigurationForm = z.infer<typeof CONFIGURATION_FORM_SCHEMA>;

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
export const API_RESPONSE_SCHEMA = <T extends z.ZodType>(dataSchema: T) =>
  z.object({
    data: dataSchema,
    errors: z.array(z.string()).optional(),
    message: z.string().optional(),
    success: z.boolean(),
  });

/** Zod schema for agent configuration API responses. */
export const AGENT_CONFIG_API_RESPONSE_SCHEMA = API_RESPONSE_SCHEMA(
  AGENT_CONFIG_RESPONSE_SCHEMA
);

/** Zod schema for configuration list API responses. */
export const CONFIGURATION_LIST_API_RESPONSE_SCHEMA = API_RESPONSE_SCHEMA(
  z.record(AGENT_TYPE_ENUM, AGENT_CONFIG_RESPONSE_SCHEMA)
);

/** Zod schema for version history API responses. */
export const VERSION_HISTORY_API_RESPONSE_SCHEMA = API_RESPONSE_SCHEMA(
  z.array(CONFIGURATION_VERSION_SCHEMA)
);

/**
 * Zod schema for agent selection form validation.
 *
 * Simple schema for validating agent type selection in UI forms and dropdowns.
 */
export const AGENT_SELECT_SCHEMA = z.object({
  agentType: AGENT_TYPE_ENUM,
});

/**
 * Zod schema for environment selection validation.
 *
 * Validates environment selection for configuration scoping and deployment targeting.
 */
export const ENVIRONMENT_SELECT_SCHEMA = z.object({
  environment: z.enum(["development", "production", "staging", "test"]),
});

/**
 * Zod schema for configuration export validation.
 *
 * Validates complete configuration exports including agent configurations,
 * feature flags, global defaults, and export metadata for backup and migration purposes.
 */
export const CONFIGURATION_EXPORT_SCHEMA = z.object({
  agentConfigurations: z.record(AGENT_TYPE_ENUM, AGENT_CONFIG_RESPONSE_SCHEMA),
  environment: z.string(),
  exportedAt: z.string().datetime(),
  exportedBy: z.string(),
  exportId: z.string(),
  exportSizeEstimateKb: z.number().min(0).optional(),
  featureFlags: z.record(z.string(), z.boolean()),
  format: z.enum(["json", "yaml"]).default("json"),
  globalDefaults: z.record(z.string(), z.any()),

  // Computed fields
  totalConfigurations: z.number().int().min(0).optional(),
});

/** TypeScript type for configuration exports inferred from CONFIGURATION_EXPORT_SCHEMA. */
export type ConfigurationExport = z.infer<typeof CONFIGURATION_EXPORT_SCHEMA>;

/**
 * Validates agent configuration request data.
 *
 * Parses and validates unknown data against the AGENT_CONFIG_REQUEST_SCHEMA,
 * throwing an error if validation fails.
 *
 * @param data - The data to validate
 * @returns The validated agent configuration request
 * @throws {z.ZodError} If validation fails
 */
export const validateAgentConfig = (data: unknown): AgentConfigRequest => {
  return AGENT_CONFIG_REQUEST_SCHEMA.parse(data);
};

/**
 * Validates agent configuration response data.
 *
 * Parses and validates unknown data against the AGENT_CONFIG_RESPONSE_SCHEMA,
 * throwing an error if validation fails.
 *
 * @param data - The data to validate
 * @returns The validated agent configuration response
 * @throws {z.ZodError} If validation fails
 */
export const validateConfigurationResponse = (data: unknown): AgentConfigResponse => {
  return AGENT_CONFIG_RESPONSE_SCHEMA.parse(data);
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
    budgetAgent: {
      description: "Budget optimization agent - low creativity, high accuracy",
      maxTokens: 1000,
      model: "gpt-4",
      temperature: 0.2,
      timeoutSeconds: 30,
      topP: 0.9,
    },
    destinationResearchAgent: {
      description: "Destination research agent - moderate creativity for research",
      maxTokens: 1000,
      model: "gpt-4",
      temperature: 0.5,
      timeoutSeconds: 30,
      topP: 0.9,
    },
    itineraryAgent: {
      description:
        "Itinerary planning agent - structured creativity for logical planning",
      maxTokens: 1000,
      model: "gpt-4",
      temperature: 0.4,
      timeoutSeconds: 30,
      topP: 0.9,
    },
  };

  return defaults[agentType];
};
