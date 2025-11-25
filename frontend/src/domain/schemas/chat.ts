/**
 * @fileoverview Chat messaging and conversation schemas with validation.
 * Includes message structure, tool calls, attachments, and conversation management.
 */

import { z } from "zod";
import { AGENT_STATUS_BROADCAST_PAYLOAD_SCHEMA } from "./realtime";
import { primitiveSchemas } from "./registry";
import { ATTACHMENT_SCHEMA } from "./shared/media";

// ===== CORE SCHEMAS =====
// Core business logic schemas for chat functionality

/** Zod schema for message roles in chat conversations (system, user, assistant, tool). */
export const messageRoleSchema = z.enum(["user", "assistant", "system"]);

/** TypeScript type for message roles. */
export type MessageRole = z.infer<typeof messageRoleSchema>;

/** Zod schema for tool call execution states during conversation flow. */
export const toolCallStateSchema = z.enum(["partial-call", "call", "result"]);

/** TypeScript type for tool call states. */
export type ToolCallState = z.infer<typeof toolCallStateSchema>;

/** Zod schema for tool call execution status with lifecycle tracking. */
export const toolCallStatusSchema = z.enum([
  "pending",
  "executing",
  "completed",
  "error",
  "cancelled",
]);

/** TypeScript type for tool call status. */
export type ToolCallStatus = z.infer<typeof toolCallStatusSchema>;

/** Zod schema for tool call metadata and execution tracking. */
export const toolCallSchema = z.object({
  arguments: z.record(z.string(), z.unknown()).optional(),
  error: z.string().optional(),
  executionTime: z.number().optional(),
  id: z.string(),
  messageId: z.string().optional(),
  name: z.string(),
  result: z.unknown().optional(),
  sessionId: z.string().optional(),
  status: toolCallStatusSchema.optional().default("pending"),
});

/** TypeScript type for tool calls. */
export type ToolCall = z.infer<typeof toolCallSchema>;

/** Zod schema for tool execution results with success/error status. */
export const toolResultSchema = z.object({
  callId: z.string(),
  errorMessage: z.string().optional(),
  executionTime: z.number().optional(),
  result: z.unknown(),
  status: z.enum(["success", "error"]),
});

/** TypeScript type for tool results. */
export type ToolResult = z.infer<typeof toolResultSchema>;

/** Zod schema for text content parts within messages. */
export const textPartSchema = z.object({
  text: z.string(),
  type: z.literal("text"),
});

/** TypeScript type for text parts. */
export type TextPart = z.infer<typeof textPartSchema>;

/** Zod schema for discriminated union of message content parts. */
export const messagePartSchema = z.discriminatedUnion("type", [textPartSchema]);

/** TypeScript type for message parts. */
export type MessagePart = z.infer<typeof messagePartSchema>;

/** Zod schema for file attachments in messages with metadata. */
export const attachmentSchema = ATTACHMENT_SCHEMA;

/** TypeScript type for attachments. */
export type Attachment = z.infer<typeof attachmentSchema>;

/**
 * Zod schema for chat messages with tool calls, attachments, and metadata.
 * Validates message structure, content requirements, and attachment constraints.
 * Used for both API communication and client-side state management.
 */
export const messageSchema = z.strictObject({
  attachments: z.array(attachmentSchema).optional(),
  content: z.string(),
  id: z.string(),
  isStreaming: z.boolean().optional(),
  role: messageRoleSchema,
  timestamp: z.iso.datetime(),
  toolCalls: z.array(toolCallSchema).optional(),
  toolResults: z.array(toolResultSchema).optional(),
});

/** TypeScript type for chat messages. */
export type Message = z.infer<typeof messageSchema>;

/**
 * Zod schema for chat session metadata and message history.
 * Manages conversation state, agent status, and temporal tracking.
 */
export const chatSessionSchema = z.strictObject({
  agentId: z.string(),
  agentStatus: AGENT_STATUS_BROADCAST_PAYLOAD_SCHEMA.optional(),
  createdAt: z.iso.datetime(),
  id: z.string(),
  lastMessageAt: z.iso.datetime().optional(),
  messages: z.array(messageSchema).default([]),
  title: z.string().optional(),
  updatedAt: z.iso.datetime(),
  userId: z.string().optional(),
});

/** TypeScript type for chat sessions. */
export type ChatSession = z.infer<typeof chatSessionSchema>;

/** Zod schema for chat store state management with loading states. */
export const chatStoreStateSchema = z.object({
  currentSessionId: z.string().nullable(),
  error: z.string().nullable(),
  sessions: z.array(chatSessionSchema),
  status: z.enum(["idle", "loading", "streaming", "error"]),
});

/** TypeScript type for chat store state. */
export type ChatStoreState = z.infer<typeof chatStoreStateSchema>;

/**
 * Zod schema for conversation messages with agent status and flexible content.
 * Supports both structured message parts and legacy content formats.
 */
export const conversationMessageSchema = z.object({
  agentStatus: AGENT_STATUS_BROADCAST_PAYLOAD_SCHEMA.optional(),
  attachments: z.array(attachmentSchema).optional(),
  content: z.string().optional(),
  createdAt: z.iso.datetime().or(z.date().transform((d) => d.toISOString())),
  id: z.string(),
  parts: z.array(messagePartSchema).optional(),
  role: messageRoleSchema,
  toolCalls: z.array(toolCallSchema).optional(),
  toolResults: z.array(toolResultSchema).optional(),
  updatedAt: z.iso
    .datetime()
    .or(z.date().transform((d) => d.toISOString()))
    .optional(),
});

/** TypeScript type for conversation messages. */
export type ConversationMessage = z.infer<typeof conversationMessageSchema>;

/** Zod schema for memory context responses with relevance scoring. */
export const memoryContextResponseSchema = z.object({
  context: z.string(),
  createdAt: primitiveSchemas.isoDateTime.optional(),
  id: primitiveSchemas.uuid.optional(),
  score: z.number().min(0).max(1),
  source: z.string().optional(),
});

/** TypeScript type for memory context responses. */
export type MemoryContextResponse = z.infer<typeof memoryContextResponseSchema>;

// ===== API SCHEMAS =====
// Request/response schemas for chat API endpoints

/** Zod schema for chat completion API requests with message arrays. */
export const chatCompletionRequestSchema = z.object({
  messages: z.array(messageSchema),
  model: z.string(),
  stream: z.boolean().optional(),
});

/** TypeScript type for chat completion requests. */
export type ChatCompletionRequest = z.infer<typeof chatCompletionRequestSchema>;

/** Zod schema for chat completion API responses with choice arrays. */
export const chatCompletionResponseSchema = z.object({
  choices: z.array(
    z.object({
      finish_reason: z.string().optional(),
      index: z.number(),
      message: messageSchema,
    })
  ),
  created: z.number(),
  id: z.string(),
  model: z.string(),
});

/** TypeScript type for chat completion responses. */
export type ChatCompletionResponse = z.infer<typeof chatCompletionResponseSchema>;

/** Zod schema for send message options with AI parameters and attachments. */
export const sendMessageOptionsSchema = z.object({
  attachments: z.array(z.instanceof(File)).optional(),
  systemPrompt: z.string().optional(),
  temperature: z.number().min(0).max(2).optional(),
  tools: z.array(z.record(z.string(), z.unknown())).optional(),
});

/** TypeScript type for send message options. */
export type SendMessageOptions = z.infer<typeof sendMessageOptionsSchema>;

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

/**
 * Form schema for sending messages with attachment validation.
 * Includes file type, size, and quantity constraints for user experience.
 */
export const sendMessageFormSchema = z.object({
  attachments: z
    .array(
      z.object({
        file: z.any(), // File object validated at runtime
        name: z.string().min(1),
        size: z
          .number()
          .positive()
          .max(50 * 1024 * 1024), // 50MB max
        type: z.enum(["image", "document", "audio", "video"]),
      })
    )
    .max(5, { error: "Too many attachments" })
    .optional(),
  conversationId: primitiveSchemas.uuid.optional(),
  message: z
    .string()
    .min(1, { error: "Message cannot be empty" })
    .max(10000, { error: "Message too long" }),
  metadata: z.record(z.string(), z.unknown()).optional(),
});

/** TypeScript type for send message form data. */
export type SendMessageFormData = z.infer<typeof sendMessageFormSchema>;

/**
 * Form schema for creating new chat conversations.
 * Validates conversation title, privacy settings, and participant constraints.
 */
export const createConversationFormSchema = z.object({
  initialMessage: z
    .string()
    .min(1, { error: "Initial message is required" })
    .max(10000, { error: "Message too long" }),
  isPrivate: z.boolean(),
  participants: z.array(primitiveSchemas.uuid).optional(),
  title: z
    .string()
    .min(1, { error: "Title is required" })
    .max(200, { error: "Title too long" }),
});

/** TypeScript type for conversation creation form data. */
export type CreateConversationFormData = z.infer<typeof createConversationFormSchema>;
