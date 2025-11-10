/**
 * @fileoverview Shared test factories for Zustand store states.
 *
 * Provides reusable, typed helpers to construct partial store states for tests
 * with sensible defaults. Avoids duplication and hidden coupling across suites.
 */

import type { AgentStatusState } from "@/stores/agent-status-store";
import type { ChatState } from "@/stores/chat-store";

/**
 * Create a mock ChatState with minimal defaults and optional overrides.
 *
 * Collections default to empty to avoid hidden coupling between tests.
 * Only the fields that tests commonly touch are populated; actions default to
 * jest/vitest fns in the consuming test via `vi.fn()` if needed.
 *
 * @param overrides Optional partial state overrides.
 * @returns A ChatState-like object for mocking `useChatStore`.
 */
export function createMockChatState(overrides: Partial<ChatState> = {}): ChatState {
  return {
    // Actions (no-ops by default; tests can override)
    addMessage: () => "message-1",
    addPendingMessage: () => undefined,
    addToolResult: () => undefined,
    autoSyncMemory: false,
    clearError: () => undefined,
    clearMessages: () => undefined,
    clearTypingUsers: () => undefined,

    // Realtime
    connectionStatus: 2 as unknown as ChatState["connectionStatus"],
    connectRealtime: () => undefined,
    createSession: () => "session-1",

    // Computed
    get currentSession() {
      return null;
    },
    currentSessionId: null,
    deleteSession: () => undefined,
    disconnectRealtime: () => undefined,
    error: null,
    exportSessionData: () => "{}",
    handleAgentStatusUpdate: () => undefined,
    handleRealtimeMessage: () => undefined,
    importSessionData: () => "session-1",
    isLoading: false,
    isRealtimeEnabled: false,
    isStreaming: false,

    // Memory
    memoryEnabled: false,
    pendingMessages: [],
    realtimeChannel: null,
    removePendingMessage: () => undefined,
    removeUserTyping: () => undefined,
    renameSession: () => undefined,
    sendMessage: async () => undefined,
    // Core state
    sessions: [],
    setAutoSyncMemory: () => undefined,
    setCurrentSession: () => undefined,
    setMemoryEnabled: () => undefined,
    setRealtimeEnabled: () => undefined,
    setUserTyping: () => undefined,
    stopStreaming: () => undefined,
    storeConversationMemory: async () => undefined,
    streamMessage: async () => undefined,
    syncMemoryToSession: async () => undefined,
    typingUsers: {},
    updateAgentStatus: () => undefined,
    updateMessage: () => undefined,
    updateSessionMemoryContext: () => undefined,

    ...overrides,
  } as ChatState;
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
    get activeAgents() {
      return this.agents.filter(
        (a) => a.status !== "idle" && a.status !== "completed" && a.status !== "error"
      );
    },

    // Actions (no-ops by default; tests can override)
    addAgent: () => undefined,
    addAgentActivity: () => undefined,
    addAgentTask: () => undefined,
    agents: [],
    completeAgentTask: () => undefined,

    // Computed
    get currentSession() {
      return this.sessions.find((s) => s.id === this.currentSessionId) ?? null;
    },
    currentSessionId: null,
    endSession: () => undefined,
    error: null,

    // Computed helpers
    getActiveAgents() {
      return this.activeAgents;
    },
    getCurrentSession() {
      return this.currentSession;
    },
    isMonitoring: false,
    lastUpdated: null,
    resetAgentStatus: () => undefined,
    sessions: [],
    setError: () => undefined,
    startSession: () => undefined,
    updateAgentProgress: () => undefined,
    updateAgentStatus: () => undefined,
    updateAgentTask: () => undefined,
    updateResourceUsage: () => undefined,
  };

  return { ...base, ...overrides } as AgentStatusState;
}
