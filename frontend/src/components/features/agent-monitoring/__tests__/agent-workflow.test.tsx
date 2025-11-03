/**
 * @fileoverview Integration tests for agent monitoring: status dashboard,
 * collaboration hub, and connection status metrics/optimizations.
 */

import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test/test-utils";
import { ConnectionStatus } from "../../shared/connection-status";
import { AgentCollaborationHub } from "../communication/agent-collaboration-hub";
import { AgentStatusDashboard } from "../dashboard/agent-status-dashboard";

// Define test-specific types that match the expected component interfaces
interface AgentMetrics {
  id: string;
  name: string;
  status: "active" | "idle" | "error";
  healthScore: number;
  cpuUsage: number;
  memoryUsage: number;
  tokensProcessed: number;
  averageResponseTime: number;
  errorRate: number;
  uptime: number;
  tasksQueued: number;
  lastUpdate: Date;
}

interface CollaborationAgent {
  id: string;
  name: string;
  avatar?: string;
  status: "active" | "busy" | "idle" | "offline";
  specialization: string;
  currentTask?: string;
  performance: { accuracy: number; speed: number; efficiency: number };
  workload: number;
  lastActive: Date;
}

interface ConnectionAnalytics {
  connectionTime: number;
  reconnectCount: number;
  totalMessages: number;
  failedMessages: number;
  avgResponseTime: number;
  uptime: number;
}

interface NetworkMetrics {
  bandwidth: number;
  latency: number;
  packetLoss: number;
  jitter: number;
  quality: "excellent" | "good" | "fair" | "poor";
  signalStrength: number;
}

// Mock Recharts components to avoid canvas rendering issues in tests
vi.mock("recharts", () => ({
  Area: () => <div data-testid="area" />,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Line: () => <div data-testid="line" />,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Tooltip: () => <div data-testid="tooltip" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
}));

// Mock framer-motion to avoid animation issues in tests
vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: any) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}));

describe("Agent Workflow Integration Tests", () => {
  const mockAgentMetrics: AgentMetrics[] = [
    {
      averageResponseTime: 125,
      cpuUsage: 68,
      errorRate: 0.8,
      healthScore: 94,
      id: "agent-1",
      lastUpdate: new Date(),
      memoryUsage: 45,
      name: "Research Agent",
      status: "active",
      tasksQueued: 3,
      tokensProcessed: 15420,
      uptime: 98.5,
    },
    {
      averageResponseTime: 156,
      cpuUsage: 78,
      errorRate: 1.2,
      healthScore: 87,
      id: "agent-2",
      lastUpdate: new Date(),
      memoryUsage: 62,
      name: "Planning Agent",
      status: "active",
      tasksQueued: 5,
      tokensProcessed: 12890,
      uptime: 97.2,
    },
    {
      averageResponseTime: 98,
      cpuUsage: 25,
      errorRate: 0.5,
      healthScore: 92,
      id: "agent-3",
      lastUpdate: new Date(),
      memoryUsage: 38,
      name: "Booking Agent",
      status: "idle",
      tasksQueued: 1,
      tokensProcessed: 8750,
      uptime: 99.1,
    },
  ];

  const mockCollaborationAgents: CollaborationAgent[] = [
    {
      currentTask: "Processing request",
      id: "agent-1",
      lastActive: new Date(),
      name: "Research Agent",
      performance: { accuracy: 85, efficiency: 89, speed: 78 },
      specialization: "Data Analysis",
      status: "active",
      workload: 68,
    },
    {
      currentTask: "Processing request",
      id: "agent-2",
      lastActive: new Date(),
      name: "Planning Agent",
      performance: { accuracy: 78, efficiency: 83, speed: 74 },
      specialization: "Trip Planning",
      status: "active",
      workload: 78,
    },
  ];

  const mockHandoffs = [
    {
      confidence: 0.89,
      fromAgent: "agent-1",
      id: "handoff-1",
      reason: "Research completed, planning phase needed",
      status: "pending" as const,
      task: "Create itinerary from research data",
      timestamp: new Date(),
      toAgent: "agent-2",
    },
    {
      confidence: 0.92,
      fromAgent: "agent-2",
      id: "handoff-2",
      reason: "Quality assurance check",
      status: "completed" as const,
      task: "Review completed bookings",
      timestamp: new Date(Date.now() - 180000),
      toAgent: "agent-1",
    },
  ];

  const mockNetworkMetrics: NetworkMetrics = {
    bandwidth: 15600000,
    jitter: 5,
    latency: 87,
    packetLoss: 0.2,
    quality: "excellent",
    signalStrength: 92,
  };

  const mockConnectionAnalytics: ConnectionAnalytics = {
    avgResponseTime: 125,
    connectionTime: 45000,
    failedMessages: 3,
    reconnectCount: 0,
    totalMessages: 1247,
    uptime: 3600,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Agent Status Dashboard Workflow", () => {
    it("renders dashboard with agent metrics", () => {
      const onAgentSelect = vi.fn();

      renderWithProviders(
        <AgentStatusDashboard
          agents={mockAgentMetrics}
          onAgentSelect={onAgentSelect}
          refreshInterval={3000}
        />
      );

      // Check if all agents are displayed
      expect(screen.getAllByText("Research Agent")).toHaveLength(1);
      expect(screen.getAllByText("Planning Agent")).toHaveLength(1);
      expect(screen.getAllByText("Booking Agent")).toHaveLength(1);

      // Check status indicators
      expect(screen.getAllByText("active")).toHaveLength(2);
      expect(screen.getByText("idle")).toBeInTheDocument();

      // Check metrics are displayed
      expect(screen.getAllByText("94%")).toHaveLength(1); // Research Agent health
      expect(screen.getAllByText("87%")).toHaveLength(1); // Planning Agent health
      expect(screen.getAllByText("92%")).toHaveLength(2); // Booking Agent health + overall average
    });

    it("handles agent selection workflow", async () => {
      const user = userEvent.setup();
      const onAgentSelect = vi.fn();

      renderWithProviders(
        <AgentStatusDashboard
          agents={mockAgentMetrics}
          onAgentSelect={onAgentSelect}
          refreshInterval={3000}
        />
      );

      // Find and click on an agent card by looking for clickable elements
      const clickableElements = screen
        .getByText("Research Agent")
        .closest(".cursor-pointer");

      expect(clickableElements).toBeInTheDocument();

      if (clickableElements) {
        await user.click(clickableElements);
        expect(onAgentSelect).toHaveBeenCalledWith("agent-1");
      }
    });

    it("updates metrics with real-time data using useOptimistic pattern", async () => {
      const onAgentSelect = vi.fn();

      const { rerender } = renderWithProviders(
        <AgentStatusDashboard
          agents={mockAgentMetrics}
          onAgentSelect={onAgentSelect}
          refreshInterval={3000}
        />
      );

      // Initial state
      expect(screen.getAllByText("94%")).toHaveLength(1);

      // Simulate real-time update
      const updatedAgents = mockAgentMetrics.map((agent) =>
        agent.id === "agent-1" ? { ...agent, cpuUsage: 72, healthScore: 96 } : agent
      );

      rerender(
        <AgentStatusDashboard
          agents={updatedAgents}
          onAgentSelect={onAgentSelect}
          refreshInterval={3000}
        />
      );

      // Check updated metrics
      expect(screen.getAllByText("96%")).toHaveLength(1);
    });

    it("displays predictive analytics section", () => {
      const onAgentSelect = vi.fn();

      renderWithProviders(
        <AgentStatusDashboard
          agents={mockAgentMetrics}
          onAgentSelect={onAgentSelect}
          refreshInterval={3000}
        />
      );

      expect(
        screen.getByText("Predictive Analytics (72h Horizon)")
      ).toBeInTheDocument();
      expect(screen.getByText("Response Time Trends")).toBeInTheDocument();
      expect(screen.getByText("Token Processing Rate")).toBeInTheDocument();
    });
  });

  describe("Agent Collaboration Workflow", () => {
    it("renders collaboration hub with agents", () => {
      const onAgentSelect = vi.fn();

      renderWithProviders(
        <AgentCollaborationHub
          agents={mockCollaborationAgents}
          handoffs={mockHandoffs}
          onAgentSelect={onAgentSelect}
        />
      );

      expect(screen.getByText("Agent Collaboration Hub")).toBeInTheDocument();
      expect(screen.getAllByText("Research Agent").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Planning Agent").length).toBeGreaterThan(0);
      expect(screen.getByText("Data Analysis")).toBeInTheDocument();
      expect(screen.getByText("Trip Planning")).toBeInTheDocument();
    });

    it("displays collaboration metrics", () => {
      const onAgentSelect = vi.fn();

      renderWithProviders(
        <AgentCollaborationHub
          agents={mockCollaborationAgents}
          handoffs={mockHandoffs}
          onAgentSelect={onAgentSelect}
        />
      );

      // Check for collaboration metrics
      expect(screen.getByText("Handoff Success Rate")).toBeInTheDocument();
      expect(screen.getByText("Task Completion Time")).toBeInTheDocument();
      expect(screen.getByText("Agent Utilization")).toBeInTheDocument();
      expect(screen.getByText("Coordination Efficiency")).toBeInTheDocument();
    });

    it("shows agent handoffs section", () => {
      const onAgentSelect = vi.fn();

      renderWithProviders(
        <AgentCollaborationHub
          agents={mockCollaborationAgents}
          handoffs={mockHandoffs}
          onAgentSelect={onAgentSelect}
        />
      );

      expect(screen.getByText("Agent Handoffs")).toBeInTheDocument();
      expect(screen.getByText("pending")).toBeInTheDocument();
      expect(screen.getByText("completed")).toBeInTheDocument();
    });

    it("handles agent collaboration selection", async () => {
      const user = userEvent.setup();
      const onAgentSelect = vi.fn();

      renderWithProviders(
        <AgentCollaborationHub
          agents={mockCollaborationAgents}
          handoffs={mockHandoffs}
          onAgentSelect={onAgentSelect}
        />
      );

      // Find agent cards and simulate clicking - using different approach since collaboration hub has buttons
      const clickableElements = screen.getAllByText("Research Agent");
      const agentCard =
        clickableElements[0].closest("button") ||
        clickableElements[0].closest(".cursor-pointer");

      if (agentCard) {
        await user.click(agentCard);
        expect(onAgentSelect).toHaveBeenCalledWith("agent-1");
      }
    });
  });

  describe("Connection Status Workflow", () => {
    it("renders connection status with metrics", () => {
      const onReconnect = vi.fn();
      const onOptimize = vi.fn();

      renderWithProviders(
        <ConnectionStatus
          status="connected"
          metrics={mockNetworkMetrics}
          analytics={mockConnectionAnalytics}
          onReconnect={onReconnect}
          onOptimize={onOptimize}
          variant="detailed"
          showMetrics
          showOptimizations
        />
      );

      expect(screen.getByText("Connected")).toBeInTheDocument();
      expect(screen.getByText("87ms")).toBeInTheDocument(); // latency
      expect(screen.getByText("excellent")).toBeInTheDocument(); // quality
    });

    it("handles reconnection workflow", async () => {
      const user = userEvent.setup();
      const onReconnect = vi.fn();
      const onOptimize = vi.fn();

      renderWithProviders(
        <ConnectionStatus
          status="disconnected"
          metrics={mockNetworkMetrics}
          analytics={mockConnectionAnalytics}
          onReconnect={onReconnect}
          onOptimize={onOptimize}
          showMetrics
          showOptimizations
        />
      );

      const reconnectButton = screen.getByText("Reconnect");
      await user.click(reconnectButton);

      expect(onReconnect).toHaveBeenCalled();
    });

    it("handles connection optimization workflow", async () => {
      const user = userEvent.setup();
      const onReconnect = vi.fn();
      const onOptimize = vi.fn();

      // Use poor metrics to trigger optimization suggestions
      const poorMetrics: NetworkMetrics = {
        ...mockNetworkMetrics,
        latency: 250,
        packetLoss: 5.0,
        quality: "poor",
        signalStrength: 45,
      };

      renderWithProviders(
        <ConnectionStatus
          status="connected"
          metrics={poorMetrics}
          analytics={mockConnectionAnalytics}
          onReconnect={onReconnect}
          onOptimize={onOptimize}
          variant="detailed"
          showMetrics
          showOptimizations
        />
      );

      // Look for any optimization button (text depends on the specific suggestion)
      const optimizeButton = screen.getByText(/Optimize/);
      await user.click(optimizeButton);

      expect(onOptimize).toHaveBeenCalled();
    });

    it("displays network metrics when enabled", () => {
      const onReconnect = vi.fn();
      const onOptimize = vi.fn();

      renderWithProviders(
        <ConnectionStatus
          status="connected"
          metrics={mockNetworkMetrics}
          analytics={mockConnectionAnalytics}
          onReconnect={onReconnect}
          onOptimize={onOptimize}
          variant="detailed"
          showMetrics
        />
      );

      // Should show the connection status and latency at minimum
      expect(screen.getByText("Connected")).toBeInTheDocument();
      expect(screen.getByText("87ms")).toBeInTheDocument(); // latency
      expect(screen.getByText("excellent")).toBeInTheDocument(); // quality
    });

    it("shows optimization suggestions when connection quality is poor", () => {
      const onReconnect = vi.fn();
      const onOptimize = vi.fn();

      const poorMetrics: NetworkMetrics = {
        ...mockNetworkMetrics,
        latency: 250,
        packetLoss: 5.0,
        quality: "poor",
        signalStrength: 45,
      };

      renderWithProviders(
        <ConnectionStatus
          status="connected"
          metrics={poorMetrics}
          analytics={mockConnectionAnalytics}
          onReconnect={onReconnect}
          onOptimize={onOptimize}
          variant="detailed"
          showOptimizations
        />
      );

      // Should show the poor connection quality and high latency
      expect(screen.getByText("poor")).toBeInTheDocument();
      expect(screen.getByText("250ms")).toBeInTheDocument(); // high latency
    });
  });

  describe("Integrated Agent Monitoring Workflow", () => {
    it("coordinates between dashboard and collaboration views", async () => {
      const user = userEvent.setup();
      let selectedAgent: string | null = null;

      const handleAgentSelect = (agentId: string) => {
        selectedAgent = agentId;
      };

      const { rerender: _rerender } = renderWithProviders(
        <div>
          <AgentStatusDashboard
            agents={mockAgentMetrics}
            onAgentSelect={handleAgentSelect}
            refreshInterval={3000}
          />
          <AgentCollaborationHub
            agents={mockCollaborationAgents}
            handoffs={mockHandoffs}
            onAgentSelect={handleAgentSelect}
          />
        </div>
      );

      // Select agent from dashboard
      const clickableElements = screen.getAllByText("Research Agent");
      const agentCard =
        clickableElements[0].closest("button") ||
        clickableElements[0].closest(".cursor-pointer");
      if (agentCard) {
        await user.click(agentCard);
        expect(selectedAgent).toBe("agent-1");
      }
    });

    it("handles real-time updates across all components", async () => {
      const onAgentSelect = vi.fn();
      const onReconnect = vi.fn();
      const onOptimize = vi.fn();

      const { rerender } = renderWithProviders(
        <div>
          <AgentStatusDashboard
            agents={mockAgentMetrics}
            onAgentSelect={onAgentSelect}
            refreshInterval={3000}
          />
          <ConnectionStatus
            status="connected"
            metrics={mockNetworkMetrics}
            analytics={mockConnectionAnalytics}
            onReconnect={onReconnect}
            onOptimize={onOptimize}
            variant="detailed"
          />
        </div>
      );

      // Initial state should render
      expect(screen.getByText("Connected")).toBeInTheDocument();
      expect(screen.getAllByText("Research Agent").length).toBeGreaterThan(0);

      // Simulate real-time updates
      const updatedAgents = mockAgentMetrics.map((agent) => ({
        ...agent,
        healthScore: agent.healthScore + 1,
        lastUpdate: new Date(),
      }));

      const updatedMetrics: NetworkMetrics = {
        ...mockNetworkMetrics,
        latency: 92,
      };

      rerender(
        <div>
          <AgentStatusDashboard
            agents={updatedAgents}
            onAgentSelect={onAgentSelect}
            refreshInterval={3000}
          />
          <ConnectionStatus
            status="connected"
            metrics={updatedMetrics}
            analytics={mockConnectionAnalytics}
            onReconnect={onReconnect}
            onOptimize={onOptimize}
            variant="detailed"
          />
        </div>
      );

      // Verify updates are reflected - 95% health score should exist
      expect(screen.getByText("95%")).toBeInTheDocument(); // Updated health score from 94% to 95%
      // Connection should still be connected after the update
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });
  });
});
