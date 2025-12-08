/**
 * @fileoverview Factory for creating ChatSession and Message test data.
 */

import type { ChatSession, Message } from "@schemas/chat";

/**
 * Create mock chat session.
 *
 * @param overrides - Partial session to override defaults
 * @returns A complete chat session
 */
export function createMockSession(overrides: Partial<ChatSession> = {}): ChatSession {
  return {
    agentId: "agent-1",
    createdAt: "2025-01-01T00:00:00Z",
    id: "session-1",
    messages: [],
    title: "Test Conversation",
    updatedAt: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

/**
 * Create mock message.
 *
 * @param overrides - Partial message to override defaults
 * @returns A complete message
 */
export function createMockMessage(overrides: Partial<Message> = {}): Message {
  return {
    content: "Test message",
    id: "msg-1",
    role: "user",
    timestamp: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}
