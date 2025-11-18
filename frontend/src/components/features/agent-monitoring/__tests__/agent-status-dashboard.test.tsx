/** @vitest-environment jsdom */

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AgentStatusState } from "@/stores/agent-status-store";
import {
  AgentStatusDashboard,
  type AgentStatusDashboardProps,
} from "../dashboard/agent-status-dashboard";

const MOCK_PAUSE = vi.fn();
const MOCK_RESUME = vi.fn();
const MOCK_RECONNECT = vi.fn();

const CREATE_STATE = (): AgentStatusState => ({
  activeAgents: [
    {
      createdAt: "2025-01-01T00:00:00.000Z",
      currentTaskId: "task-1",
      description: "",
      id: "agent-1",
      metadata: {},
      name: "Agent Alpha",
      progress: 65,
      status: "active",
      tasks: [
        {
          createdAt: "2025-01-01T00:00:00.000Z",
          description: "",
          id: "task-1",
          status: "in_progress",
          title: "Plan",
          updatedAt: "2025-01-01T00:00:00.000Z",
        },
      ],
      type: "planner",
      updatedAt: "2025-01-01T00:00:00.000Z",
    },
  ],
  activities: [
    {
      agentId: "agent-1",
      id: "activity-1",
      message: "Task started",
      timestamp: "2025-01-01T00:00:00.000Z",
      type: "info",
    },
  ],
  agentOrder: ["agent-1"],
  agents: [
    {
      createdAt: "2025-01-01T00:00:00.000Z",
      currentTaskId: "task-1",
      description: "",
      id: "agent-1",
      metadata: {},
      name: "Agent Alpha",
      progress: 65,
      status: "active",
      tasks: [
        {
          createdAt: "2025-01-01T00:00:00.000Z",
          description: "",
          id: "task-1",
          status: "in_progress",
          title: "Plan",
          updatedAt: "2025-01-01T00:00:00.000Z",
        },
      ],
      type: "planner",
      updatedAt: "2025-01-01T00:00:00.000Z",
    },
  ],
  agentsById: {},
  connection: {
    error: null,
    lastChangedAt: "2025-01-01T00:00:00.000Z",
    retryCount: 0,
    status: "subscribed",
    topic: "user:1",
  },
  isMonitoring: true,
  lastEventAt: "2025-01-01T00:00:00.000Z",
  recordActivity: vi.fn(),
  recordResourceUsage: vi.fn(),
  registerAgents: vi.fn(),
  resetAgentStatusState: vi.fn(),
  resourceUsage: [
    {
      activeAgents: 1,
      cpuUsage: 40,
      memoryUsage: 50,
      networkRequests: 10,
      timestamp: "2025-01-01T00:05:00.000Z",
    },
  ],
  setAgentStatusConnection: vi.fn(),
  setMonitoring: vi.fn(),
  updateAgentStatus: vi.fn(),
  updateAgentTask: vi.fn(),
});

let mockState: AgentStatusState;

vi.mock("@/stores/agent-status-store", () => ({
  useAgentStatusStore: (selector?: (state: AgentStatusState) => unknown) =>
    selector ? selector(mockState) : mockState,
}));

describe("AgentStatusDashboard", () => {
  let realtimeProps: AgentStatusDashboardProps;
  const renderDashboard = (override?: Partial<AgentStatusDashboardProps>) =>
    render(<AgentStatusDashboard {...realtimeProps} {...override} />);

  beforeEach(() => {
    MOCK_PAUSE.mockClear();
    MOCK_RESUME.mockClear();
    MOCK_RECONNECT.mockClear();
    mockState = CREATE_STATE();
    realtimeProps = {
      connectionError: null,
      connectionStatus: "subscribed",
      pause: MOCK_PAUSE,
      reconnect: MOCK_RECONNECT,
      resume: MOCK_RESUME,
      retryCount: 0,
    };
  });

  it("renders agent data from store", () => {
    renderDashboard();

    expect(screen.getByText("Agent Alpha")).toBeInTheDocument();
    expect(screen.getByText("Active Agents")).toBeInTheDocument();
    expect(screen.getByText(/Live Supabase updates/i)).toBeInTheDocument();
    expect(screen.getByText("Task started")).toBeInTheDocument();
  });

  it("invokes pause when monitoring is active", () => {
    renderDashboard();
    fireEvent.click(screen.getByRole("button", { name: /pause/i }));
    expect(MOCK_PAUSE).toHaveBeenCalled();
  });

  it("invokes resume when monitoring is paused", () => {
    mockState.isMonitoring = false;
    renderDashboard();
    fireEvent.click(screen.getByRole("button", { name: /resume/i }));
    expect(MOCK_RESUME).toHaveBeenCalled();
  });
});
