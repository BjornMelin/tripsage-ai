/** @vitest-environment jsdom */

import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ProfilePage from "@/app/(app)/dashboard/profile/page";
import { render } from "@/test/test-utils";
import { AccountSettingsSection } from "../account-settings-section";
import { PersonalInfoSection } from "../personal-info-section";
import { PreferencesSection } from "../preferences-section";

const { mockAuthState, mockCurrencyState, mockRouter } = vi.hoisted(() => {
  const user = {
    createdAt: "2025-01-01T00:00:00.000Z",
    displayName: "John Doe",
    email: "test@example.com",
    firstName: "John",
    id: "user-1",
    isEmailVerified: true,
    lastName: "Doe",
    preferences: {
      notifications: {
        email: true,
        marketing: false,
        priceAlerts: false,
        tripReminders: true,
      },
    },
    updatedAt: "2025-01-01T00:00:00.000Z",
  };

  return {
    mockAuthState: {
      hasInitialized: true,
      initialize: vi.fn().mockResolvedValue(undefined),
      isLoading: false,
      logout: vi.fn(),
      setUser: vi.fn(),
      user,
    },
    mockCurrencyState: {
      baseCurrency: "USD",
      setBaseCurrency: vi.fn(),
    },
    mockRouter: {
      replace: vi.fn(),
    },
  };
});

vi.mock("@/features/auth/store/auth/auth-core", () => ({
  useAuthCore: <T,>(selector?: (state: typeof mockAuthState) => T) =>
    selector ? selector(mockAuthState) : mockAuthState,
}));

vi.mock("@/features/shared/store/currency-store", () => ({
  useCurrencyStore: <T,>(selector?: (state: typeof mockCurrencyState) => T) =>
    selector ? selector(mockCurrencyState) : mockCurrencyState,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

const RENDER_PHASE_UPDATE_WARNING = "Cannot update a component";
type ConsoleErrorSpy = {
  mock: {
    calls: unknown[][];
  };
  mockRestore: () => void;
};

let consoleErrorSpy: ConsoleErrorSpy;

const ExpectNoRenderPhaseUpdateWarning = () => {
  expect(
    consoleErrorSpy.mock.calls.some((call) => {
      const message: unknown = call[0];
      return String(message).includes(RENDER_PHASE_UPDATE_WARNING);
    })
  ).toBe(false);
};

beforeEach(() => {
  consoleErrorSpy = vi.spyOn(console, "error");
});

afterEach(() => {
  ExpectNoRenderPhaseUpdateWarning();
  consoleErrorSpy.mockRestore();
});

describe("Profile Components Smoke Tests", () => {
  it("renders PersonalInfoSection without crashing", () => {
    render(<PersonalInfoSection />);
    expect(screen.getByText("Personal Information")).toBeInTheDocument();
  });

  it("renders AccountSettingsSection without crashing", () => {
    render(<AccountSettingsSection />);
    expect(screen.getByText("Email Settings")).toBeInTheDocument();
  });

  it("renders PreferencesSection without crashing", () => {
    render(<PreferencesSection />);
    expect(screen.getByText("Regional & Language")).toBeInTheDocument();
  });

  it("displays user information in PersonalInfoSection", () => {
    render(<PersonalInfoSection />);
    expect(screen.getByText("Profile Picture")).toBeInTheDocument();
    expect(screen.getByText("Personal Information")).toBeInTheDocument();
  });

  it("displays email settings in AccountSettingsSection", () => {
    render(<AccountSettingsSection />);
    expect(screen.getByText("Email Settings")).toBeInTheDocument();
    expect(screen.getByText("Notification Preferences")).toBeInTheDocument();
    expect(screen.getByText("Danger Zone")).toBeInTheDocument();
  });

  it("displays preferences in PreferencesSection", () => {
    render(<PreferencesSection />);
    expect(screen.getByText("Regional & Language")).toBeInTheDocument();
    expect(screen.getByText("Additional Settings")).toBeInTheDocument();
  });
});

describe("Profile Page Integration", () => {
  it("renders profile page with all section tabs and shared auth context", () => {
    render(<ProfilePage />);

    // Page header with shared auth context
    expect(screen.getByRole("heading", { name: "Profile" })).toBeInTheDocument();
    expect(
      screen.getByText("Manage your account settings and preferences.")
    ).toBeInTheDocument();

    // All three section tabs are present (Personal is default active)
    expect(screen.getByRole("tab", { name: /Personal/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Account/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Preferences/i })).toBeInTheDocument();

    // Default tab (Personal) content is visible
    expect(screen.getByText("Personal Information")).toBeInTheDocument();

    // Security card is present
    expect(screen.getByText("Security & MFA")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Open Security Console/i })
    ).toBeInTheDocument();
  });
});
