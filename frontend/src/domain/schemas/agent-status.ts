/**
 * @fileoverview Agent status tracking and validation schemas.
 * Includes agent entities, tasks, workflows, metrics, and real-time update schemas.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====

// Core business logic schemas for agent management
const DATE_STRING_SCHEMA = primitiveSchemas.isoDateTime;
const PROGRESS_SCHEMA = z.number().int().min(0).max(100);

/**
 * Zod schema for agent status type enumeration.
 * Defines possible states for agent execution lifecycle.
 */
export const agentStatusTypeSchema = z.enum([
  "idle",
  "initializing",
  "active",
  "waiting",
  "paused",
  "thinking",
  "executing",
  "error",
  "completed",
]);

/** TypeScript type for agent status types. */
export type AgentStatusType = z.infer<typeof agentStatusTypeSchema>;

/**
 * Zod schema for task status enumeration.
 * Defines possible states for agent task execution.
 */
export const taskStatusSchema = z.enum([
  "pending",
  "in_progress",
  "completed",
  "failed",
]);

/** TypeScript type for task status. */
export type TaskStatus = z.infer<typeof taskStatusSchema>;

/**
 * Zod schema for session status enumeration.
 * Defines possible states for agent sessions.
 */
export const sessionStatusSchema = z.enum(["active", "completed", "error"]);

/** TypeScript type for session status. */
export type SessionStatus = z.infer<typeof sessionStatusSchema>;

/**
 * Zod schema for agent task entities.
 * Validates task details including status, progress, and error information.
 */
export const agentTaskSchema = z.object({
  completedAt: DATE_STRING_SCHEMA.optional(),
  createdAt: DATE_STRING_SCHEMA,
  description: z.string().max(1000, { error: "Description too long" }),
  error: z.string().max(500).optional(),
  id: primitiveSchemas.uuid,
  progress: PROGRESS_SCHEMA.optional(),
  status: taskStatusSchema,
  title: z
    .string()
    .min(1, { error: "Task title is required" })
    .max(200, { error: "Title too long" }),
  updatedAt: DATE_STRING_SCHEMA,
});

/** TypeScript type for agent tasks. */
export type AgentTask = z.infer<typeof agentTaskSchema>;

/**
 * Zod schema for agent entities.
 * Validates agent configuration, status, and associated tasks.
 */
export const agentSchema = z.object({
  createdAt: DATE_STRING_SCHEMA,
  currentTaskId: primitiveSchemas.uuid.optional(),
  description: z.string().max(500).optional(),
  id: primitiveSchemas.uuid,
  metadata: z.record(z.string(), z.unknown()).optional(),
  name: z
    .string()
    .min(1, { error: "Agent name is required" })
    .max(100, { error: "Name too long" }),
  progress: PROGRESS_SCHEMA,
  status: agentStatusTypeSchema,
  tasks: z.array(agentTaskSchema),
  type: z
    .string()
    .min(1, { error: "Agent type is required" })
    .max(50, { error: "Type too long" }),
  updatedAt: DATE_STRING_SCHEMA,
});

/** TypeScript type for agents. */
export type Agent = z.infer<typeof agentSchema>;

/**
 * Zod schema for agent activity records.
 * Validates activity logs with timestamps and metadata.
 */
export const agentActivitySchema = z.object({
  agentId: primitiveSchemas.uuid,
  id: primitiveSchemas.uuid,
  message: z
    .string()
    .min(1, { error: "Activity message is required" })
    .max(1000, { error: "Message too long" }),
  metadata: z.record(z.string(), z.unknown()).optional(),
  timestamp: DATE_STRING_SCHEMA,
  type: z
    .string()
    .min(1, { error: "Activity type is required" })
    .max(50, { error: "Type too long" }),
});

/** TypeScript type for agent activities. */
export type AgentActivity = z.infer<typeof agentActivitySchema>;

/**
 * Zod schema for resource usage metrics.
 * Tracks CPU, memory, and network usage for agents.
 */
export const resourceUsageSchema = z.object({
  activeAgents: z.number().int().nonnegative(),
  cpuUsage: z.number().min(0).max(100),
  memoryUsage: z.number().min(0).max(100),
  networkRequests: z.number().int().nonnegative(),
  timestamp: DATE_STRING_SCHEMA,
});

/** TypeScript type for resource usage. */
export type ResourceUsage = z.infer<typeof resourceUsageSchema>;

/**
 * Zod schema for agent session entities.
 * Groups agents, activities, and resource usage for a session.
 */
export const agentSessionSchema = z.object({
  activities: z.array(agentActivitySchema),
  agents: z.array(agentSchema),
  endedAt: DATE_STRING_SCHEMA.optional(),
  id: primitiveSchemas.uuid,
  resourceUsage: z.array(resourceUsageSchema),
  startedAt: DATE_STRING_SCHEMA,
  status: sessionStatusSchema,
});

/** TypeScript type for agent sessions. */
export type AgentSession = z.infer<typeof agentSessionSchema>;

/**
 * Zod schema for workflow connections between agents.
 * Defines conditional connections in agent workflows.
 */
export const workflowConnectionSchema = z.object({
  condition: z.string().max(500).optional(),
  from: primitiveSchemas.uuid,
  to: primitiveSchemas.uuid,
});

/** TypeScript type for workflow connections. */
export type WorkflowConnection = z.infer<typeof workflowConnectionSchema>;

/**
 * Zod schema for agent workflow entities.
 * Validates workflow configuration including agents and connections.
 */
export const agentWorkflowEntitySchema = z.object({
  agents: z
    .array(primitiveSchemas.uuid)
    .min(1, { error: "At least one agent is required" }),
  connections: z.array(workflowConnectionSchema),
  createdAt: DATE_STRING_SCHEMA,
  description: z.string().max(500).optional(),
  id: primitiveSchemas.uuid,
  name: z
    .string()
    .min(1, { error: "Workflow name is required" })
    .max(100, { error: "Name too long" }),
  updatedAt: DATE_STRING_SCHEMA,
});

/** TypeScript type for agent workflows. */
export type AgentWorkflowEntity = z.infer<typeof agentWorkflowEntitySchema>;

/**
 * Zod schema for agent runtime configuration.
 * Validates runtime settings including concurrency limits and timeouts.
 */
export const agentRuntimeConfigSchema = z.object({
  agentId: primitiveSchemas.uuid,
  createdAt: DATE_STRING_SCHEMA,
  customSettings: z.record(z.string(), z.unknown()).optional(),
  enableLogging: z.boolean(),
  enableMetrics: z.boolean(),
  id: primitiveSchemas.uuid,
  maxConcurrentTasks: z.number().int().positive().max(10),
  priority: z.enum(["low", "normal", "high", "critical"]),
  retryAttempts: z.number().int().nonnegative().max(5),
  timeoutMs: z.number().int().positive().max(300000), // 5 minutes max
  updatedAt: DATE_STRING_SCHEMA,
});

/** TypeScript type for agent runtime configuration. */
export type AgentRuntimeConfig = z.infer<typeof agentRuntimeConfigSchema>;

/**
 * Zod schema for agent performance metrics.
 * Tracks execution times, success rates, and task completion statistics.
 */
export const agentMetricsSchema = z.object({
  agentId: primitiveSchemas.uuid,
  averageExecutionTime: z.number().nonnegative(),
  createdAt: DATE_STRING_SCHEMA,
  lastActive: DATE_STRING_SCHEMA.optional(),
  successRate: z.number().min(0).max(1),
  tasksCompleted: z.number().int().nonnegative(),
  tasksFailed: z.number().int().nonnegative(),
  totalExecutionTime: z.number().nonnegative(),
  updatedAt: DATE_STRING_SCHEMA,
});

/** TypeScript type for agent metrics. */
export type AgentMetrics = z.infer<typeof agentMetricsSchema>;

// ===== STATE SCHEMAS =====
// Schemas for client-side state management

/**
 * Zod schema for agent state management in Zustand stores.
 * Organizes agents, sessions, workflows, and metrics for UI state.
 */
export const agentStateSchema = z.object({
  activeAgentIds: z.array(primitiveSchemas.uuid),
  activities: z.array(agentActivitySchema),
  agents: z.record(primitiveSchemas.uuid, agentSchema),
  currentSessionId: primitiveSchemas.uuid.nullable(),
  error: z.string().nullable(),
  isLoading: z.boolean(),
  lastUpdated: DATE_STRING_SCHEMA.nullable(),
  metrics: z.record(primitiveSchemas.uuid, agentMetricsSchema),
  resourceUsage: resourceUsageSchema.nullable(),
  sessions: z.record(primitiveSchemas.uuid, agentSessionSchema),
  workflows: z.record(primitiveSchemas.uuid, agentWorkflowEntitySchema),
});

/** TypeScript type for agent state. */
export type AgentState = z.infer<typeof agentStateSchema>;

// ===== API SCHEMAS =====
// Request/response schemas for agent API endpoints

/**
 * API request schema for creating agent tasks.
 * Validates task parameters including priority and metadata.
 */
export const createAgentTaskRequestSchema = z.object({
  agentId: primitiveSchemas.uuid,
  description: z.string().max(1000, { error: "Description too long" }),
  metadata: z.record(z.string(), z.unknown()).optional(),
  priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
  title: z
    .string()
    .min(1, { error: "Task title is required" })
    .max(200, { error: "Title too long" }),
});

/** TypeScript type for agent task creation requests. */
export type CreateAgentTaskRequest = z.infer<typeof createAgentTaskRequestSchema>;

/**
 * API request schema for updating existing agent tasks.
 * Allows partial updates of task properties.
 */
export const updateAgentTaskRequestSchema = z.object({
  description: z.string().max(1000).optional(),
  error: z.string().max(500).optional(),
  id: primitiveSchemas.uuid,
  progress: PROGRESS_SCHEMA.optional(),
  status: taskStatusSchema.optional(),
  title: z.string().min(1).max(200).optional(),
});

/** TypeScript type for agent task update requests. */
export type UpdateAgentTaskRequest = z.infer<typeof updateAgentTaskRequestSchema>;

/**
 * API request schema for creating new agents.
 * Validates agent configuration including type, name, and runtime settings.
 */
export const createAgentRequestSchema = z.object({
  config: z
    .object({
      enableLogging: z.boolean().default(true),
      enableMetrics: z.boolean().default(true),
      maxConcurrentTasks: z.number().int().positive().max(10).default(3),
      priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
      retryAttempts: z.number().int().nonnegative().max(5).default(3),
      timeoutMs: z.number().int().positive().max(300000).default(30000),
    })
    .optional(),
  description: z.string().max(500).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  name: z
    .string()
    .min(1, { error: "Agent name is required" })
    .max(100, { error: "Name too long" }),
  type: z
    .string()
    .min(1, { error: "Agent type is required" })
    .max(50, { error: "Type too long" }),
});

/** TypeScript type for agent creation requests. */
export type CreateAgentRequest = z.infer<typeof createAgentRequestSchema>;

/**
 * API request schema for updating existing agents.
 * Allows partial updates of agent properties.
 */
export const updateAgentRequestSchema = z.object({
  description: z.string().max(500).optional(),
  id: primitiveSchemas.uuid,
  metadata: z.record(z.string(), z.unknown()).optional(),
  name: z.string().min(1).max(100).optional(),
  status: agentStatusTypeSchema.optional(),
});

/** TypeScript type for agent update requests. */
export type UpdateAgentRequest = z.infer<typeof updateAgentRequestSchema>;

/**
 * API request schema for creating agent workflows.
 * Validates workflow configuration including agents and connections.
 */
export const createWorkflowRequestSchema = z.object({
  agents: z
    .array(primitiveSchemas.uuid)
    .min(1, { error: "At least one agent is required" }),
  connections: z.array(workflowConnectionSchema),
  description: z.string().max(500).optional(),
  name: z
    .string()
    .min(1, { error: "Workflow name is required" })
    .max(100, { error: "Name too long" }),
});

/** TypeScript type for workflow creation requests. */
export type CreateWorkflowRequest = z.infer<typeof createWorkflowRequestSchema>;

/**
 * API request schema for updating existing workflows.
 * Allows partial updates of workflow properties.
 */
export const updateWorkflowRequestSchema = z.object({
  agents: z.array(primitiveSchemas.uuid).min(1).optional(),
  connections: z.array(workflowConnectionSchema).optional(),
  description: z.string().max(500).optional(),
  id: primitiveSchemas.uuid,
  name: z.string().min(1).max(100).optional(),
});

/** TypeScript type for workflow update requests. */
export type UpdateWorkflowRequest = z.infer<typeof updateWorkflowRequestSchema>;

// ===== REALTIME SCHEMAS =====
// WebSocket message schemas for real-time updates

/**
 * Zod schema for agent status update WebSocket messages.
 * Broadcasts agent status changes in real-time.
 */
export const agentStatusUpdateSchema = z.object({
  agentId: primitiveSchemas.uuid,
  currentTaskId: primitiveSchemas.uuid.optional(),
  progress: PROGRESS_SCHEMA.optional(),
  status: agentStatusTypeSchema,
  timestamp: DATE_STRING_SCHEMA,
  type: z.literal("agent_status_update"),
});

/** TypeScript type for agent status updates. */
export type AgentStatusUpdate = z.infer<typeof agentStatusUpdateSchema>;

/**
 * Zod schema for task status update WebSocket messages.
 * Broadcasts task status changes in real-time.
 */
export const taskStatusUpdateSchema = z.object({
  agentId: primitiveSchemas.uuid,
  error: z.string().optional(),
  progress: PROGRESS_SCHEMA.optional(),
  status: taskStatusSchema,
  taskId: primitiveSchemas.uuid,
  timestamp: DATE_STRING_SCHEMA,
  type: z.literal("task_status_update"),
});

/** TypeScript type for task status updates. */
export type TaskStatusUpdate = z.infer<typeof taskStatusUpdateSchema>;

/**
 * Zod schema for resource usage update WebSocket messages.
 * Broadcasts resource usage metrics in real-time.
 */
export const resourceUsageUpdateSchema = z.object({
  type: z.literal("resource_usage_update"),
  usage: resourceUsageSchema,
});

/** TypeScript type for resource usage updates. */
export type ResourceUsageUpdate = z.infer<typeof resourceUsageUpdateSchema>;

/**
 * Zod schema for union of all agent WebSocket message types.
 * Supports status updates, task updates, and resource usage updates.
 */
export const agentWebSocketMessageSchema = z.union([
  agentStatusUpdateSchema,
  taskStatusUpdateSchema,
  resourceUsageUpdateSchema,
]);

/** TypeScript type for agent WebSocket messages. */
export type AgentWebSocketMessage = z.infer<typeof agentWebSocketMessageSchema>;

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

/**
 * Form schema for creating and editing agents.
 * Includes validation for agent configuration and runtime settings.
 */
export const agentFormSchema = z.object({
  description: z.string().max(500).optional(),
  enableLogging: z.boolean().default(true),
  enableMetrics: z.boolean().default(true),
  maxConcurrentTasks: z.number().int().positive().max(10).default(3),
  name: z
    .string()
    .min(1, { error: "Agent name is required" })
    .max(100, { error: "Name too long" }),
  priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
  retryAttempts: z.number().int().nonnegative().max(5).default(3),
  timeoutMs: z.number().int().positive().max(300000).default(30000),
  type: z
    .string()
    .min(1, { error: "Agent type is required" })
    .max(50, { error: "Type too long" }),
});

/** TypeScript type for agent form data. */
export type AgentFormData = z.infer<typeof agentFormSchema>;

/**
 * Form schema for creating and editing agent tasks.
 * Includes validation for task details and priority.
 */
export const taskFormSchema = z.object({
  agentId: primitiveSchemas.uuid,
  description: z.string().max(1000, { error: "Description too long" }),
  priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
  title: z
    .string()
    .min(1, { error: "Task title is required" })
    .max(200, { error: "Title too long" }),
});

/** TypeScript type for task form data. */
export type TaskFormData = z.infer<typeof taskFormSchema>;

/**
 * Form schema for creating and editing agent workflows.
 * Includes validation for workflow configuration and connections.
 */
export const workflowFormSchema = z.object({
  agents: z
    .array(primitiveSchemas.uuid)
    .min(1, { error: "At least one agent is required" }),
  connections: z.array(
    z.object({
      condition: z.string().max(500).optional(),
      from: primitiveSchemas.uuid,
      to: primitiveSchemas.uuid,
    })
  ),
  description: z.string().max(500).optional(),
  name: z
    .string()
    .min(1, { error: "Workflow name is required" })
    .max(100, { error: "Name too long" }),
});

/** TypeScript type for workflow form data. */
export type WorkflowFormData = z.infer<typeof workflowFormSchema>;

// ===== UTILITY FUNCTIONS =====
// Validation helpers and business logic functions

/**
 * Validates agent data from external sources.
 * Performs comprehensive validation of agent entities.
 *
 * @param data - Raw agent data to validate
 * @returns Parsed and validated agent data
 * @throws {ZodError} When validation fails with detailed error information
 */
export const validateAgentData = (data: unknown): Agent => {
  return agentSchema.parse(data);
};

/**
 * Validates agent task data from external sources.
 * Ensures task details meet business requirements.
 *
 * @param data - Raw task data to validate
 * @returns Parsed and validated task data
 * @throws {ZodError} When validation fails with detailed error information
 */
export const validateAgentTask = (data: unknown): AgentTask => {
  return agentTaskSchema.parse(data);
};

/**
 * Validates workflow data from external sources.
 * Ensures workflow configuration is valid.
 *
 * @param data - Raw workflow data to validate
 * @returns Parsed and validated workflow data
 * @throws {ZodError} When validation fails with detailed error information
 */
export const validateWorkflow = (data: unknown): AgentWorkflowEntity => {
  return agentWorkflowEntitySchema.parse(data);
};

/**
 * Safely validates agent data with error handling.
 *
 * @param data - Raw agent data to validate
 * @returns Validation result with success/error information
 */
export const safeValidateAgent = (data: unknown) => {
  return agentSchema.safeParse(data);
};

/**
 * Safely validates task data with error handling.
 *
 * @param data - Raw task data to validate
 * @returns Validation result with success/error information
 */
export const safeValidateTask = (data: unknown) => {
  return agentTaskSchema.safeParse(data);
};

/**
 * Safely validates workflow data with error handling.
 *
 * @param data - Raw workflow data to validate
 * @returns Validation result with success/error information
 */
export const safeValidateWorkflow = (data: unknown) => {
  return agentWorkflowEntitySchema.safeParse(data);
};

/**
 * Calculates agent success rate from metrics.
 * Computes the ratio of completed tasks to total tasks.
 *
 * @param metrics - Agent metrics containing task completion data
 * @returns Success rate as a number between 0 and 1
 */
export const calculateSuccessRate = (metrics: AgentMetrics): number => {
  const total = metrics.tasksCompleted + metrics.tasksFailed;
  if (total === 0) return 0;
  return metrics.tasksCompleted / total;
};

/**
 * Checks if an agent is currently active.
 * Determines if agent is in an active execution state.
 *
 * @param agent - Agent entity to check
 * @returns True if agent is active, false otherwise
 */
export const isAgentActive = (agent: Agent): boolean => {
  return ["active", "thinking", "executing"].includes(agent.status);
};

/**
 * Gets the current load (active tasks) for an agent.
 * Counts tasks that are currently in progress.
 *
 * @param agent - Agent entity to analyze
 * @returns Number of active tasks
 */
export const getAgentLoad = (agent: Agent): number => {
  const activeTasks = agent.tasks.filter(
    (task) => task.status === "in_progress"
  ).length;
  return activeTasks;
};

/**
 * Determines if an agent can accept a new task.
 * Checks agent status and concurrency limits.
 *
 * @param agent - Agent entity to check
 * @param config - Optional runtime configuration for concurrency limits
 * @returns True if agent can accept new tasks, false otherwise
 */
export const canAcceptNewTask = (
  agent: Agent,
  config?: AgentRuntimeConfig
): boolean => {
  if (!isAgentActive(agent)) return false;

  const maxTasks = config?.maxConcurrentTasks || 3;
  const currentLoad = getAgentLoad(agent);

  return currentLoad < maxTasks;
};
