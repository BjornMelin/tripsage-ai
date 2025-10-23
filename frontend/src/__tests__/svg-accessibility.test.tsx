/**
 * SVG Accessibility Test Suite
 * Ensures all SVG elements have proper accessibility attributes
 */

import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LoginForm } from "@/components/auth/login-form";
import { ChatInterface } from "@/components/chat/chat-interface";
import { MessageList } from "@/components/chat/message-list";
import { ChatLayout } from "@/components/layouts/chat-layout";
import type { OptimisticChatMessage } from "@/hooks/use-optimistic-chat";
import { render } from "@/test/test-utils";

// Mock the auth context
const mockAuthContext = {
  signIn: vi.fn(),
  signInWithOAuth: vi.fn(),
  isLoading: false,
  error: null,
  isAuthenticated: false,
  clearError: vi.fn(),
};

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => mockAuthContext,
}));

// Mock other dependencies
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  usePathname: () => "/dashboard/chat",
}));

vi.mock("@/stores/chat-store", () => ({
  useChatStore: () => ({}),
}));

vi.mock("@/stores/agent-status-store", () => ({
  useAgentStatusStore: () => ({
    activeAgents: [],
    isMonitoring: false,
  }),
}));

// Mock DOM methods that aren't available in jsdom
Object.defineProperty(window.HTMLElement.prototype, "scrollIntoView", {
  value: vi.fn(),
  writable: true,
});

Object.defineProperty(window.HTMLElement.prototype, "scrollTo", {
  value: vi.fn(),
  writable: true,
});

describe("SVG Accessibility", () => {
  describe("LoginForm Component", () => {
    it("should have accessible Google OAuth button SVG", () => {
      render(<LoginForm />);

      const googleIcon = screen.getByRole("img", { name: "Google" });
      expect(googleIcon).toBeInTheDocument();
      expect(googleIcon.tagName.toLowerCase()).toBe("svg");
    });
  });

  describe("ChatInterface Component", () => {
    it("should have accessible send message button SVG", () => {
      render(<ChatInterface />);

      const sendIcon = screen.getByRole("img", { name: "Send message" });
      expect(sendIcon).toBeInTheDocument();
      expect(sendIcon.tagName.toLowerCase()).toBe("svg");
    });
  });

  describe("MessageList Component", () => {
    const mockMessages: OptimisticChatMessage[] = [];
    const currentUserId = "user-1";

    it("should have accessible empty state SVG when no messages", () => {
      render(<MessageList messages={mockMessages} currentUserId={currentUserId} />);

      const emptyStateIcon = screen.getByRole("img", { name: "No messages" });
      expect(emptyStateIcon).toBeInTheDocument();
      expect(emptyStateIcon.tagName.toLowerCase()).toBe("svg");
    });
  });

  describe("ChatLayout Component", () => {
    it("should have accessible new chat button SVG", () => {
      render(
        <ChatLayout>
          <div>Test content</div>
        </ChatLayout>
      );

      const newChatIcon = screen.getByRole("img", { name: "New chat" });
      expect(newChatIcon).toBeInTheDocument();
      expect(newChatIcon.tagName.toLowerCase()).toBe("svg");
    });

    it("should have accessible settings button SVG", () => {
      render(
        <ChatLayout>
          <div>Test content</div>
        </ChatLayout>
      );

      const settingsIcon = screen.getByRole("img", { name: "Settings" });
      expect(settingsIcon).toBeInTheDocument();
      expect(settingsIcon.tagName.toLowerCase()).toBe("svg");
    });

    it("should have accessible no active agents SVG", () => {
      render(
        <ChatLayout>
          <div>Test content</div>
        </ChatLayout>
      );

      const noAgentsIcon = screen.getByRole("img", { name: "No active agents" });
      expect(noAgentsIcon).toBeInTheDocument();
      expect(noAgentsIcon.tagName.toLowerCase()).toBe("svg");
    });
  });

  describe("SVG Accessibility Verification", () => {
    it("should verify that specific SVGs have proper accessibility attributes", () => {
      // Test that our specific fixes are working
      const { container } = render(<LoginForm />);

      // Check Google OAuth SVG specifically
      const googleSvg = container.querySelector('svg[aria-label="Google"]');
      expect(googleSvg).toBeInTheDocument();
      expect(googleSvg).toHaveAttribute("role", "img");
      expect(googleSvg).toHaveAttribute("aria-label", "Google");
    });
  });
});
