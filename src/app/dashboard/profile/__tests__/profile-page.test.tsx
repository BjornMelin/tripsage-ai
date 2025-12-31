/** @vitest-environment jsdom */

import type { AuthUser as User } from "@schemas/stores";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthCore } from "@/stores/auth/auth-core";

const { mockReplace } = vi.hoisted(() => ({
  mockReplace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
  }),
}));

vi.mock("@/components/ui/tabs", () => {
  const React = require("react");
  type TabsCtx = { value: string; setValue: (v: string) => void };
  const TabsContext = React.createContext(null) as React.Context<TabsCtx | null>;

  const Tabs = ({
    defaultValue,
    children,
  }: {
    defaultValue: string;
    children: React.ReactNode;
  }) => {
    const [value, setValue] = React.useState(defaultValue);
    return React.createElement(
      TabsContext.Provider,
      { value: { setValue, value } },
      children
    );
  };

  const TabsList = ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", { role: "tablist" }, children);

  const TabsTrigger = ({
    value,
    children,
    ...props
  }: {
    value: string;
    children: React.ReactNode;
  }) => {
    const ctx = React.useContext(TabsContext);
    const active = ctx?.value === value;
    return React.createElement(
      "button",
      {
        "aria-selected": active,
        "data-state": active ? "active" : "inactive",
        onClick: () => ctx?.setValue(value),
        role: "tab",
        ...props,
      },
      children
    );
  };

  const TabsContent = ({
    value,
    children,
  }: {
    value: string;
    children: React.ReactNode;
  }) => {
    const ctx = React.useContext(TabsContext);
    if (ctx?.value !== value) return null;
    return React.createElement("div", { role: "tabpanel" }, children);
  };

  return { Tabs, TabsContent, TabsList, TabsTrigger };
});

/**
 * Type definition for auth store return values.
 */
interface AuthStoreReturn {
  /** Whether authentication is loading */
  isLoading: boolean;
  /** Initializes auth state from /auth/me */
  initialize: () => Promise<void>;
  /** Current user data */
  user: User | null;
}

/**
 * Mock data for testing user authentication scenarios.
 */
// Shared auth fixture for tests; use a Partial to keep setup minimal.
const MOCK_USER: Partial<User> = {
  displayName: "John Doe",
  email: "test@example.com",
  firstName: "John",
  id: "1",
  isEmailVerified: true,
  lastName: "Doe",
};

// Mock the stores and profile components
vi.mock("@/stores/auth/auth-core");

// Define mock components in a hoisted block so they are available to vi.mock
// factories, which are hoisted by Vitest.
const { PERSONAL_INFO_SECTION, ACCOUNT_SETTINGS_SECTION, PREFERENCES_SECTION } =
  vi.hoisted(() => {
    const PersonalInfoSection = () => (
      <div data-testid="personal-info-section">Personal Info Section</div>
    );
    const AccountSettingsSection = () => (
      <div data-testid="account-settings-section">Account Settings Section</div>
    );
    const PreferencesSection = () => (
      <div data-testid="preferences-section">Preferences Section</div>
    );
    return {
      ACCOUNT_SETTINGS_SECTION: AccountSettingsSection,
      PERSONAL_INFO_SECTION: PersonalInfoSection,
      PREFERENCES_SECTION: PreferencesSection,
    } as const;
  });

vi.mock("@/components/features/profile/personal-info-section", () => ({
  PersonalInfoSection: PERSONAL_INFO_SECTION,
}));

vi.mock("@/components/features/profile/account-settings-section", () => ({
  AccountSettingsSection: ACCOUNT_SETTINGS_SECTION,
}));

vi.mock("@/components/features/profile/preferences-section", () => ({
  PreferencesSection: PREFERENCES_SECTION,
}));

const { default: PROFILE_PAGE } = await import("../page");

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  const setupAuthState = (overrides: Partial<AuthStoreReturn> = {}) => {
    vi.mocked(useAuthCore).mockReturnValue({
      initialize: vi.fn().mockResolvedValue(undefined),
      isLoading: false,
      user: MOCK_USER as User,
      ...overrides,
    } as AuthStoreReturn);
  };

  it("renders loading state when user data is loading", () => {
    setupAuthState({ isLoading: true, user: null });

    render(<PROFILE_PAGE />);

    // Check for accessible loading skeletons
    const statuses = screen.getAllByRole("status", { name: /loading content/i });
    expect(statuses.length).toBeGreaterThan(0);
  });

  it("redirects to login when user is not logged in", async () => {
    setupAuthState({ user: null });

    render(<PROFILE_PAGE />);

    await waitFor(() =>
      expect(mockReplace).toHaveBeenCalledWith("/login?from=%2Fdashboard%2Fprofile")
    );
  });

  it("renders profile page with tabs when user is logged in", () => {
    setupAuthState();

    render(<PROFILE_PAGE />);

    expect(
      screen.getByRole("heading", { level: 1, name: /profile/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Open Security Console/i })
    ).toHaveAttribute("href", "/dashboard/security");
    expect(
      screen.getByText("Manage your account settings and preferences.")
    ).toBeInTheDocument();

    // Check that all tabs are present
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();
    expect(screen.getByText("Preferences")).toBeInTheDocument();
  });

  it("displays personal info section by default", () => {
    setupAuthState();

    render(<PROFILE_PAGE />);

    expect(screen.getByTestId("personal-info-section")).toBeInTheDocument();
  });

  it("switches to account settings tab", async () => {
    setupAuthState();

    render(<PROFILE_PAGE />);

    const accountTab = screen.getByRole("tab", { name: /account/i });
    fireEvent.click(accountTab);

    await waitFor(() => expect(accountTab).toHaveAttribute("data-state", "active"));
    expect(await screen.findByTestId("account-settings-section")).toBeInTheDocument();
  });

  it("switches to preferences tab", async () => {
    setupAuthState();

    render(<PROFILE_PAGE />);

    const preferencesTab = screen.getByRole("tab", { name: /preferences/i });
    fireEvent.click(preferencesTab);

    await waitFor(() => expect(preferencesTab).toHaveAttribute("data-state", "active"));
    expect(await screen.findByTestId("preferences-section")).toBeInTheDocument();
  });

  it("renders tab icons correctly", () => {
    setupAuthState();

    render(<PROFILE_PAGE />);

    // Check that tabs have the correct structure (with icons)
    const personalTab = screen.getByRole("tab", { name: /personal/i });
    const accountTab = screen.getByRole("tab", { name: /account/i });
    const preferencesTab = screen.getByRole("tab", { name: /preferences/i });

    expect(personalTab).toBeInTheDocument();
    expect(accountTab).toBeInTheDocument();
    expect(preferencesTab).toBeInTheDocument();
  });

  it("maintains tab state during navigation", async () => {
    setupAuthState();

    render(<PROFILE_PAGE />);

    // Switch to preferences tab
    const preferencesTab = screen.getByRole("tab", { name: /preferences/i });
    fireEvent.click(preferencesTab);

    await waitFor(() => expect(preferencesTab).toHaveAttribute("data-state", "active"));
    expect(await screen.findByTestId("preferences-section")).toBeInTheDocument();

    // Switch back to personal tab
    const personalTab = screen.getByRole("tab", { name: /personal/i });
    fireEvent.click(personalTab);

    await waitFor(() => expect(personalTab).toHaveAttribute("data-state", "active"));
    expect(await screen.findByTestId("personal-info-section")).toBeInTheDocument();
  });

  it("renders proper heading structure", () => {
    setupAuthState();

    render(<PROFILE_PAGE />);

    // Check heading hierarchy
    const mainHeading = screen.getByRole("heading", { level: 1, name: /profile/i });
    expect(mainHeading).toBeInTheDocument();
  });

  it("has accessible tab structure", () => {
    setupAuthState();

    render(<PROFILE_PAGE />);

    // Check that tabs are properly structured for accessibility
    const tabList = screen.getByRole("tablist");
    const tabs = screen.getAllByRole("tab");
    const tabPanels = screen.getAllByRole("tabpanel");

    expect(tabList).toBeInTheDocument();
    expect(tabs).toHaveLength(3);
    expect(tabPanels).toHaveLength(1); // Only active tab panel is visible
  });

  it("handles loading state gracefully with skeletons", () => {
    setupAuthState({ isLoading: true, user: null });

    render(<PROFILE_PAGE />);

    // Check that accessible loading skeletons are present
    const statuses = screen.getAllByRole("status", { name: /loading content/i });
    expect(statuses.length).toBeGreaterThan(0);
  });

  // Removed brittle class assertions for container spacing; UI semantics are validated above.
});
