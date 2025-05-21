import { z } from 'zod';

// Message role schema
export const MessageRoleSchema = z.enum(['user', 'assistant', 'system']);
export type MessageRole = z.infer<typeof MessageRoleSchema>;

// Tool call state schema
export const ToolCallStateSchema = z.enum(['partial-call', 'call', 'result']);
export type ToolCallState = z.infer<typeof ToolCallStateSchema>;

// Tool invocation schema
export const ToolInvocationSchema = z.object({
  toolCallId: z.string(),
  toolName: z.string(),
  args: z.record(z.any()).optional(),
  state: ToolCallStateSchema,
  result: z.any().optional(),
});
export type ToolInvocation = z.infer<typeof ToolInvocationSchema>;

// Message part for text content
export const TextPartSchema = z.object({
  type: z.literal('text'),
  text: z.string(),
});
export type TextPart = z.infer<typeof TextPartSchema>;

// Message part for tool invocation
export const ToolInvocationPartSchema = z.object({
  type: z.literal('tool-invocation'),
  toolInvocation: ToolInvocationSchema,
});
export type ToolInvocationPart = z.infer<typeof ToolInvocationPartSchema>;

// Union of message part types
export const MessagePartSchema = z.discriminatedUnion('type', [
  TextPartSchema,
  ToolInvocationPartSchema,
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
  toolInvocations: z.array(ToolInvocationSchema).optional(),
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
  status: z.enum(['idle', 'loading', 'streaming', 'error']),
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
  usage: z.object({
    promptTokens: z.number(),
    completionTokens: z.number(),
    totalTokens: z.number(),
  }).optional(),
});
export type ChatCompletionResponse = z.infer<typeof ChatCompletionResponseSchema>;