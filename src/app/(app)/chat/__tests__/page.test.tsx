/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ChatPage from "../../chat/page";

// Mock Streamdown-backed Response to avoid rehype/ESM issues in node test runner
vi.mock("@/components/ai-elements/response", () => ({
  Response: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="response">{children}</div>
  ),
}));

describe("ChatPage", () => {
  it("renders empty state and input controls", () => {
    render(<ChatPage />);
    expect(
      screen.getByText(/Start a conversation to see messages here/i)
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Chat prompt/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Submit/i })).toBeInTheDocument();
  });
});
