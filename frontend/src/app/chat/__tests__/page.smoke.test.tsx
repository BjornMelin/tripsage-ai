/**
 * @fileoverview Smoke tests for ChatPage component, verifying basic rendering
 * and presence of essential UI controls for chat functionality without full
 * interaction testing.
 */

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ChatPage from "../page";

describe("ChatPage UI smoke", () => {
  it("renders Stop and Retry controls", () => {
    render(<ChatPage />);
    expect(
      screen.getByRole("button", { name: /Stop streaming/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Retry last request/i })
    ).toBeInTheDocument();
  });
});
