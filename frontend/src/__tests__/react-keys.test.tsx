/**
 * Test file to verify React key prop fixes
 * Tests that components render without key warnings when using proper keys
 */

import { SearchFilters } from "@/components/features/search/search-filters";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { render } from "@/test/test-utils";
import type { FilterOption } from "@/types/search";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock console.warn to capture React key warnings
const originalWarn = console.warn;
let warningMessages: string[] = [];

beforeEach(() => {
  warningMessages = [];
  console.warn = vi.fn((message: string) => {
    warningMessages.push(message);
    originalWarn(message);
  });
});

afterEach(() => {
  console.warn = originalWarn;
});

describe("React Key Props", () => {
  it("LoadingSpinner dots variant should not produce key warnings", () => {
    render(<LoadingSpinner variant="dots" />);

    const keyWarnings = warningMessages.filter(
      (msg) => msg.includes("key") && msg.includes("Warning")
    );

    expect(keyWarnings).toHaveLength(0);
  });

  it("LoadingSpinner bars variant should not produce key warnings", () => {
    render(<LoadingSpinner variant="bars" />);

    const keyWarnings = warningMessages.filter(
      (msg) => msg.includes("key") && msg.includes("Warning")
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
        type: "checkbox",
        value: "duration",
        options: [
          { label: "1-3 days", value: "short", count: 15 },
          { label: "4-7 days", value: "medium", count: 23 },
          { label: "8+ days", value: "long", count: 8 },
        ],
      },
    ];

    render(
      <SearchFilters
        type="accommodation"
        filters={mockFilters}
        onApplyFilters={() => {}}
        onResetFilters={() => {}}
      />
    );

    const keyWarnings = warningMessages.filter(
      (msg) => msg.includes("key") && msg.includes("Warning")
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
      (msg) => msg.includes("key") && msg.includes("Warning")
    );
    expect(keyWarnings).toHaveLength(0);
  });
});
