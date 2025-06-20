/**
 * Comprehensive Zod schemas for Agent Status tracking
 * Runtime validation for all agent-related data types
 */

import { z } from "zod";

// Common validation patterns
const uuidSchema = z.string().uuid();
const dateStringSchema = z.string().datetime();
const progressSchema = z.number().int().min(0).max(100);

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
  id: uuidSchema,
  title: z.string().min(1, "Task title is required").max(200, "Title too long"),
  description: z.string().max(1000, "Description too long"),
  status: taskStatusSchema,
  progress: progressSchema.optional(),
  createdAt: dateStringSchema,
  updatedAt: dateStringSchema,
  completedAt: dateStringSchema.optional(),
  error: z.string().max(500).optional(),
});

// Agent schema
export const agentSchema = z.object({
  id: uuidSchema,
  name: z.string().min(1, "Agent name is required").max(100, "Name too long"),
  type: z.string().min(1, "Agent type is required").max(50, "Type too long"),
  description: z.string().max(500).optional(),
  status: agentStatusTypeSchema,
  currentTaskId: uuidSchema.optional(),
  progress: progressSchema,
  tasks: z.array(agentTaskSchema),
  createdAt: dateStringSchema,
  updatedAt: dateStringSchema,
  metadata: z.record(z.unknown()).optional(),
});

// Agent activity schema
export const agentActivitySchema = z.object({
  id: uuidSchema,
  agentId: uuidSchema,
  type: z.string().min(1, "Activity type is required").max(50, "Type too long"),
  message: z
    .string()
    .min(1, "Activity message is required")
    .max(1000, "Message too long"),
  metadata: z.record(z.unknown()).optional(),
  timestamp: dateStringSchema,
});

// Resource usage schema
export const resourceUsageSchema = z.object({
  cpuUsage: z.number().min(0).max(100),
  memoryUsage: z.number().min(0).max(100),
  networkRequests: z.number().int().nonnegative(),
  activeAgents: z.number().int().nonnegative(),
  timestamp: dateStringSchema,
});

// Agent session schema
export const agentSessionSchema = z.object({
  id: uuidSchema,
  agents: z.array(agentSchema),
  activities: z.array(agentActivitySchema),
  resourceUsage: z.array(resourceUsageSchema),
  startedAt: dateStringSchema,
  endedAt: dateStringSchema.optional(),
  status: sessionStatusSchema,
});

// Workflow connection schema
export const workflowConnectionSchema = z.object({
  from: uuidSchema,
  to: uuidSchema,
  condition: z.string().max(500).optional(),
});

// Agent workflow schema
export const agentWorkflowSchema = z.object({
  id: uuidSchema,
  name: z.string().min(1, "Workflow name is required").max(100, "Name too long"),
  description: z.string().max(500).optional(),
  agents: z.array(uuidSchema).min(1, "At least one agent is required"),
  connections: z.array(workflowConnectionSchema),
  createdAt: dateStringSchema,
  updatedAt: dateStringSchema,
});

// Agent configuration schema
export const agentConfigSchema = z.object({
  id: uuidSchema,
  agentId: uuidSchema,
  maxConcurrentTasks: z.number().int().positive().max(10),
  timeoutMs: z.number().int().positive().max(300000), // 5 minutes max
  retryAttempts: z.number().int().nonnegative().max(5),
  priority: z.enum(["low", "normal", "high", "critical"]),
  enableLogging: z.boolean(),
  enableMetrics: z.boolean(),
  customSettings: z.record(z.unknown()).optional(),
  createdAt: dateStringSchema,
  updatedAt: dateStringSchema,
});

// Agent metrics schema
export const agentMetricsSchema = z.object({
  agentId: uuidSchema,
  tasksCompleted: z.number().int().nonnegative(),
  tasksFailed: z.number().int().nonnegative(),
  averageExecutionTime: z.number().nonnegative(),
  totalExecutionTime: z.number().nonnegative(),
  successRate: z.number().min(0).max(1),
  lastActive: dateStringSchema.optional(),
  createdAt: dateStringSchema,
  updatedAt: dateStringSchema,
});

// Agent state schema for Zustand stores
export const agentStateSchema = z.object({
  agents: z.record(uuidSchema, agentSchema),
  sessions: z.record(uuidSchema, agentSessionSchema),
  workflows: z.record(uuidSchema, agentWorkflowSchema),
  activities: z.array(agentActivitySchema),
  currentSessionId: uuidSchema.nullable(),
  activeAgentIds: z.array(uuidSchema),
  resourceUsage: resourceUsageSchema.nullable(),
  metrics: z.record(uuidSchema, agentMetricsSchema),
  isLoading: z.boolean(),
  error: z.string().nullable(),
  lastUpdated: dateStringSchema.nullable(),
});

// API Request schemas
export const createAgentTaskRequestSchema = z.object({
  agentId: uuidSchema,
  title: z.string().min(1, "Task title is required").max(200, "Title too long"),
  description: z.string().max(1000, "Description too long"),
  priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
  metadata: z.record(z.unknown()).optional(),
});

export const updateAgentTaskRequestSchema = z.object({
  id: uuidSchema,
  title: z.string().min(1).max(200).optional(),
  description: z.string().max(1000).optional(),
  status: taskStatusSchema.optional(),
  progress: progressSchema.optional(),
  error: z.string().max(500).optional(),
});

export const createAgentRequestSchema = z.object({
  name: z.string().min(1, "Agent name is required").max(100, "Name too long"),
  type: z.string().min(1, "Agent type is required").max(50, "Type too long"),
  description: z.string().max(500).optional(),
  config: z
    .object({
      maxConcurrentTasks: z.number().int().positive().max(10).default(3),
      timeoutMs: z.number().int().positive().max(300000).default(30000),
      retryAttempts: z.number().int().nonnegative().max(5).default(3),
      priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
      enableLogging: z.boolean().default(true),
      enableMetrics: z.boolean().default(true),
    })
    .optional(),
  metadata: z.record(z.unknown()).optional(),
});

export const updateAgentRequestSchema = z.object({
  id: uuidSchema,
  name: z.string().min(1).max(100).optional(),
  description: z.string().max(500).optional(),
  status: agentStatusTypeSchema.optional(),
  metadata: z.record(z.unknown()).optional(),
});

export const createWorkflowRequestSchema = z.object({
  name: z.string().min(1, "Workflow name is required").max(100, "Name too long"),
  description: z.string().max(500).optional(),
  agents: z.array(uuidSchema).min(1, "At least one agent is required"),
  connections: z.array(workflowConnectionSchema),
});

export const updateWorkflowRequestSchema = z.object({
  id: uuidSchema,
  name: z.string().min(1).max(100).optional(),
  description: z.string().max(500).optional(),
  agents: z.array(uuidSchema).min(1).optional(),
  connections: z.array(workflowConnectionSchema).optional(),
});

// WebSocket message schemas for real-time updates
export const agentStatusUpdateSchema = z.object({
  type: z.literal("agent_status_update"),
  agentId: uuidSchema,
  status: agentStatusTypeSchema,
  progress: progressSchema.optional(),
  currentTaskId: uuidSchema.optional(),
  timestamp: dateStringSchema,
});

export const taskStatusUpdateSchema = z.object({
  type: z.literal("task_status_update"),
  taskId: uuidSchema,
  agentId: uuidSchema,
  status: taskStatusSchema,
  progress: progressSchema.optional(),
  error: z.string().optional(),
  timestamp: dateStringSchema,
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
  name: z.string().min(1, "Agent name is required").max(100, "Name too long"),
  type: z.string().min(1, "Agent type is required").max(50, "Type too long"),
  description: z.string().max(500).optional(),
  maxConcurrentTasks: z.number().int().positive().max(10).default(3),
  timeoutMs: z.number().int().positive().max(300000).default(30000),
  retryAttempts: z.number().int().nonnegative().max(5).default(3),
  priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
  enableLogging: z.boolean().default(true),
  enableMetrics: z.boolean().default(true),
});

export const taskFormSchema = z.object({
  agentId: uuidSchema,
  title: z.string().min(1, "Task title is required").max(200, "Title too long"),
  description: z.string().max(1000, "Description too long"),
  priority: z.enum(["low", "normal", "high", "critical"]).default("normal"),
});

export const workflowFormSchema = z.object({
  name: z.string().min(1, "Workflow name is required").max(100, "Name too long"),
  description: z.string().max(500).optional(),
  agents: z.array(uuidSchema).min(1, "At least one agent is required"),
  connections: z.array(
    z.object({
      from: uuidSchema,
      to: uuidSchema,
      condition: z.string().max(500).optional(),
    })
  ),
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
