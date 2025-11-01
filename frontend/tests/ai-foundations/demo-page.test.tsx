/**
 * @fileoverview Smoke test for the AI SDK v6 demo page. Ensures the page renders
 * core controls from AI Elements without coupling to implementation details.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Page from "@/app/ai-demo/page";

describe("AI Demo Page", () => {
  it("renders prompt input", () => {
    render(<Page />);
    expect(screen.getByLabelText(/upload files/i)).toBeInTheDocument();
  });
});
