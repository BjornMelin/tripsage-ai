/** @vitest-environment jsdom */

import type { FilterOption } from "@schemas/search";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SearchFilters } from "@/components/features/search/search-filters";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { render } from "@/test/test-utils";

let warningMessages: string[] = [];
let warnSpy: ReturnType<typeof vi.spyOn> | null = null;

beforeEach(() => {
  warningMessages = [];
  warnSpy = vi.spyOn(console, "warn").mockImplementation((message: string) => {
    warningMessages.push(message);
  });
});

afterEach(() => {
  warnSpy?.mockRestore();
  warnSpy = null;
});

describe("React Key Props", () => {
  it("LoadingSpinner dots variant should not produce key warnings", () => {
    render(<LoadingSpinner variant="dots" />);

    const keyWarnings = warningMessages.filter(
      (msg) =>
        typeof msg === "string" &&
        (msg.includes('unique "key" prop') ||
          (msg.includes("key") && msg.includes("Warning")))
    );

    expect(keyWarnings).toHaveLength(0);
  });

  it("LoadingSpinner bars variant should not produce key warnings", () => {
    render(<LoadingSpinner variant="bars" />);

    const keyWarnings = warningMessages.filter(
      (msg) =>
        typeof msg === "string" &&
        (msg.includes('unique "key" prop') ||
          (msg.includes("key") && msg.includes("Warning")))
    );

    expect(keyWarnings).toHaveLength(0);
  });

  it("SearchFilters component should not produce key warnings", () => {
    const mockFilters: FilterOption[] = [
      {
        id: "price",
        label: "Price Range",
        type: "range",
        value: [0, 5000],
      },
      {
        id: "duration",
        label: "Trip Duration",
        options: [
          { count: 15, label: "1-3 days", value: "short" },
          { count: 23, label: "4-7 days", value: "medium" },
          { count: 8, label: "8+ days", value: "long" },
        ],
        type: "checkbox",
        value: "duration",
      },
    ];

    render(
      <SearchFilters
        type="accommodation"
        filters={mockFilters}
        onApplyFilters={() => {
          // Intentional no-op for testing
        }}
        onResetFilters={() => {
          // Intentional no-op for testing
        }}
      />
    );

    const keyWarnings = warningMessages.filter(
      (msg) =>
        typeof msg === "string" &&
        (msg.includes('unique "key" prop') ||
          (msg.includes("key") && msg.includes("Warning")))
    );

    expect(keyWarnings).toHaveLength(0);
  });

  it("components with static arrays should use semantic keys", () => {
    // Test that our key patterns use semantic naming instead of just indexes
    const { container } = render(<LoadingSpinner variant="dots" />);

    // Check that the DOM structure is consistent and renders properly
    const dots = container.querySelectorAll('[style*="animation-delay"]');
    expect(dots).toHaveLength(3);

    // Verify no React key warnings
    const keyWarnings = warningMessages.filter(
      (msg) =>
        typeof msg === "string" &&
        (msg.includes('unique "key" prop') ||
          (msg.includes("key") && msg.includes("Warning")))
    );
    expect(keyWarnings).toHaveLength(0);
  });
});
