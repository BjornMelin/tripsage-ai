/**
 * @fileoverview Canonical Zod v4 schemas for configuration management.
 * Runtime type safety for agent configs, models, versions, and domain config.
 */

import { z } from "zod";

/** Zod schema for agent type classifications. */
export const AGENT_TYPE_ENUM = z.enum([
  "budgetAgent",
  "destinationResearchAgent",
  "itineraryAgent",
] as const);
/** TypeScript type for agent types. */
export type AgentType = z.infer<typeof AGENT_TYPE_ENUM>;

/** Zod schema for configuration scope levels. */
export const CONFIGURATION_SCOPE_ENUM = z.enum([
  "global",
  "environment",
  "agentSpecific",
  "userOverride",
] as const);
/** TypeScript type for configuration scopes. */
export type ConfigurationScope = z.infer<typeof CONFIGURATION_SCOPE_ENUM>;

/** Zod schema for supported AI model names. */
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
/** TypeScript type for model names. */
export type ModelName = z.infer<typeof MODEL_NAME_SCHEMA>;

/** Zod schema for version identifiers with validation. */
export const VERSION_ID_SCHEMA = z
  .string()
  .regex(/^v\d+_[a-f0-9]{8}$/, "Version ID must match format: v{timestamp}_{hash}");
/** TypeScript type for version IDs. */
export type VersionId = z.infer<typeof VERSION_ID_SCHEMA>;

/**
 * Zod schema for agent configuration requests.
 * Validates model parameters and generation settings.
 */
export const AGENT_CONFIG_REQUEST_SCHEMA = z
  .object({
    description: z.string().max(500).trim().optional().nullable(),
    maxTokens: z.number().int().min(1).max(8000).optional(),
    model: MODEL_NAME_SCHEMA.optional(),
    temperature: z.number().min(0.0).max(2.0).multipleOf(0.01).optional(),
    timeoutSeconds: z.number().int().min(5).max(300).optional(),
    topP: z.number().min(0.0).max(1.0).multipleOf(0.01).optional(),
  })
  .refine((data) => {
    if (data.model && data.temperature !== undefined) {
      if (
        (data.model.startsWith("gpt-4") || data.model.startsWith("gpt-5")) &&
        data.temperature > 1.5
      ) {
        return false;
      }
    }
    return true;
  }, "Temperature too high for selected model");

/** TypeScript type for agent config requests. */
export type AgentConfigRequest = z.infer<typeof AGENT_CONFIG_REQUEST_SCHEMA>;

/** Zod schema for complete agent configuration records. */
export const AGENT_CONFIG_SCHEMA = z.object({
  createdAt: z.string().datetime(),
  id: VERSION_ID_SCHEMA,
  model: MODEL_NAME_SCHEMA,
  parameters: AGENT_CONFIG_REQUEST_SCHEMA,
  scope: CONFIGURATION_SCOPE_ENUM,
  updatedAt: z.string().datetime(),
});
/** TypeScript type for agent configurations. */
export type AgentConfig = z.infer<typeof AGENT_CONFIG_SCHEMA>;

/** Zod schema for date ranges with validation. */
export const dateRangeSchema = z
  .object({ endDate: z.date(), startDate: z.date() })
  .refine((d) => d.endDate >= d.startDate, "End date must be on or after start date");
/** TypeScript type for date ranges. */
export type DateRange = z.infer<typeof dateRangeSchema>;

/** Zod schema for availability information with capacity and restrictions. */
export const availabilitySchema = z
  .object({
    available: z.boolean(),
    capacity: z.number().int().min(0).optional(),
    fromDatetime: z.date().optional(),
    restrictions: z.array(z.string()).optional(),
    toDatetime: z.date().optional(),
  })
  .refine(
    (d) => (d.fromDatetime && d.toDatetime ? d.toDatetime > d.fromDatetime : true),
    {
      message: "toDatetime must be after fromDatetime",
      path: ["toDatetime"],
    }
  );
/** TypeScript type for availability. */
export type Availability = z.infer<typeof availabilitySchema>;
