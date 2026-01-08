/**
 * @fileoverview Shared test factories for Zustand store states.
 *
 * Provides reusable, typed helpers to construct partial store states for tests
 * with sensible defaults. Avoids duplication and hidden coupling across suites.
 */

import type { AgentStatusState } from "@/features/agent-monitoring/store/agent-status-store";

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
    removeStaleAgents: () => undefined,
    resetAgentStatusState: () => undefined,
    resourceUsage: [],
    setAgentStatusConnection: () => undefined,
    setMonitoring: () => undefined,
    unregisterAgent: () => undefined,
    updateAgentStatus: () => undefined,
    updateAgentTask: () => undefined,
  };

  return { ...base, ...overrides } as AgentStatusState;
}
