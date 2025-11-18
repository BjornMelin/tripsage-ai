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

describe("ChatPage UI smoke", () => {
  it("renders Stop and Retry controls", () => {
    render(<ChatPage />);
    expect(screen.getByRole("button", { name: /Stop streaming/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Retry last request/i })
    ).toBeInTheDocument();
  });
});
