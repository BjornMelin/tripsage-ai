/**
 * Zod validation schemas for configuration management.
 *
 * These schemas provide runtime type safety and validation for all configuration
 * data, ensuring consistency between frontend and backend APIs.
 */

import { z } from "zod";

// Agent type enum matching backend
export const AgentTypeEnum = z.enum([
  "budget_agent",
  "destination_research_agent",
  "itinerary_agent",
] as const);

export type AgentType = z.infer<typeof AgentTypeEnum>;

// Configuration scope enum
export const ConfigurationScopeEnum = z.enum([
  "global",
  "environment",
  "agent_specific",
  "user_override",
] as const);

export type ConfigurationScope = z.infer<typeof ConfigurationScopeEnum>;

// Model name validation with supported models
export const ModelNameSchema = z.enum([
  "gpt-4",
  "gpt-4-turbo",
  "gpt-4o",
  "gpt-4o-mini",
  "gpt-3.5-turbo",
  "claude-3-sonnet",
  "claude-3-haiku",
] as const);

export type ModelName = z.infer<typeof ModelNameSchema>;

// Version ID format validation
export const VersionIdSchema = z
  .string()
  .regex(/^v\d+_[a-f0-9]{8}$/, "Version ID must match format: v{timestamp}_{hash}");

export type VersionId = z.infer<typeof VersionIdSchema>;

// Base agent configuration request schema
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

export type AgentConfigRequest = z.infer<typeof AgentConfigRequestSchema>;

// Agent configuration response schema
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

export type AgentConfigResponse = z.infer<typeof AgentConfigResponseSchema>;

// Configuration version schema
export const ConfigurationVersionSchema = z.object({
  version_id: VersionIdSchema,
  agent_type: AgentTypeEnum,
  configuration: z.record(z.any()),
  scope: ConfigurationScopeEnum,
  created_at: z.string().datetime(),
  created_by: z.string(),
  description: z.string().max(500).nullable().optional(),
  is_current: z.boolean().default(false),

  // Computed fields
  age_in_days: z.number().int().min(0).optional(),
  is_recent: z.boolean().optional(),
});

export type ConfigurationVersion = z.infer<typeof ConfigurationVersionSchema>;

// Performance metrics schema
export const PerformanceMetricsSchema = z.object({
  agent_type: AgentTypeEnum,
  average_response_time: z.number().min(0),
  success_rate: z.number().min(0).max(1),
  error_rate: z.number().min(0).max(1),
  token_usage: z.record(z.number().int()),
  cost_estimate: z.string(), // Decimal as string
  measured_at: z.string().datetime(),
  sample_size: z.number().int().min(1),

  // Computed fields
  performance_grade: z.string().optional(),
  tokens_per_second: z.number().min(0).optional(),
});

export type PerformanceMetrics = z.infer<typeof PerformanceMetricsSchema>;

// Configuration validation error schema
export const ConfigurationValidationErrorSchema = z.object({
  field: z.string(),
  error: z.string(),
  current_value: z.union([z.string(), z.number(), z.boolean(), z.null()]),
  suggested_value: z.union([z.string(), z.number(), z.boolean(), z.null()]).optional(),
  severity: z.enum(["error", "warning", "info"]).default("error"),
  error_code: z.string().optional(),
});

export type ConfigurationValidationError = z.infer<
  typeof ConfigurationValidationErrorSchema
>;

// Configuration validation response schema
export const ConfigurationValidationResponseSchema = z.object({
  is_valid: z.boolean(),
  errors: z.array(ConfigurationValidationErrorSchema).default([]),
  warnings: z.array(ConfigurationValidationErrorSchema).default([]),
  suggestions: z.array(z.string()).default([]),
  validation_summary: z.string().optional(),
});

export type ConfigurationValidationResponse = z.infer<
  typeof ConfigurationValidationResponseSchema
>;

// WebSocket message schema
export const WebSocketConfigMessageSchema = z.object({
  type: z.string(),
  agent_type: AgentTypeEnum.optional(),
  configuration: z.record(z.any()).optional(),
  version_id: VersionIdSchema.optional(),
  updated_by: z.string().optional(),
  timestamp: z.string().datetime(),
  message: z.string().optional(),
});

export type WebSocketConfigMessage = z.infer<typeof WebSocketConfigMessageSchema>;

// Configuration form schema for UI
export const ConfigurationFormSchema = z.object({
  agent_type: AgentTypeEnum,
  temperature: z.number().optional(),
  max_tokens: z.number().optional(),
  top_p: z.number().optional(),
  timeout_seconds: z.number().optional(),
  model: z.string().optional(),
  description: z.string().optional().nullable(),
}).refine((data: any) => {
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

export type ConfigurationForm = z.infer<typeof ConfigurationFormSchema>;

// API response wrapper schema
export const ApiResponseSchema = <T extends z.ZodType>(dataSchema: T) =>
  z.object({
    data: dataSchema,
    success: z.boolean(),
    message: z.string().optional(),
    errors: z.array(z.string()).optional(),
  });

// Common API responses
export const AgentConfigApiResponseSchema = ApiResponseSchema(
  AgentConfigResponseSchema
);
export const ConfigurationListApiResponseSchema = ApiResponseSchema(
  z.record(AgentTypeEnum, AgentConfigResponseSchema)
);
export const VersionHistoryApiResponseSchema = ApiResponseSchema(
  z.array(ConfigurationVersionSchema)
);

// Utility schemas for forms
export const AgentSelectSchema = z.object({
  agent_type: AgentTypeEnum,
});

export const EnvironmentSelectSchema = z.object({
  environment: z.enum(["development", "production", "staging", "test"]),
});

// Export statement validation schema for import/export
export const ConfigurationExportSchema = z.object({
  export_id: z.string(),
  environment: z.string(),
  agent_configurations: z.record(AgentTypeEnum, AgentConfigResponseSchema),
  feature_flags: z.record(z.boolean()),
  global_defaults: z.record(z.any()),
  exported_at: z.string().datetime(),
  exported_by: z.string(),
  format: z.enum(["json", "yaml"]).default("json"),

  // Computed fields
  total_configurations: z.number().int().min(0).optional(),
  export_size_estimate_kb: z.number().min(0).optional(),
});

export type ConfigurationExport = z.infer<typeof ConfigurationExportSchema>;

// Helper functions for validation
export const validateAgentConfig = (data: unknown): AgentConfigRequest => {
  return AgentConfigRequestSchema.parse(data);
};

export const validateConfigurationResponse = (data: unknown): AgentConfigResponse => {
  return AgentConfigResponseSchema.parse(data);
};

export const validateApiResponse = <T>(schema: z.ZodType<T>, data: unknown): T => {
  return schema.parse(data);
};

// Form validation helpers
export const getFieldErrorMessage = (
  error: z.ZodError,
  fieldName: string
): string | undefined => {
  const fieldError = error.errors.find((err) => err.path.includes(fieldName));
  return fieldError?.message;
};

export const getFormErrors = (error: z.ZodError): Record<string, string> => {
  const errors: Record<string, string> = {};

  error.errors.forEach((err) => {
    const field = err.path.join(".");
    errors[field] = err.message;
  });

  return errors;
};

// Default values for forms
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
      description:
        "Destination research agent - moderate creativity for comprehensive research",
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
