/** @vitest-environment jsdom */

import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";
import { PreferencesSection } from "../preferences-section";

const { mockAuthState, mockCurrencyState } = vi.hoisted(() => ({
  mockAuthState: {
    setUser: vi.fn(),
    user: {
      createdAt: "2025-01-01T00:00:00.000Z",
      email: "test@example.com",
      id: "user-1",
      isEmailVerified: true,
      preferences: {
        analytics: true,
        autoSaveSearches: true,
        locationServices: false,
        smartSuggestions: true,
      },
      updatedAt: "2025-01-01T00:00:00.000Z",
    },
  },
  mockCurrencyState: {
    baseCurrency: "USD",
    setBaseCurrency: vi.fn(),
  },
}));

vi.mock("@/features/auth/store/auth/auth-core", () => ({
  useAuthCore: <T,>(selector?: (state: typeof mockAuthState) => T) =>
    selector ? selector(mockAuthState) : mockAuthState,
}));

vi.mock("@/features/shared/store/currency-store", () => ({
  useCurrencyStore: <T,>(selector?: (state: typeof mockCurrencyState) => T) =>
    selector ? selector(mockCurrencyState) : mockCurrencyState,
}));

describe("PreferencesSection", () => {
  it("renders additional setting switches with accessible descriptions", () => {
    render(<PreferencesSection />);

    expect(
      screen.getByRole("switch", { name: "Auto-save Searches" })
    ).toHaveAccessibleDescription(
      "Automatically save your search history for quick access."
    );
    expect(
      screen.getByRole("switch", { name: "Smart Suggestions" })
    ).toHaveAccessibleDescription(
      "Get AI-powered travel suggestions based on your preferences."
    );
    expect(
      screen.getByRole("switch", { name: "Location Services" })
    ).toHaveAccessibleDescription("Allow location access for nearby recommendations.");
    expect(
      screen.getByRole("switch", { name: "Analytics" })
    ).toHaveAccessibleDescription("Help us improve by sharing anonymous usage data.");
  });
});
