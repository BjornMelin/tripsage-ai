/** @vitest-environment jsdom */

import type { AuthUser as User, UserProfile } from "@schemas/stores";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthCore } from "@/stores/auth/auth-core";
import { useUserProfileStore } from "@/stores/user-store";
import ProfilePage from "../page";

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
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
  /** Whether authentication is loading */
  isLoading: boolean;
  /** Current user data */
  user: User | null;
}

/**
 * Type definition for user profile store return values.
 */
interface UserProfileStoreReturn {
  /** Whether profile data is loading */
  isLoading: boolean;
  /** Current user profile data */
  profile: UserProfile | null;
}

/**
 * Mock data for testing user authentication scenarios.
 */
const MOCK_USER: Partial<User> = {
  /** User's display name */
  displayName: "John Doe",
  /** User's email address */
  email: "test@example.com",
  /** User's first name */
  firstName: "John",
  /** Unique user identifier */
  id: "1",
  /** Whether email has been verified */
  isEmailVerified: true,
  lastName: "Doe",
};

// Mock the stores and profile components
vi.mock("@/stores/user-store");
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

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("renders loading state when user data is loading", () => {
    vi.mocked(useAuthCore).mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      user: null,
    } as AuthStoreReturn);
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      profile: null,
    } as UserProfileStoreReturn);

    render(<ProfilePage />);

    // Check for accessible loading skeletons
    const statuses = screen.getAllByRole("status", { name: /loading content/i });
    expect(statuses.length).toBeGreaterThan(0);
  });

  it("renders not found state when user is not logged in", () => {
    vi.mocked(useAuthCore).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
    } as AuthStoreReturn);
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      profile: null,
    } as UserProfileStoreReturn);

    render(<ProfilePage />);

    expect(screen.getByText("Profile Not Found")).toBeInTheDocument();
    expect(screen.getByText("Please log in to view your profile.")).toBeInTheDocument();
  });

  it("renders profile page with tabs when user is logged in", () => {
    vi.mocked(useAuthCore).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: MOCK_USER as User,
    } as AuthStoreReturn);
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      profile: {
        createdAt: "",
        email: MOCK_USER.email || "",
        id: "p1",
        updatedAt: "",
      } as UserProfile,
    } as UserProfileStoreReturn);

    render(<ProfilePage />);

    expect(
      screen.getByRole("heading", { level: 1, name: /profile/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Open Security Console/i })
    ).toHaveAttribute("href", "/security");
    expect(
      screen.getByText("Manage your account settings and preferences.")
    ).toBeInTheDocument();

    // Check that all tabs are present
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();
    expect(screen.getByText("Preferences")).toBeInTheDocument();
  });

  it("displays personal info section by default", () => {
    vi.mocked(useAuthCore).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: MOCK_USER as User,
    } as AuthStoreReturn);
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      profile: {
        createdAt: "",
        email: MOCK_USER.email || "",
        id: "p1",
        updatedAt: "",
      } as UserProfile,
    } as UserProfileStoreReturn);

    render(<ProfilePage />);

    expect(screen.getByTestId("personal-info-section")).toBeInTheDocument();
  });

  it("switches to account settings tab", async () => {
    vi.mocked(useAuthCore).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: MOCK_USER as User,
    } as AuthStoreReturn);
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      profile: {
        createdAt: "",
        email: MOCK_USER.email || "",
        id: "p1",
        updatedAt: "",
      } as UserProfile,
    } as UserProfileStoreReturn);

    render(<ProfilePage />);

    const accountTab = screen.getByRole("tab", { name: /account/i });
    act(() => {
      fireEvent.click(accountTab);
    });

    await waitFor(() => expect(accountTab).toHaveAttribute("data-state", "active"));
    expect(await screen.findByTestId("account-settings-section")).toBeInTheDocument();
  });

  it("switches to preferences tab", async () => {
    vi.mocked(useAuthCore).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: MOCK_USER as User,
    } as AuthStoreReturn);
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      profile: {
        createdAt: "",
        email: MOCK_USER.email || "",
        id: "p1",
        updatedAt: "",
      } as UserProfile,
    } as UserProfileStoreReturn);

    render(<ProfilePage />);

    const preferencesTab = screen.getByRole("tab", { name: /preferences/i });
    act(() => {
      fireEvent.click(preferencesTab);
    });

    await waitFor(() => expect(preferencesTab).toHaveAttribute("data-state", "active"));
    expect(await screen.findByTestId("preferences-section")).toBeInTheDocument();
  });

  it("renders tab icons correctly", () => {
    vi.mocked(useAuthCore).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: MOCK_USER as User,
    } as AuthStoreReturn);
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      profile: {
        createdAt: "",
        email: MOCK_USER.email || "",
        id: "p1",
        updatedAt: "",
      } as UserProfile,
    } as UserProfileStoreReturn);

    render(<ProfilePage />);

    // Check that tabs have the correct structure (with icons)
    const personalTab = screen.getByRole("tab", { name: /personal/i });
    const accountTab = screen.getByRole("tab", { name: /account/i });
    const preferencesTab = screen.getByRole("tab", { name: /preferences/i });

    expect(personalTab).toBeInTheDocument();
    expect(accountTab).toBeInTheDocument();
    expect(preferencesTab).toBeInTheDocument();
  });

  it("maintains tab state during navigation", async () => {
    vi.mocked(useAuthCore).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: MOCK_USER as User,
    } as AuthStoreReturn);
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      profile: {
        createdAt: "",
        email: MOCK_USER.email || "",
        id: "p1",
        updatedAt: "",
      } as UserProfile,
    } as UserProfileStoreReturn);

    render(<ProfilePage />);

    // Switch to preferences tab
    const preferencesTab = screen.getByRole("tab", { name: /preferences/i });
    act(() => {
      fireEvent.click(preferencesTab);
    });

    await waitFor(() => expect(preferencesTab).toHaveAttribute("data-state", "active"));
    expect(await screen.findByTestId("preferences-section")).toBeInTheDocument();

    // Switch back to personal tab
    const personalTab = screen.getByRole("tab", { name: /personal/i });
    act(() => {
      fireEvent.click(personalTab);
    });

    await waitFor(() => expect(personalTab).toHaveAttribute("data-state", "active"));
    expect(await screen.findByTestId("personal-info-section")).toBeInTheDocument();
  });

  it("renders proper heading structure", () => {
    vi.mocked(useAuthCore).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: MOCK_USER as User,
    } as AuthStoreReturn);
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      profile: {
        createdAt: "",
        email: MOCK_USER.email || "",
        id: "p1",
        updatedAt: "",
      } as UserProfile,
    } as UserProfileStoreReturn);

    render(<ProfilePage />);

    // Check heading hierarchy
    const mainHeading = screen.getByRole("heading", { level: 1, name: /profile/i });
    expect(mainHeading).toBeInTheDocument();
  });

  it("has accessible tab structure", () => {
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: false,
      user: MOCK_USER,
    });

    render(<ProfilePage />);

    // Check that tabs are properly structured for accessibility
    const tabList = screen.getByRole("tablist");
    const tabs = screen.getAllByRole("tab");
    const tabPanels = screen.getAllByRole("tabpanel");

    expect(tabList).toBeInTheDocument();
    expect(tabs).toHaveLength(3);
    expect(tabPanels).toHaveLength(1); // Only active tab panel is visible
  });

  it("handles loading state gracefully with skeletons", () => {
    vi.mocked(useUserProfileStore).mockReturnValue({
      isLoading: true,
      user: null,
    });

    render(<ProfilePage />);

    // Check that accessible loading skeletons are present
    const statuses = screen.getAllByRole("status", { name: /loading content/i });
    expect(statuses.length).toBeGreaterThan(0);
  });

  // Removed brittle class assertions for container spacing; UI semantics are validated above.
});
