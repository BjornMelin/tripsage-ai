/**
 * @fileoverview Zod v4 schemas for chat messaging and tool calling.
 */

import { z } from "zod";

/** Zod schema for message role types in chat conversations. */
export const MESSAGE_ROLE_SCHEMA = z.enum(["user", "assistant", "system"]);
/** TypeScript type for message roles. */
export type MessageRole = z.infer<typeof MESSAGE_ROLE_SCHEMA>;

/** Zod schema for tool call state types. */
export const TOOL_CALL_STATE_SCHEMA = z.enum(["partial-call", "call", "result"]);
/** TypeScript type for tool call states. */
export type ToolCallState = z.infer<typeof TOOL_CALL_STATE_SCHEMA>;

/** Zod schema for tool call status types. */
export const TOOL_CALL_STATUS_SCHEMA = z.enum([
  "pending",
  "executing",
  "completed",
  "error",
  "cancelled",
]);
/** TypeScript type for tool call status. */
export type ToolCallStatus = z.infer<typeof TOOL_CALL_STATUS_SCHEMA>;

/** Zod schema for tool call metadata and execution tracking. */
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
/** TypeScript type for tool calls. */
export type ToolCall = z.infer<typeof TOOL_CALL_SCHEMA>;

/** Zod schema for tool execution results. */
export const TOOL_RESULT_SCHEMA = z.object({
  callId: z.string(),
  errorMessage: z.string().optional(),
  executionTime: z.number().optional(),
  result: z.unknown(),
  status: z.enum(["success", "error"]),
});
/** TypeScript type for tool results. */
export type ToolResult = z.infer<typeof TOOL_RESULT_SCHEMA>;

/** Zod schema for text message parts. */
export const TEXT_PART_SCHEMA = z.object({
  text: z.string(),
  type: z.literal("text"),
});
/** TypeScript type for text parts. */
export type TextPart = z.infer<typeof TEXT_PART_SCHEMA>;

/** Zod schema for discriminated union of message parts. */
export const MESSAGE_PART_SCHEMA = z.discriminatedUnion("type", [TEXT_PART_SCHEMA]);
/** TypeScript type for message parts. */
export type MessagePart = z.infer<typeof MESSAGE_PART_SCHEMA>;

/** Zod schema for message attachments. */
export const ATTACHMENT_SCHEMA = z.object({
  contentType: z.string().optional(),
  id: z.string(),
  name: z.string().optional(),
  size: z.number().optional(),
  url: z.string(),
});
/** TypeScript type for attachments. */
export type Attachment = z.infer<typeof ATTACHMENT_SCHEMA>;

/**
 * Zod schema for chat messages with tool calls, attachments, and metadata.
 */
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
  routedTo: z.string().optional(),
  routingConfidence: z.number().optional(),
  toolCalls: z.array(TOOL_CALL_SCHEMA).optional(),
  toolResults: z.array(TOOL_RESULT_SCHEMA).optional(),
  updatedAt: z.date().or(z.string().datetime()).optional(),
});
/** TypeScript type for chat messages. */
export type Message = z.infer<typeof MESSAGE_SCHEMA>;

/** Zod schema for chat session metadata and message history. */
export const CHAT_SESSION_SCHEMA = z.object({
  createdAt: z.date().or(z.string().datetime()),
  id: z.string(),
  messages: z.array(MESSAGE_SCHEMA).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  title: z.string(),
  updatedAt: z.date().or(z.string().datetime()),
});
/** TypeScript type for chat sessions. */
export type ChatSession = z.infer<typeof CHAT_SESSION_SCHEMA>;

/** Zod schema for chat store state management. */
export const CHAT_STORE_STATE_SCHEMA = z.object({
  currentSessionId: z.string().nullable(),
  error: z.string().nullable(),
  sessions: z.array(CHAT_SESSION_SCHEMA),
  status: z.enum(["idle", "loading", "streaming", "error"]),
});
/** TypeScript type for chat store state. */
export type ChatStoreState = z.infer<typeof CHAT_STORE_STATE_SCHEMA>;

/** Zod schema for agent status information. */
export const AGENT_STATUS_SCHEMA = z.object({
  active: z.boolean(),
  lastUpdated: z.string().datetime().optional(),
  message: z.string().optional(),
});
/** TypeScript type for agent status. */
export type AgentStatus = z.infer<typeof AGENT_STATUS_SCHEMA>;

/** Zod schema for conversation messages with agent status. */
export const CONVERSATION_MESSAGE_SCHEMA = z.object({
  agentStatus: AGENT_STATUS_SCHEMA.optional(),
  attachments: z.array(ATTACHMENT_SCHEMA).optional(),
  content: z.string().optional(),
  createdAt: z.date().or(z.string().datetime()),
  id: z.string(),
  parts: z.array(MESSAGE_PART_SCHEMA).optional(),
  role: MESSAGE_ROLE_SCHEMA,
  toolCalls: z.array(TOOL_CALL_SCHEMA).optional(),
  toolResults: z.array(TOOL_RESULT_SCHEMA).optional(),
  updatedAt: z.date().or(z.string().datetime()).optional(),
});
/** TypeScript type for conversation messages. */
export type ConversationMessage = z.infer<typeof CONVERSATION_MESSAGE_SCHEMA>;

/** Zod schema for memory context responses. */
export const MEMORY_CONTEXT_RESPONSE_SCHEMA = z.object({
  context: z.string(),
  score: z.number().min(0).max(1),
  source: z.string().optional(),
});
/** TypeScript type for memory context responses. */
export type MemoryContextResponse = z.infer<typeof MEMORY_CONTEXT_RESPONSE_SCHEMA>;

/** Zod schema for chat completion API requests. */
export const CHAT_COMPLETION_REQUEST_SCHEMA = z.object({
  messages: z.array(MESSAGE_SCHEMA),
  model: z.string(),
  stream: z.boolean().optional(),
});
/** TypeScript type for chat completion requests. */
export type ChatCompletionRequest = z.infer<typeof CHAT_COMPLETION_REQUEST_SCHEMA>;

/** Zod schema for chat completion API responses. */
export const CHAT_COMPLETION_RESPONSE_SCHEMA = z.object({
  choices: z.array(
    z.object({
      finish_reason: z.string().optional(),
      index: z.number(),
      message: MESSAGE_SCHEMA,
    })
  ),
  created: z.number(),
  id: z.string(),
  model: z.string(),
});
/** TypeScript type for chat completion responses. */
export type ChatCompletionResponse = z.infer<typeof CHAT_COMPLETION_RESPONSE_SCHEMA>;

/** Zod schema for send message options. */
export const SEND_MESSAGE_OPTIONS_SCHEMA = z.object({
  /** Optional file attachments to include with the message */
  attachments: z.array(z.instanceof(File)).optional(),
  /** Custom system prompt to override defaults */
  systemPrompt: z.string().optional(),
  /** AI temperature parameter for response creativity */
  temperature: z.number().min(0).max(2).optional(),
  /** Available tools/functions for the AI to use */
  tools: z.array(z.record(z.string(), z.unknown())).optional(),
});
/** TypeScript type for send message options. */
export type SendMessageOptions = z.infer<typeof SEND_MESSAGE_OPTIONS_SCHEMA>;
