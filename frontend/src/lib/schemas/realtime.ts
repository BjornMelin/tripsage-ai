/**
 * @fileoverview Zod v4 schemas for realtime connection and backoff configuration.
 */

import { z } from "zod";

/** Zod schema for exponential backoff configuration. */
export const backoffConfigSchema = z.object({
  /** Exponential factor (e.g., 2 for doubling, 1.5 for 50% increase). */
  factor: z.number().positive(),
  /** Initial delay in milliseconds before the first retry. */
  initialDelayMs: z.number().int().positive(),
  /** Maximum delay in milliseconds (caps exponential growth). */
  maxDelayMs: z.number().int().positive(),
});
/** TypeScript type for backoff configuration. */
export type BackoffConfig = z.infer<typeof backoffConfigSchema>;

/** Zod schema for connection status enumeration. */
export const CONNECTION_STATUS_SCHEMA = z.enum([
  "connecting",
  "connected",
  "disconnected",
  "reconnecting",
  "error",
]);
/** TypeScript type for connection status. */
export type ConnectionStatus = z.infer<typeof CONNECTION_STATUS_SCHEMA>;

/** Zod schema for chat message broadcast payload. */
export const CHAT_MESSAGE_BROADCAST_PAYLOAD_SCHEMA = z.object({
  content: z.string(),
  id: z.string().optional(),
  sender: z
    .object({
      avatar: z.string().optional(),
      id: z.string(),
      name: z.string(),
    })
    .optional(),
  timestamp: z.iso.datetime().optional(),
});
/** TypeScript type for chat message broadcast payload. */
export type ChatMessageBroadcastPayload = z.infer<
  typeof CHAT_MESSAGE_BROADCAST_PAYLOAD_SCHEMA
>;

/** Zod schema for chat typing broadcast payload. */
export const CHAT_TYPING_BROADCAST_PAYLOAD_SCHEMA = z.object({
  isTyping: z.boolean(),
  userId: z.string(),
});
/** TypeScript type for chat typing broadcast payload. */
export type ChatTypingBroadcastPayload = z.infer<
  typeof CHAT_TYPING_BROADCAST_PAYLOAD_SCHEMA
>;

/** Zod schema for agent status broadcast payload. */
export const AGENT_STATUS_BROADCAST_PAYLOAD_SCHEMA = z.object({
  currentTask: z.string().optional(),
  isActive: z.boolean(),
  progress: z.number().int().min(0).max(100),
  statusMessage: z.string().optional(),
});
/** TypeScript type for agent status broadcast payload. */
export type AgentStatusBroadcastPayload = z.infer<
  typeof AGENT_STATUS_BROADCAST_PAYLOAD_SCHEMA
>;
