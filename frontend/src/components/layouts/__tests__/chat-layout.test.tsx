import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AgentStatusState } from "@/stores/agent-status-store";
import { useAgentStatusStore } from "@/stores/agent-status-store";
import { useChatMemory } from "@/stores/chat/chat-memory";
import { useChatMessages, useSessions } from "@/stores/chat/chat-messages";
import { useChatRealtime } from "@/stores/chat/chat-realtime";
import {
  createMockAgentStatusState,
  createMockChatMemoryState,
  createMockChatMessagesState,
  createMockChatRealtimeState,
} from "@/test/factories/stores";
import { render } from "@/test/test-utils";
import { AgentStatusPanel, ChatLayout, ChatSidebar } from "../chat-layout";

// Store mocks (partial to preserve non-mocked exports)
vi.mock("@/stores/chat/chat-messages", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/stores/chat/chat-messages")>();
  return {
    ...actual,
    useChatMessages: vi.fn(),
    useSessions: vi.fn(),
  };
});
vi.mock("@/stores/chat/chat-realtime", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/stores/chat/chat-realtime")>();
  return {
    ...actual,
    useChatRealtime: vi.fn(),
  };
});
vi.mock("@/stores/chat/chat-memory", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/stores/chat/chat-memory")>();
  return {
    ...actual,
    useChatMemory: vi.fn(),
  };
});
vi.mock("@/stores/agent-status-store", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/stores/agent-status-store")>();
  return {
    ...actual,
    useAgentStatusStore: vi.fn(),
  };
});

// Next.js router mock
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/chat"),
}));

const MOCK_USE_CHAT_MESSAGES = vi.mocked(useChatMessages);
const MOCK_USE_SESSIONS = vi.mocked(useSessions);
const MOCK_USE_CHAT_REALTIME = vi.mocked(useChatRealtime);
const MOCK_USE_CHAT_MEMORY = vi.mocked(useChatMemory);
const MOCK_USE_AGENT_STATUS_STORE = vi.mocked(useAgentStatusStore);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ChatLayout", () => {
  beforeEach(() => {
    MOCK_USE_CHAT_MESSAGES.mockReturnValue(createMockChatMessagesState());
    MOCK_USE_SESSIONS.mockReturnValue([]);
    MOCK_USE_CHAT_REALTIME.mockReturnValue(createMockChatRealtimeState());
    MOCK_USE_CHAT_MEMORY.mockReturnValue(createMockChatMemoryState());
    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(createMockAgentStatusState());
  });

  afterEach(() => {
    // No fake timers required for these tests
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

    const sidebar = screen.getByTestId("chat-sidebar");
    expect(sidebar).toBeInTheDocument();
    expect(sidebar.getAttribute("data-collapsed")).toBe("true");
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

    const button = screen.getByRole("button", { name: /new chat/i });
    fireEvent.click(button);
    expect(onNewChat).toHaveBeenCalledTimes(1);
  });
});

describe("ChatSidebar", () => {
  beforeEach(() => {
    MOCK_USE_CHAT_MESSAGES.mockReturnValue(
      createMockChatMessagesState({
        createSession: vi.fn(() => "new-session-id"),
        setCurrentSession: vi.fn(),
      })
    );
    MOCK_USE_SESSIONS.mockReturnValue([]);
    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(createMockAgentStatusState());
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

    const button = screen.getByRole("button", { name: /new chat/i });
    fireEvent.click(button);
    expect(onNewChat).toHaveBeenCalledTimes(1);
  });
});

describe("AgentStatusPanel", () => {
  beforeEach(() => {
    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(createMockAgentStatusState());
  });

  it("renders agent status header", () => {
    render(<AgentStatusPanel />);

    expect(screen.getByText("Agent Status")).toBeInTheDocument();
  });

  it("shows no active agents message when no agents are active", () => {
    MOCK_USE_AGENT_STATUS_STORE.mockReturnValue(
      createMockAgentStatusState({
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
      createMockAgentStatusState({
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
      createMockAgentStatusState({
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
