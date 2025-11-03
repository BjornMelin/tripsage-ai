/**
 * @fileoverview Chat types and enums used across messaging features.
 * Includes Zod-backed role/schema helpers for validation.
 */
import { z } from "zod";

// Message role schema
export const MESSAGE_ROLE_SCHEMA = z.enum(["user", "assistant", "system"]);
export type MessageRole = z.infer<typeof MESSAGE_ROLE_SCHEMA>;

// Tool call state schema
export const TOOL_CALL_STATE_SCHEMA = z.enum(["partial-call", "call", "result"]);
export type ToolCallState = z.infer<typeof TOOL_CALL_STATE_SCHEMA>;

// Tool call status schema for execution tracking
export const TOOL_CALL_STATUS_SCHEMA = z.enum([
  "pending",
  "executing",
  "completed",
  "error",
  "cancelled",
]);
export type ToolCallStatus = z.infer<typeof TOOL_CALL_STATUS_SCHEMA>;

// tool call schema that matches backend
export const TOOL_CALL_SCHEMA = z.object({
  arguments: z.record(z.string(), z.unknown()).optional(),
  error: z.string().optional(),
  executionTime: z.number().optional(),
  id: z.string(),
  messageId: z.string().optional(),
  name: z.string(),
  result: z.unknown().optional(),
  sessionId: z.string().optional(),
  status: TOOL_CALL_STATUS_SCHEMA.optional().default("pending"),
});
export type ToolCall = z.infer<typeof TOOL_CALL_SCHEMA>;

// Tool result schema for displaying results
export const TOOL_RESULT_SCHEMA = z.object({
  callId: z.string(),
  errorMessage: z.string().optional(),
  executionTime: z.number().optional(),
  result: z.unknown(),
  status: z.enum(["success", "error"]),
});
export type ToolResult = z.infer<typeof TOOL_RESULT_SCHEMA>;

// Message part for text content
export const TEXT_PART_SCHEMA = z.object({
  text: z.string(),
  type: z.literal("text"),
});
export type TextPart = z.infer<typeof TEXT_PART_SCHEMA>;

// Union of message part types (simplified without legacy tool invocation)
export const MESSAGE_PART_SCHEMA = z.discriminatedUnion("type", [TEXT_PART_SCHEMA]);
export type MessagePart = z.infer<typeof MESSAGE_PART_SCHEMA>;

// Attachment schema for files
export const ATTACHMENT_SCHEMA = z.object({
  contentType: z.string().optional(),
  id: z.string(),
  name: z.string().optional(),
  size: z.number().optional(),
  url: z.string(),
});
export type Attachment = z.infer<typeof ATTACHMENT_SCHEMA>;

// Message schema
export const MESSAGE_SCHEMA = z.object({
  annotations: z.record(z.string(), z.unknown()).optional(),
  attachments: z.array(ATTACHMENT_SCHEMA).optional(),
  content: z.string().optional(),
  createdAt: z.date().or(z.string().datetime()),
  handledBy: z.string().optional(),
  id: z.string(),
  intentDetected: z.record(z.string(), z.unknown()).optional(),
  parts: z.array(MESSAGE_PART_SCHEMA).optional(),
  role: MESSAGE_ROLE_SCHEMA,
  // Agent routing information
  routedTo: z.string().optional(),
  routingConfidence: z.number().optional(),
  // tool calling support
  toolCalls: z.array(TOOL_CALL_SCHEMA).optional(),
  toolResults: z.array(TOOL_RESULT_SCHEMA).optional(),
  updatedAt: z.date().or(z.string().datetime()).optional(),
});
export type Message = z.infer<typeof MESSAGE_SCHEMA>;

// Chat session schema
export const CHAT_SESSION_SCHEMA = z.object({
  createdAt: z.date().or(z.string().datetime()),
  id: z.string(),
  messages: z.array(MESSAGE_SCHEMA).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  title: z.string(),
  updatedAt: z.date().or(z.string().datetime()),
});
export type ChatSession = z.infer<typeof CHAT_SESSION_SCHEMA>;

// Chat store state schema
export const CHAT_STORE_STATE_SCHEMA = z.object({
  currentSessionId: z.string().nullable(),
  error: z.string().nullable(),
  sessions: z.array(CHAT_SESSION_SCHEMA),
  status: z.enum(["idle", "loading", "streaming", "error"]),
});
export type ChatStoreState = z.infer<typeof CHAT_STORE_STATE_SCHEMA>;

// Agent status schema
export const AGENT_STATUS_SCHEMA = z.object({
  currentTask: z.string().nullable(),
  isActive: z.boolean(),
  progress: z.number().min(0).max(100),
  statusMessage: z.string().optional(),
});
export type AgentStatus = z.infer<typeof AGENT_STATUS_SCHEMA>;

// Chat completion request schema
export const CHAT_COMPLETION_REQUEST_SCHEMA = z.object({
  attachments: z.array(ATTACHMENT_SCHEMA).optional(),
  maxTokens: z.number().positive().optional(),
  messages: z.array(MESSAGE_SCHEMA),
  model: z.string().optional(),
  temperature: z.number().min(0).max(2).optional(),
  tools: z.array(z.string()).optional(),
});
export type ChatCompletionRequest = z.infer<typeof CHAT_COMPLETION_REQUEST_SCHEMA>;

// Chat completion response schema
export const CHAT_COMPLETION_RESPONSE_SCHEMA = z.object({
  content: z.string(),
  durationMs: z.number().optional(),
  model: z.string(),
  reasons: z.array(z.string()).optional(),
  usage: z
    .object({
      completionTokens: z.number().optional(),
      promptTokens: z.number().optional(),
      totalTokens: z.number().optional(),
    })
    .optional(),
});
export type ChatCompletionResponse = z.infer<typeof CHAT_COMPLETION_RESPONSE_SCHEMA>;
