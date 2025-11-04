/**
 * @fileoverview Unit tests for ChatLayout components including ChatLayout,
 * ChatSidebar, and AgentStatusPanel, covering layout rendering, sidebar
 * collapse/expand functionality, agent status display, and chat navigation.
 */

import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AgentStatusState } from "@/stores/agent-status-store";
import { useAgentStatusStore } from "@/stores/agent-status-store";
import type { ChatState } from "@/stores/chat-store";
import { useChatStore } from "@/stores/chat-store";
import { render } from "@/test/test-utils";
import { AgentStatusPanel, ChatLayout, ChatSidebar } from "../chat-layout";

// Mock the stores
vi.mock("@/stores/chat-store", () => ({
  useChatStore: vi.fn(),
}));

vi.mock("@/stores/agent-status-store", () => ({
  useAgentStatusStore: vi.fn(),
}));

// Mock Next.js router
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/chat"),
}));

describe("ChatLayout", () => {
  beforeEach(() => {
    // Mock store implementations
    (useChatStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      addMessage: vi.fn(),
      addPendingMessage: vi.fn(),
      addToolResult: vi.fn(),
      addTypingUser: vi.fn(),
      autoSyncMemory: false,
      clearError: vi.fn(),
      clearMessages: vi.fn(),
      clearPendingMessages: vi.fn(),
      clearTypingUsers: vi.fn(),
      connectionStatus: "disconnected" as const,
      connectRealtime: vi.fn(),
      createSession: vi.fn(),
      currentSession: null,
      currentSessionId: null,
      deleteSession: vi.fn(),
      disconnectRealtime: vi.fn(),
      error: null,
      exportSessionData: vi.fn(),
      handleAgentStatusUpdate: vi.fn(),
      handleRealtimeMessage: vi.fn(),
      importSessionData: vi.fn(),
      isLoading: false,
      isRealtimeEnabled: false,
      isStreaming: false,
      memoryEnabled: false,
      pendingMessages: [],
      realtimeChannel: null,
      removePendingMessage: vi.fn(),
      removeTypingUser: vi.fn(),
      removeUserTyping: vi.fn(),
      renameSession: vi.fn(),
      sendMessage: vi.fn(),
      sessions: [],
      setAutoSyncMemory: vi.fn(),
      setCurrentSession: vi.fn(),
      setMemoryEnabled: vi.fn(),
      setRealtimeEnabled: vi.fn(),
      setUserTyping: vi.fn(),
      stopStreaming: vi.fn(),
      storeConversationMemory: vi.fn(),
      streamMessage: vi.fn(),
      syncMemoryToSession: vi.fn(),
      toggleAutoSyncMemory: vi.fn(),
      toggleMemory: vi.fn(),
      typingUsers: {},
      updateAgentStatus: vi.fn(),
      updateMessage: vi.fn(),
      updateSessionMemoryContext: vi.fn(),
      updateTypingUser: vi.fn(),
    } as ChatState);

    (useAgentStatusStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      activeAgents: [],
      addAgent: vi.fn(),
      addAgentActivity: vi.fn(),
      addAgentTask: vi.fn(),
      agents: [],
      completeAgentTask: vi.fn(),
      currentSession: null,
      currentSessionId: null,
      endSession: vi.fn(),
      error: null,
      getActiveAgents: vi.fn(),
      getCurrentSession: vi.fn(),
      isMonitoring: false,
      lastUpdated: null,
      resetAgentStatus: vi.fn(),
      sessions: [],
      setError: vi.fn(),
      startSession: vi.fn(),
      updateAgentProgress: vi.fn(),
      updateAgentStatus: vi.fn(),
      updateAgentTask: vi.fn(),
      updateResourceUsage: vi.fn(),
    } as AgentStatusState);
  });

  it("renders with children content", () => {
    render(
      <ChatLayout>
        <div data-testid="chat-content">Chat Content</div>
      </ChatLayout>
    );

    expect(screen.getByTestId("chat-content")).toBeInTheDocument();
  });

  it("renders sidebar by default", () => {
    render(
      <ChatLayout>
        <div>Content</div>
      </ChatLayout>
    );

    expect(screen.getByText("New Chat")).toBeInTheDocument();
    expect(screen.getByText("Recent Chats")).toBeInTheDocument();
  });

  it("hides sidebar when collapsed", () => {
    render(
      <ChatLayout sidebarCollapsed={true}>
        <div>Content</div>
      </ChatLayout>
    );

    // Sidebar should have width of 0 when collapsed
    const sidebar = screen.getByText("New Chat").closest('[class*="w-0"]');
    expect(sidebar).toBeInTheDocument();
  });

  it("shows agent panel by default", () => {
    render(
      <ChatLayout>
        <div>Content</div>
      </ChatLayout>
    );

    expect(screen.getByText("Agent Status")).toBeInTheDocument();
  });

  it("hides agent panel when showAgentPanel is false", () => {
    render(
      <ChatLayout showAgentPanel={false}>
        <div>Content</div>
      </ChatLayout>
    );

    expect(screen.queryByText("Agent Status")).not.toBeInTheDocument();
  });

  it("calls onNewChat when new chat button is clicked", () => {
    const onNewChat = vi.fn();

    render(
      <ChatLayout onNewChat={onNewChat}>
        <div>Content</div>
      </ChatLayout>
    );

    const newChatButton = screen.getByText("New Chat");
    newChatButton.click();

    expect(onNewChat).toHaveBeenCalled();
  });
});

describe("ChatSidebar", () => {
  it("renders recent chats section", () => {
    render(<ChatSidebar />);

    expect(screen.getByText("Recent Chats")).toBeInTheDocument();
  });

  it("renders new chat button", () => {
    render(<ChatSidebar />);

    expect(screen.getByText("New Chat")).toBeInTheDocument();
  });

  it("renders chat settings link", () => {
    render(<ChatSidebar />);

    expect(screen.getByText("Chat Settings")).toBeInTheDocument();
  });

  it("calls onNewChat when new chat button is clicked", () => {
    const onNewChat = vi.fn();

    render(<ChatSidebar onNewChat={onNewChat} />);

    const newChatButton = screen.getByText("New Chat");
    newChatButton.click();

    expect(onNewChat).toHaveBeenCalled();
  });
});

describe("AgentStatusPanel", () => {
  it("renders agent status header", () => {
    render(<AgentStatusPanel />);

    expect(screen.getByText("Agent Status")).toBeInTheDocument();
  });

  it("shows no active agents message when no agents are active", () => {
    (useAgentStatusStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      activeAgents: [],
      addAgent: vi.fn(),
      addAgentActivity: vi.fn(),
      addAgentTask: vi.fn(),
      agents: [],
      completeAgentTask: vi.fn(),
      currentSession: null,
      currentSessionId: null,
      endSession: vi.fn(),
      error: null,
      getActiveAgents: vi.fn(),
      getCurrentSession: vi.fn(),
      isMonitoring: false,
      lastUpdated: null,
      resetAgentStatus: vi.fn(),
      sessions: [],
      setError: vi.fn(),
      startSession: vi.fn(),
      updateAgentProgress: vi.fn(),
      updateAgentStatus: vi.fn(),
      updateAgentTask: vi.fn(),
      updateResourceUsage: vi.fn(),
    } as AgentStatusState);

    render(<AgentStatusPanel />);

    expect(screen.getByText("No active agents")).toBeInTheDocument();
  });

  it("shows active agents when available", () => {
    const mockAgent = {
      createdAt: new Date().toISOString(),
      currentTaskId: "t1",
      id: "1",
      name: "Flight Agent",
      progress: 75,
      status: "active" as const,
      tasks: [
        {
          completedAt: null,
          createdAt: new Date().toISOString(),
          description: "Searching for flights",
          id: "t1",
          progress: 75,
          status: "in_progress" as const,
          title: "Search Flights",
          updatedAt: new Date().toISOString(),
        },
      ],
      type: "flight-search",
      updatedAt: new Date().toISOString(),
    };

    (useAgentStatusStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      activeAgents: [mockAgent],
      addAgent: vi.fn(),
      addAgentActivity: vi.fn(),
      addAgentTask: vi.fn(),
      agents: [mockAgent],
      completeAgentTask: vi.fn(),
      currentSession: null,
      currentSessionId: null,
      endSession: vi.fn(),
      error: null,
      getActiveAgents: vi.fn(),
      getCurrentSession: vi.fn(),
      isMonitoring: false,
      lastUpdated: null,
      resetAgentStatus: vi.fn(),
      sessions: [],
      setError: vi.fn(),
      startSession: vi.fn(),
      updateAgentProgress: vi.fn(),
      updateAgentStatus: vi.fn(),
      updateAgentTask: vi.fn(),
      updateResourceUsage: vi.fn(),
    } as unknown as AgentStatusState);

    render(<AgentStatusPanel />);

    expect(screen.getByText("Flight Agent")).toBeInTheDocument();
    expect(screen.getByText("Searching for flights")).toBeInTheDocument();
    expect(screen.getByText("75% complete")).toBeInTheDocument();
  });

  it("shows recent activity section", () => {
    render(<AgentStatusPanel />);

    expect(screen.getByText("Recent Activity")).toBeInTheDocument();
  });

  it("displays loading state indicator", () => {
    (useAgentStatusStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      activeAgents: [],
      addAgent: vi.fn(),
      addAgentActivity: vi.fn(),
      addAgentTask: vi.fn(),
      agents: [],
      completeAgentTask: vi.fn(),
      currentSession: null,
      currentSessionId: null,
      endSession: vi.fn(),
      error: null,
      getActiveAgents: vi.fn(),
      getCurrentSession: vi.fn(),
      isMonitoring: true,
      lastUpdated: null,
      resetAgentStatus: vi.fn(),
      sessions: [],
      setError: vi.fn(),
      startSession: vi.fn(),
      updateAgentProgress: vi.fn(),
      updateAgentStatus: vi.fn(),
      updateAgentTask: vi.fn(),
      updateResourceUsage: vi.fn(),
    } as AgentStatusState);

    render(<AgentStatusPanel />);

    // The status indicator should be yellow when loading
    const statusIndicator = screen
      .getByText("Agent Status")
      .parentElement?.querySelector(".bg-yellow-500");
    expect(statusIndicator).toBeInTheDocument();
  });
});
