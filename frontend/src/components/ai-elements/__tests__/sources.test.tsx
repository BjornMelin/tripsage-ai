import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";

/**
 * Test suite for Sources components.
 * Tests popover interaction and source link rendering functionality.
 */
describe("ai-elements/sources", () => {
  /**
   * Verifies Sources popover opens and displays source links when trigger is clicked.
   * Tests the complete interaction flow from trigger click to content display.
   */
  it("opens popover and shows sources", async () => {
    const user = userEvent.setup();
    render(
      <Sources>
        <SourcesTrigger count={2} />
        <SourcesContent>
          <Source href="https://example.com/a">A</Source>
          <Source href="https://example.com/b">B</Source>
        </SourcesContent>
      </Sources>
    );

    await user.click(screen.getByRole("button", { name: /sources/i }));

    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
  });
});
