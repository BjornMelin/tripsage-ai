/**
 * @fileoverview Unit tests for ChatLayout components including ChatLayout,
 * ChatSidebar, and AgentStatusPanel, covering layout rendering, sidebar
 * collapse/expand functionality, agent status display, and chat navigation.
 */

import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAgentStatusStore } from "@/stores/agent-status-store";
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
    (useChatStore as any).mockReturnValue({
      createSession: vi.fn(),
      currentSessionId: null,
      sessions: [],
    });

    (useAgentStatusStore as any).mockReturnValue({
      activeAgents: [],
      isMonitoring: false,
    });
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
    (useAgentStatusStore as any).mockReturnValue({
      activeAgents: [],
      isMonitoring: false,
    });

    render(<AgentStatusPanel />);

    expect(screen.getByText("No active agents")).toBeInTheDocument();
  });

  it("shows active agents when available", () => {
    (useAgentStatusStore as any).mockReturnValue({
      activeAgents: [
        {
          currentTaskId: "t1",
          id: "1",
          name: "Flight Agent",
          progress: 75,
          status: "active",
          tasks: [{ description: "Searching for flights", id: "t1" }],
        },
      ],
      isMonitoring: false,
    });

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
    (useAgentStatusStore as any).mockReturnValue({
      activeAgents: [],
      isMonitoring: true,
    });

    render(<AgentStatusPanel />);

    // The status indicator should be yellow when loading
    const statusIndicator = screen
      .getByText("Agent Status")
      .parentElement?.querySelector(".bg-yellow-500");
    expect(statusIndicator).toBeInTheDocument();
  });
});
