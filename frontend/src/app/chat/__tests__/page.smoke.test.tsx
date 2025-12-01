/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ChatPage from "../page";

// Mock Streamdown-backed Response to avoid rehype/ESM issues in node test runner
vi.mock("@/components/ai-elements/response", () => ({
  Response: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="response">{children}</div>
  ),
}));

// Mock the ChatClient component to avoid importing server-side dependencies
// and AI SDK components that are not needed for this smoke test.
// This allows us to test the page structure without full component initialization.
vi.mock("../chat-client", () => ({
  ChatClient: () => <div data-testid="chat-client">Chat Client</div>,
}));

describe("ChatPage UI smoke", () => {
  it("renders the chat client component", () => {
    render(<ChatPage />);
    expect(screen.getByTestId("chat-client")).toBeInTheDocument();
  });
});
