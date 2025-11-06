import { cleanup, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AgentStatusState } from "@/stores/agent-status-store";
import { useAgentStatusStore } from "@/stores/agent-status-store";
import type { ChatState } from "@/stores/chat-store";
import { ConnectionStatus, useChatStore } from "@/stores/chat-store";
import { render } from "@/test/test-utils.test";
import { AgentStatusPanel, ChatLayout, ChatSidebar } from "../chat-layout";

// Store mocks
vi.mock("@/stores/chat-store", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/stores/chat-store")>();
  return {
    ...actual,
    useChatStore: vi.fn(),
  };
});

vi.mock("@/stores/agent-status-store", () => ({
  useAgentStatusStore: vi.fn(),
}));

// Next.js router mock
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/chat"),
}));

const MOCK_USE_CHAT_STORE = vi.mocked(useChatStore);
const MOCK_USE_AGENT_STATUS_STORE = vi.mocked(useAgentStatusStore);

function CreateMockChatState(): ChatState {
  return {
    addMessage: vi.fn(),
    addPendingMessage: vi.fn(),
    addToolResult: vi.fn(),
    autoSyncMemory: false,
    clearError: vi.fn(),
    clearMessages: vi.fn(),
    clearTypingUsers: vi.fn(),
    connectionStatus: ConnectionStatus.Disconnected,
    connectRealtime: vi.fn(),
    createSession: vi.fn(() => "session-1"),
    currentSession: null,
    currentSessionId: null,
    deleteSession: vi.fn(),
    disconnectRealtime: vi.fn(),
    error: null,
    exportSessionData: vi.fn(() => "{}"),
    handleAgentStatusUpdate: vi.fn(),
    handleRealtimeMessage: vi.fn(),
    importSessionData: vi.fn(() => "session-1"),
    isLoading: false,
    isRealtimeEnabled: false,
    isStreaming: false,
    memoryEnabled: false,
    pendingMessages: [],
    realtimeChannel: null,
    removePendingMessage: vi.fn(),
    removeUserTyping: vi.fn(),
    renameSession: vi.fn(),
    sendMessage: vi.fn(() => Promise.resolve()),
    sessions: [],
    setAutoSyncMemory: vi.fn(),
    setCurrentSession: vi.fn(),
    setMemoryEnabled: vi.fn(),
    setRealtimeEnabled: vi.fn(),
    setUserTyping: vi.fn(),
    stopStreaming: vi.fn(),
    storeConversationMemory: vi.fn(() => Promise.resolve()),
    streamMessage: vi.fn(() => Promise.resolve()),
    syncMemoryToSession: vi.fn(() => Promise.resolve()),
    typingUsers: {},
    updateAgentStatus: vi.fn(),
    updateMessage: vi.fn(),
    updateSessionMemoryContext: vi.fn(),
  } satisfies ChatState;
}

function CreateMockAgentStatusState(
  overrides: Partial<AgentStatusState> = {}
): AgentStatusState {
  const activeAgents = overrides.activeAgents ?? [];
  const sessions = overrides.sessions ?? [];
  return {
    activeAgents,
    addAgent: vi.fn(),
    addAgentActivity: vi.fn(),
    addAgentTask: vi.fn(),
    agents: overrides.agents ?? activeAgents,
    completeAgentTask: vi.fn(),
    currentSession: overrides.currentSession ?? null,
    currentSessionId: overrides.currentSessionId ?? null,
    endSession: vi.fn(),
    error: overrides.error ?? null,
    getActiveAgents: vi.fn(() => activeAgents),
    getCurrentSession: vi.fn(() => overrides.currentSession ?? null),
    isMonitoring: overrides.isMonitoring ?? false,
    lastUpdated: overrides.lastUpdated ?? null,
    resetAgentStatus: vi.fn(),
    sessions,
    setError: vi.fn(),
    startSession: vi.fn(),
    updateAgentProgress: vi.fn(),
    updateAgentStatus: vi.fn(),
    updateAgentTask: vi.fn(),
    updateResourceUsage: vi.fn(),
  };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ChatLayout", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MOCK_USE_CHAT_STORE.mockReturnValue(CreateMockChatState());
    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(CreateMockAgentStatusState());
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
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
      <ChatLayout sidebarCollapsed>
        <div>Content</div>
      </ChatLayout>
    );

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

    screen.getByText("New Chat").click();
    expect(onNewChat).toHaveBeenCalled();
  });
});

describe("ChatSidebar", () => {
  beforeEach(() => {
    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(CreateMockAgentStatusState());
  });

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

    screen.getByText("New Chat").click();
    expect(onNewChat).toHaveBeenCalled();
  });
});

describe("AgentStatusPanel", () => {
  beforeEach(() => {
    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(CreateMockAgentStatusState());
  });

  it("renders agent status header", () => {
    render(<AgentStatusPanel />);

    expect(screen.getByText("Agent Status")).toBeInTheDocument();
  });

  it("shows no active agents message when no agents are active", () => {
    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(
      CreateMockAgentStatusState({
        activeAgents: [],
        agents: [],
      })
    );

    render(<AgentStatusPanel />);

    expect(screen.getByText("No active agents")).toBeInTheDocument();
  });

  it("shows active agents when available", () => {
    const mockAgent = {
      createdAt: new Date().toISOString(),
      currentTaskId: "00000000-0000-0000-0000-000000000012",
      id: "00000000-0000-0000-0000-000000000011",
      name: "Flight Agent",
      progress: 75,
      status: "active" as const,
      tasks: [
        {
          createdAt: new Date().toISOString(),
          description: "Searching for flights",
          id: "00000000-0000-0000-0000-000000000012",
          progress: 75,
          status: "in_progress" as const,
          title: "Search Flights",
          updatedAt: new Date().toISOString(),
        },
      ],
      type: "flight-search",
      updatedAt: new Date().toISOString(),
    } satisfies AgentStatusState["agents"][number];

    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(
      CreateMockAgentStatusState({
        activeAgents: [mockAgent],
        agents: [mockAgent],
      })
    );

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
    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(
      CreateMockAgentStatusState({
        isMonitoring: true,
      })
    );

    render(<AgentStatusPanel />);

    const statusIndicator = screen
      .getByText("Agent Status")
      .parentElement?.querySelector(".bg-yellow-500");
    expect(statusIndicator).toBeInTheDocument();
  });
});
