/**
 * @fileoverview Configuration management schemas with validation.
 * Includes agent configurations, model names, version identifiers, and configuration scopes.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for configuration management

/**
 * Zod schema for agent type classifications.
 * Defines available agent types in the system.
 */
export const agentTypeSchema = z.enum([
  "budgetAgent",
  "destinationResearchAgent",
  "itineraryAgent",
  "flightAgent",
  "accommodationAgent",
  "activityAgent",
  "memoryAgent",
] as const);

/** TypeScript type for agent types. */
export type AgentType = z.infer<typeof agentTypeSchema>;

/**
 * Zod schema for configuration scope levels.
 * Defines hierarchy of configuration scopes from global to user-specific.
 */
export const configurationScopeSchema = z.enum([
  "global",
  "environment",
  "agentSpecific",
  "userOverride",
] as const);

/** TypeScript type for configuration scopes. */
export type ConfigurationScope = z.infer<typeof configurationScopeSchema>;

/**
 * Zod schema for supported AI model names.
 * Defines available AI models for agent configuration.
 */
export const modelNameSchema = z.enum([
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

/** TypeScript type for model names. */
export type ModelName = z.infer<typeof modelNameSchema>;

/**
 * Zod schema for version identifiers with validation.
 * Validates version ID format: v{timestamp}_{hash}.
 */
export const versionIdSchema = z.string().regex(/^v\d+_[a-f0-9]{8}$/, {
  error: "Version ID must match format: v{timestamp}_{hash}",
});

/** TypeScript type for version IDs. */
export type VersionId = z.infer<typeof versionIdSchema>;

/**
 * Zod schema for agent configuration requests.
 * Validates model parameters and generation settings with business rules.
 */
export const agentConfigRequestSchema = z
  .strictObject({
    description: z.string().max(500).trim().optional().nullable(),
    maxTokens: z.number().int().min(1).max(8000).optional(),
    model: modelNameSchema.optional(),
    temperature: z.number().min(0.0).max(2.0).multipleOf(0.01).optional(),
    timeoutSeconds: z.number().int().min(5).max(300).optional(),
    topKTools: z.number().int().min(1).max(8).optional(),
    topP: z.number().min(0.0).max(1.0).multipleOf(0.01).optional(),
  })
  .refine(
    (data) => {
      if (data.model && data.temperature !== undefined) {
        if (
          (data.model.startsWith("gpt-4") || data.model.startsWith("gpt-5")) &&
          data.temperature > 1.5
        ) {
          return false;
        }
      }
      return true;
    },
    { error: "Temperature too high for selected model" }
  );

/** TypeScript type for agent config requests. */
export type AgentConfigRequest = z.infer<typeof agentConfigRequestSchema>;

/**
 * Zod schema for complete agent configuration records.
 * Validates agent configuration including model, parameters, scope, and timestamps.
 */
export const configurationAgentConfigSchema = z.object({
  agentType: agentTypeSchema,
  createdAt: primitiveSchemas.isoDateTime,
  id: versionIdSchema,
  model: modelNameSchema,
  parameters: agentConfigRequestSchema,
  scope: configurationScopeSchema,
  updatedAt: primitiveSchemas.isoDateTime,
});

/** TypeScript type for agent configurations. */
export type AgentConfig = z.infer<typeof configurationAgentConfigSchema>;
