/**
 * @fileoverview Chat types and enums used across messaging features.
 * Includes Zod-backed role/schema helpers for validation.
 */
import { z } from "zod";

// Message role schema
export const MessageRoleSchema = z.enum(["user", "assistant", "system"]);
export type MessageRole = z.infer<typeof MessageRoleSchema>;

// Tool call state schema
export const ToolCallStateSchema = z.enum(["partial-call", "call", "result"]);
export type ToolCallState = z.infer<typeof ToolCallStateSchema>;

// Tool call status schema for execution tracking
export const ToolCallStatusSchema = z.enum([
  "pending",
  "executing",
  "completed",
  "error",
  "cancelled",
]);
export type ToolCallStatus = z.infer<typeof ToolCallStatusSchema>;

// tool call schema that matches backend
export const ToolCallSchema = z.object({
  arguments: z.record(z.string(), z.unknown()).optional(),
  error: z.string().optional(),
  executionTime: z.number().optional(),
  id: z.string(),
  messageId: z.string().optional(),
  name: z.string(),
  result: z.unknown().optional(),
  sessionId: z.string().optional(),
  status: ToolCallStatusSchema.optional().default("pending"),
});
export type ToolCall = z.infer<typeof ToolCallSchema>;

// Tool result schema for displaying results
export const ToolResultSchema = z.object({
  callId: z.string(),
  errorMessage: z.string().optional(),
  executionTime: z.number().optional(),
  result: z.unknown(),
  status: z.enum(["success", "error"]),
});
export type ToolResult = z.infer<typeof ToolResultSchema>;

// Message part for text content
export const TextPartSchema = z.object({
  text: z.string(),
  type: z.literal("text"),
});
export type TextPart = z.infer<typeof TextPartSchema>;

// Union of message part types (simplified without legacy tool invocation)
export const MessagePartSchema = z.discriminatedUnion("type", [TextPartSchema]);
export type MessagePart = z.infer<typeof MessagePartSchema>;

// Attachment schema for files
export const AttachmentSchema = z.object({
  contentType: z.string().optional(),
  id: z.string(),
  name: z.string().optional(),
  size: z.number().optional(),
  url: z.string(),
});
export type Attachment = z.infer<typeof AttachmentSchema>;

// Message schema
export const MessageSchema = z.object({
  annotations: z.record(z.string(), z.unknown()).optional(),
  attachments: z.array(AttachmentSchema).optional(),
  content: z.string().optional(),
  createdAt: z.date().or(z.string().datetime()),
  handledBy: z.string().optional(),
  id: z.string(),
  intentDetected: z.record(z.string(), z.unknown()).optional(),
  parts: z.array(MessagePartSchema).optional(),
  role: MessageRoleSchema,
  // Agent routing information
  routedTo: z.string().optional(),
  routingConfidence: z.number().optional(),
  // tool calling support
  toolCalls: z.array(ToolCallSchema).optional(),
  toolResults: z.array(ToolResultSchema).optional(),
  updatedAt: z.date().or(z.string().datetime()).optional(),
});
export type Message = z.infer<typeof MessageSchema>;

// Chat session schema
export const ChatSessionSchema = z.object({
  createdAt: z.date().or(z.string().datetime()),
  id: z.string(),
  messages: z.array(MessageSchema).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  title: z.string(),
  updatedAt: z.date().or(z.string().datetime()),
});
export type ChatSession = z.infer<typeof ChatSessionSchema>;

// Chat store state schema
export const ChatStoreStateSchema = z.object({
  currentSessionId: z.string().nullable(),
  error: z.string().nullable(),
  sessions: z.array(ChatSessionSchema),
  status: z.enum(["idle", "loading", "streaming", "error"]),
});
export type ChatStoreState = z.infer<typeof ChatStoreStateSchema>;

// Agent status schema
export const AgentStatusSchema = z.object({
  currentTask: z.string().nullable(),
  isActive: z.boolean(),
  progress: z.number().min(0).max(100),
  statusMessage: z.string().optional(),
});
export type AgentStatus = z.infer<typeof AgentStatusSchema>;

// Chat completion request schema
export const ChatCompletionRequestSchema = z.object({
  attachments: z.array(AttachmentSchema).optional(),
  maxTokens: z.number().positive().optional(),
  messages: z.array(MessageSchema),
  model: z.string().optional(),
  temperature: z.number().min(0).max(2).optional(),
  tools: z.array(z.string()).optional(),
});
export type ChatCompletionRequest = z.infer<typeof ChatCompletionRequestSchema>;

// Chat completion response schema
export const ChatCompletionResponseSchema = z.object({
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
export type ChatCompletionResponse = z.infer<typeof ChatCompletionResponseSchema>;
