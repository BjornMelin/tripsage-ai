/**
 * @fileoverview Zod schemas for agent status tracking and validation.
 */

import { z } from "zod";

// Common validation patterns
const UUID_SCHEMA = z.uuid();
const DATE_STRING_SCHEMA = z.iso.datetime();
const PROGRESS_SCHEMA = z.number().int().min(0).max(100);

// Agent status type enum
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

// Task status enum
export const taskStatusSchema = z.enum([
  "pending",
  "in_progress",
  "completed",
  "failed",
]);

// Session status enum
export const sessionStatusSchema = z.enum(["active", "completed", "error"]);

// Agent task schema
export const agentTaskSchema = z.object({
  completedAt: DATE_STRING_SCHEMA.optional(),
  createdAt: DATE_STRING_SCHEMA,
  description: z.string().max(1000, "Description too long"),
  error: z.string().max(500).optional(),
  id: UUID_SCHEMA,
  progress: PROGRESS_SCHEMA.optional(),
  status: taskStatusSchema,
  title: z.string().min(1, "Task title is required").max(200, "Title too long"),
  updatedAt: DATE_STRING_SCHEMA,
});

// Agent schema
export const agentSchema = z.object({
  createdAt: DATE_STRING_SCHEMA,
  currentTaskId: UUID_SCHEMA.optional(),
  description: z.string().max(500).optional(),
  id: UUID_SCHEMA,
  metadata: z.record(z.string(), z.unknown()).optional(),
  name: z.string().min(1, "Agent name is required").max(100, "Name too long"),
  progress: PROGRESS_SCHEMA,
  status: agentStatusTypeSchema,
  tasks: z.array(agentTaskSchema),
  type: z.string().min(1, "Agent type is required").max(50, "Type too long"),
  updatedAt: DATE_STRING_SCHEMA,
});

// Agent activity schema
export const agentActivitySchema = z.object({
  agentId: UUID_SCHEMA,
  id: UUID_SCHEMA,
  message: z
    .string()
    .min(1, "Activity message is required")
    .max(1000, "Message too long"),
  metadata: z.record(z.string(), z.unknown()).optional(),
  timestamp: DATE_STRING_SCHEMA,
  type: z.string().min(1, "Activity type is required").max(50, "Type too long"),
});

// Resource usage schema
export const resourceUsageSchema = z.object({
  activeAgents: z.number().int().nonnegative(),
  cpuUsage: z.number().min(0).max(100),
  memoryUsage: z.number().min(0).max(100),
  networkRequests: z.number().int().nonnegative(),
  timestamp: DATE_STRING_SCHEMA,
});

// Agent session schema
export const agentSessionSchema = z.object({
  activities: z.array(agentActivitySchema),
  agents: z.array(agentSchema),
  endedAt: DATE_STRING_SCHEMA.optional(),
  id: UUID_SCHEMA,
  resourceUsage: z.array(resourceUsageSchema),
  startedAt: DATE_STRING_SCHEMA,
  status: sessionStatusSchema,
});

// Workflow connection schema
export const workflowConnectionSchema = z.object({
  condition: z.string().max(500).optional(),
  from: UUID_SCHEMA,
  to: UUID_SCHEMA,
});

// Agent workflow schema
export const agentWorkflowSchema = z.object({
  agents: z.array(UUID_SCHEMA).min(1, "At least one agent is required"),
  connections: z.array(workflowConnectionSchema),
  createdAt: DATE_STRING_SCHEMA,
  description: z.string().max(500).optional(),
  id: UUID_SCHEMA,
  name: z.string().min(1, "Workflow name is required").max(100, "Name too long"),
  updatedAt: DATE_STRING_SCHEMA,
});

// Agent configuration schema
export const agentConfigSchema = z.object({
  agentId: UUID_SCHEMA,
  createdAt: DATE_STRING_SCHEMA,
  customSettings: z.record(z.string(), z.unknown()).optional(),
  enableLogging: z.boolean(),
  enableMetrics: z.boolean(),
  id: UUID_SCHEMA,
  maxConcurrentTasks: z.number().int().positive().max(10),
  priority: z.enum(["low", "normal", "high", "critical"]),
  retryAttempts: z.number().int().nonnegative().max(5),
  timeoutMs: z.number().int().positive().max(300000), // 5 minutes max
  updatedAt: DATE_STRING_SCHEMA,
});

// Agent metrics schema
export const agentMetricsSchema = z.object({
  agentId: UUID_SCHEMA,
  averageExecutionTime: z.number().nonnegative(),
  createdAt: DATE_STRING_SCHEMA,
  lastActive: DATE_STRING_SCHEMA.optional(),
  successRate: z.number().min(0).max(1),
  tasksCompleted: z.number().int().nonnegative(),
  tasksFailed: z.number().int().nonnegative(),
  totalExecutionTime: z.number().nonnegative(),
  updatedAt: DATE_STRING_SCHEMA,
});

// Agent state schema for Zustand stores
export const agentStateSchema = z.object({
  activeAgentIds: z.array(UUID_SCHEMA),
  activities: z.array(agentActivitySchema),
  agents: z.record(UUID_SCHEMA, agentSchema),
  currentSessionId: UUID_SCHEMA.nullable(),
  error: z.string().nullable(),
  isLoading: z.boolean(),
  lastUpdated: DATE_STRING_SCHEMA.nullable(),
  metrics: z.record(UUID_SCHEMA, agentMetricsSchema),
  resourceUsage: resourceUsageSchema.nullable(),
  sessions: z.record(UUID_SCHEMA, agentSessionSchema),
  workflows: z.record(UUID_SCHEMA, agentWorkflowSchema),
});

// API Request schemas
export const createAgentTaskRequestSchema = z.object({
  agentId: UUID_SCHEMA,
  description: z.string().max(1000, "Description too long"),
  metadata: z.record(z.string(), z.unknown()).optional(),
  priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
  title: z.string().min(1, "Task title is required").max(200, "Title too long"),
});

export const updateAgentTaskRequestSchema = z.object({
  description: z.string().max(1000).optional(),
  error: z.string().max(500).optional(),
  id: UUID_SCHEMA,
  progress: PROGRESS_SCHEMA.optional(),
  status: taskStatusSchema.optional(),
  title: z.string().min(1).max(200).optional(),
});

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
  name: z.string().min(1, "Agent name is required").max(100, "Name too long"),
  type: z.string().min(1, "Agent type is required").max(50, "Type too long"),
});

export const updateAgentRequestSchema = z.object({
  description: z.string().max(500).optional(),
  id: UUID_SCHEMA,
  metadata: z.record(z.string(), z.unknown()).optional(),
  name: z.string().min(1).max(100).optional(),
  status: agentStatusTypeSchema.optional(),
});

export const createWorkflowRequestSchema = z.object({
  agents: z.array(UUID_SCHEMA).min(1, "At least one agent is required"),
  connections: z.array(workflowConnectionSchema),
  description: z.string().max(500).optional(),
  name: z.string().min(1, "Workflow name is required").max(100, "Name too long"),
});

export const updateWorkflowRequestSchema = z.object({
  agents: z.array(UUID_SCHEMA).min(1).optional(),
  connections: z.array(workflowConnectionSchema).optional(),
  description: z.string().max(500).optional(),
  id: UUID_SCHEMA,
  name: z.string().min(1).max(100).optional(),
});

// WebSocket message schemas for real-time updates
export const agentStatusUpdateSchema = z.object({
  agentId: UUID_SCHEMA,
  currentTaskId: UUID_SCHEMA.optional(),
  progress: PROGRESS_SCHEMA.optional(),
  status: agentStatusTypeSchema,
  timestamp: DATE_STRING_SCHEMA,
  type: z.literal("agent_status_update"),
});

export const taskStatusUpdateSchema = z.object({
  agentId: UUID_SCHEMA,
  error: z.string().optional(),
  progress: PROGRESS_SCHEMA.optional(),
  status: taskStatusSchema,
  taskId: UUID_SCHEMA,
  timestamp: DATE_STRING_SCHEMA,
  type: z.literal("task_status_update"),
});

export const resourceUsageUpdateSchema = z.object({
  type: z.literal("resource_usage_update"),
  usage: resourceUsageSchema,
});

export const agentWebSocketMessageSchema = z.union([
  agentStatusUpdateSchema,
  taskStatusUpdateSchema,
  resourceUsageUpdateSchema,
]);

// Form schemas for React Hook Form
export const agentFormSchema = z.object({
  description: z.string().max(500).optional(),
  enableLogging: z.boolean().default(true),
  enableMetrics: z.boolean().default(true),
  maxConcurrentTasks: z.number().int().positive().max(10).default(3),
  name: z.string().min(1, "Agent name is required").max(100, "Name too long"),
  priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
  retryAttempts: z.number().int().nonnegative().max(5).default(3),
  timeoutMs: z.number().int().positive().max(300000).default(30000),
  type: z.string().min(1, "Agent type is required").max(50, "Type too long"),
});

export const taskFormSchema = z.object({
  agentId: UUID_SCHEMA,
  description: z.string().max(1000, "Description too long"),
  priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
  title: z.string().min(1, "Task title is required").max(200, "Title too long"),
});

export const workflowFormSchema = z.object({
  agents: z.array(UUID_SCHEMA).min(1, "At least one agent is required"),
  connections: z.array(
    z.object({
      condition: z.string().max(500).optional(),
      from: UUID_SCHEMA,
      to: UUID_SCHEMA,
    })
  ),
  description: z.string().max(500).optional(),
  name: z.string().min(1, "Workflow name is required").max(100, "Name too long"),
});

// Validation utilities
export const validateAgentData = (data: unknown) => {
  return agentSchema.parse(data);
};

export const validateAgentTask = (data: unknown) => {
  return agentTaskSchema.parse(data);
};

export const validateWorkflow = (data: unknown) => {
  return agentWorkflowSchema.parse(data);
};

export const safeValidateAgent = (data: unknown) => {
  return agentSchema.safeParse(data);
};

export const safeValidateTask = (data: unknown) => {
  return agentTaskSchema.safeParse(data);
};

export const safeValidateWorkflow = (data: unknown) => {
  return agentWorkflowSchema.safeParse(data);
};

// Helper functions
export const calculateSuccessRate = (metrics: AgentMetrics): number => {
  const total = metrics.tasksCompleted + metrics.tasksFailed;
  if (total === 0) return 0;
  return metrics.tasksCompleted / total;
};

export const isAgentActive = (agent: Agent): boolean => {
  return ["active", "thinking", "executing"].includes(agent.status);
};

export const getAgentLoad = (agent: Agent): number => {
  const activeTasks = agent.tasks.filter(
    (task) => task.status === "in_progress"
  ).length;
  return activeTasks;
};

export const canAcceptNewTask = (agent: Agent, config?: AgentConfig): boolean => {
  if (!isAgentActive(agent)) return false;

  const maxTasks = config?.maxConcurrentTasks || 3;
  const currentLoad = getAgentLoad(agent);

  return currentLoad < maxTasks;
};

// Type exports
export type AgentStatusType = z.infer<typeof agentStatusTypeSchema>;
export type TaskStatus = z.infer<typeof taskStatusSchema>;
export type SessionStatus = z.infer<typeof sessionStatusSchema>;
export type AgentTask = z.infer<typeof agentTaskSchema>;
export type Agent = z.infer<typeof agentSchema>;
export type AgentActivity = z.infer<typeof agentActivitySchema>;
export type ResourceUsage = z.infer<typeof resourceUsageSchema>;
export type AgentSession = z.infer<typeof agentSessionSchema>;
export type WorkflowConnection = z.infer<typeof workflowConnectionSchema>;
export type AgentWorkflow = z.infer<typeof agentWorkflowSchema>;
export type AgentConfig = z.infer<typeof agentConfigSchema>;
export type AgentMetrics = z.infer<typeof agentMetricsSchema>;
export type AgentState = z.infer<typeof agentStateSchema>;
export type CreateAgentTaskRequest = z.infer<typeof createAgentTaskRequestSchema>;
export type UpdateAgentTaskRequest = z.infer<typeof updateAgentTaskRequestSchema>;
export type CreateAgentRequest = z.infer<typeof createAgentRequestSchema>;
export type UpdateAgentRequest = z.infer<typeof updateAgentRequestSchema>;
export type CreateWorkflowRequest = z.infer<typeof createWorkflowRequestSchema>;
export type UpdateWorkflowRequest = z.infer<typeof updateWorkflowRequestSchema>;
export type AgentStatusUpdate = z.infer<typeof agentStatusUpdateSchema>;
export type TaskStatusUpdate = z.infer<typeof taskStatusUpdateSchema>;
export type ResourceUsageUpdate = z.infer<typeof resourceUsageUpdateSchema>;
export type AgentWebSocketMessage = z.infer<typeof agentWebSocketMessageSchema>;
export type AgentFormData = z.infer<typeof agentFormSchema>;
export type TaskFormData = z.infer<typeof taskFormSchema>;
export type WorkflowFormData = z.infer<typeof workflowFormSchema>;
