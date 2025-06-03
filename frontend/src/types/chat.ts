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

// Enhanced tool call schema that matches backend
export const ToolCallSchema = z.object({
  id: z.string(),
  name: z.string(),
  arguments: z.record(z.any()).optional(),
  status: ToolCallStatusSchema.optional().default("pending"),
  result: z.any().optional(),
  error: z.string().optional(),
  executionTime: z.number().optional(),
  sessionId: z.string().optional(),
  messageId: z.string().optional(),
});
export type ToolCall = z.infer<typeof ToolCallSchema>;

// Tool result schema for displaying results
export const ToolResultSchema = z.object({
  callId: z.string(),
  result: z.any(),
  status: z.enum(["success", "error"]),
  executionTime: z.number().optional(),
  errorMessage: z.string().optional(),
});
export type ToolResult = z.infer<typeof ToolResultSchema>;

// Message part for text content
export const TextPartSchema = z.object({
  type: z.literal("text"),
  text: z.string(),
});
export type TextPart = z.infer<typeof TextPartSchema>;

// Union of message part types (simplified without legacy tool invocation)
export const MessagePartSchema = z.discriminatedUnion("type", [
  TextPartSchema,
]);
export type MessagePart = z.infer<typeof MessagePartSchema>;

// Attachment schema for files
export const AttachmentSchema = z.object({
  id: z.string(),
  url: z.string(),
  name: z.string().optional(),
  contentType: z.string().optional(),
  size: z.number().optional(),
});
export type Attachment = z.infer<typeof AttachmentSchema>;

// Message schema
export const MessageSchema = z.object({
  id: z.string(),
  role: MessageRoleSchema,
  content: z.string().optional(),
  parts: z.array(MessagePartSchema).optional(),
  createdAt: z.date().or(z.string().datetime()),
  updatedAt: z.date().or(z.string().datetime()).optional(),
  attachments: z.array(AttachmentSchema).optional(),
  annotations: z.record(z.any()).optional(),
  // Enhanced tool calling support
  toolCalls: z.array(ToolCallSchema).optional(),
  toolResults: z.array(ToolResultSchema).optional(),
  // Agent routing information
  routedTo: z.string().optional(),
  routingConfidence: z.number().optional(),
  intentDetected: z.record(z.any()).optional(),
  handledBy: z.string().optional(),
});
export type Message = z.infer<typeof MessageSchema>;

// Chat session schema
export const ChatSessionSchema = z.object({
  id: z.string(),
  title: z.string(),
  createdAt: z.date().or(z.string().datetime()),
  updatedAt: z.date().or(z.string().datetime()),
  messages: z.array(MessageSchema).optional(),
  metadata: z.record(z.any()).optional(),
});
export type ChatSession = z.infer<typeof ChatSessionSchema>;

// Chat store state schema
export const ChatStoreStateSchema = z.object({
  sessions: z.array(ChatSessionSchema),
  currentSessionId: z.string().nullable(),
  status: z.enum(["idle", "loading", "streaming", "error"]),
  error: z.string().nullable(),
});
export type ChatStoreState = z.infer<typeof ChatStoreStateSchema>;

// Agent status schema
export const AgentStatusSchema = z.object({
  isActive: z.boolean(),
  currentTask: z.string().nullable(),
  progress: z.number().min(0).max(100),
  statusMessage: z.string().optional(),
});
export type AgentStatus = z.infer<typeof AgentStatusSchema>;

// Chat completion request schema
export const ChatCompletionRequestSchema = z.object({
  messages: z.array(MessageSchema),
  systemPrompt: z.string().optional(),
  temperature: z.number().min(0).max(2).optional(),
  maxTokens: z.number().positive().optional(),
  stream: z.boolean().optional(),
  tools: z.array(z.any()).optional(),
  attachments: z.array(AttachmentSchema).optional(),
});
export type ChatCompletionRequest = z.infer<typeof ChatCompletionRequestSchema>;

// Chat completion response schema
export const ChatCompletionResponseSchema = z.object({
  id: z.string(),
  message: MessageSchema,
  usage: z
    .object({
      promptTokens: z.number(),
      completionTokens: z.number(),
      totalTokens: z.number(),
    })
    .optional(),
});
export type ChatCompletionResponse = z.infer<
  typeof ChatCompletionResponseSchema
>;
