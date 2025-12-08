/**
 * @fileoverview Shared test factories for Zustand store states.
 *
 * Provides reusable, typed helpers to construct partial store states for tests
 * with sensible defaults. Avoids duplication and hidden coupling across suites.
 */

import type { AgentStatusState } from "@/stores/agent-status-store";
import type { ChatMessagesState } from "@/stores/chat/chat-messages";
import type { ChatRealtimeState } from "@/stores/chat/chat-realtime";

/**
 * Create a mock ChatMessagesState with minimal defaults and optional overrides.
 *
 * @param overrides Optional partial state overrides.
 * @returns A ChatMessagesState-like object for mocking `useChatMessages`.
 */
export function createMockChatMessagesState(
  overrides: Partial<ChatMessagesState> = {}
): ChatMessagesState {
  return {
    addMessage: () => "message-1",
    addToolResult: () => undefined,
    clearError: () => undefined,
    clearMessages: () => undefined,
    createSession: () => "session-1",
    get currentSession() {
      return null;
    },
    currentSessionId: null,
    deleteSession: () => undefined,
    error: null,
    exportSessionData: () => "{}",
    importSessionData: () => "session-1",
    isLoading: false,
    isStreaming: false,
    renameSession: () => undefined,
    sendMessage: async () => undefined,
    sessions: [],
    setCurrentSession: () => undefined,
    stopStreaming: () => undefined,
    streamMessage: async () => undefined,
    updateMessage: () => undefined,
    ...overrides,
  } as ChatMessagesState;
}

/**
 * Create a mock ChatRealtimeState with minimal defaults and optional overrides.
 *
 * @param overrides Optional partial state overrides.
 * @returns A ChatRealtimeState-like object for mocking `useChatRealtime`.
 */
export function createMockChatRealtimeState(
  overrides: Partial<ChatRealtimeState> = {}
): ChatRealtimeState {
  return {
    addPendingMessage: () => undefined,
    agentStatuses: {},
    clearTypingUsers: () => undefined,
    connectionStatus: "disconnected",
    handleAgentStatusUpdate: () => undefined,
    handleRealtimeMessage: () => undefined,
    handleTypingUpdate: () => undefined,
    isRealtimeEnabled: false,
    pendingMessages: [],
    removePendingMessage: () => undefined,
    removeUserTyping: () => undefined,
    resetRealtimeState: () => undefined,
    setChatConnectionStatus: () => undefined,
    setRealtimeEnabled: () => undefined,
    setUserTyping: () => undefined,
    typingUsers: {},
    updateAgentStatus: () => undefined,
    ...overrides,
  } as ChatRealtimeState;
}

/**
 * Create a mock AgentStatusState with minimal defaults and optional overrides.
 *
 * Arrays default to empty to ensure deterministic tests. Timestamps are left to
 * the test to control via vi.setSystemTime/Date stubs when needed.
 *
 * @param overrides Optional partial state overrides.
 * @returns An AgentStatusState-like object for mocking `useAgentStatusStore`.
 */
export function createMockAgentStatusState(
  overrides: Partial<AgentStatusState> = {}
): AgentStatusState {
  const base: AgentStatusState = {
    activeAgents: [],
    activities: [],
    agentOrder: [],
    agents: [],
    agentsById: {},
    connection: {
      error: null,
      lastChangedAt: null,
      retryCount: 0,
      status: "idle",
      topic: null,
    },
    isMonitoring: false,
    lastEventAt: null,
    recordActivity: () => undefined,
    recordResourceUsage: () => undefined,
    registerAgents: () => undefined,
    resetAgentStatusState: () => undefined,
    resourceUsage: [],
    setAgentStatusConnection: () => undefined,
    setMonitoring: () => undefined,
    updateAgentStatus: () => undefined,
    updateAgentTask: () => undefined,
  };

  return { ...base, ...overrides } as AgentStatusState;
}
