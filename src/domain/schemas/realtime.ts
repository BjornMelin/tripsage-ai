/**
 * @fileoverview Realtime connection and backoff configuration schemas.
 * Includes connection status, backoff configuration, and broadcast payload schemas.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for realtime connections

/**
 * Zod schema for exponential backoff configuration.
 * Validates retry configuration including factor, initial delay, and maximum delay.
 */
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

/**
 * Zod schema for connection status enumeration.
 * Defines possible states for realtime connections.
 */
export const CONNECTION_STATUS_SCHEMA = z.enum([
  "connecting",
  "connected",
  "disconnected",
  "reconnecting",
  "error",
]);

/** TypeScript type for connection status. */
export type ConnectionStatus = z.infer<typeof CONNECTION_STATUS_SCHEMA>;

/**
 * Zod schema for chat message broadcast payload.
 * Validates chat message data for realtime broadcasting.
 */
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
  timestamp: primitiveSchemas.isoDateTime.optional(),
});

/** TypeScript type for chat message broadcast payload. */
export type ChatMessageBroadcastPayload = z.infer<
  typeof CHAT_MESSAGE_BROADCAST_PAYLOAD_SCHEMA
>;

/**
 * Zod schema for chat typing broadcast payload.
 * Validates typing indicator data for realtime broadcasting.
 */
export const CHAT_TYPING_BROADCAST_PAYLOAD_SCHEMA = z.object({
  isTyping: z.boolean(),
  userId: z.string(),
});

/** TypeScript type for chat typing broadcast payload. */
export type ChatTypingBroadcastPayload = z.infer<
  typeof CHAT_TYPING_BROADCAST_PAYLOAD_SCHEMA
>;

/**
 * Zod schema for agent status broadcast payload.
 * Validates agent status data for realtime broadcasting.
 */
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
