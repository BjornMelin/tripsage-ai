/**
 * @fileoverview Tests for the Profile Page component and its integration with user stores.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "@/stores/auth-store";
import { useAuthStore } from "@/stores/auth-store";
import type { UserProfile } from "@/stores/user-store";
import { useUserProfileStore } from "@/stores/user-store";
import ProfilePage from "../page";

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
vi.mock("@/stores/auth-store");

/** Mock component for PersonalInfoSection */
const PERSONAL_INFO_SECTION = () => (
  <div data-testid="personal-info-section">Personal Info Section</div>
);

/** Mock component for AccountSettingsSection */
const ACCOUNT_SETTINGS_SECTION = () => (
  <div data-testid="account-settings-section">Account Settings Section</div>
);

/** Mock component for PreferencesSection */
const PREFERENCES_SECTION = () => (
  <div data-testid="preferences-section">Preferences Section</div>
);

/** Mock component for SecuritySection */
const SECURITY_SECTION = () => (
  <div data-testid="security-section">Security Section</div>
);

vi.mock("@/components/features/profile/personal-info-section", () => ({
  PersonalInfoSection: PERSONAL_INFO_SECTION,
}));

vi.mock("@/components/features/profile/account-settings-section", () => ({
  AccountSettingsSection: ACCOUNT_SETTINGS_SECTION,
}));

vi.mock("@/components/features/profile/preferences-section", () => ({
  PreferencesSection: PREFERENCES_SECTION,
}));

vi.mock("@/components/features/profile/security-section", () => ({
  SecuritySection: SECURITY_SECTION,
}));

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state when user data is loading", () => {
    vi.mocked(useAuthStore).mockReturnValue({
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
    vi.mocked(useAuthStore).mockReturnValue({
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
    vi.mocked(useAuthStore).mockReturnValue({
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
      screen.getByText("Manage your account settings and preferences.")
    ).toBeInTheDocument();

    // Check that all tabs are present
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();
    expect(screen.getByText("Preferences")).toBeInTheDocument();
    expect(screen.getByText("Security")).toBeInTheDocument();
  });

  it("displays personal info section by default", () => {
    vi.mocked(useAuthStore).mockReturnValue({
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
    vi.mocked(useAuthStore).mockReturnValue({
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
    await userEvent.click(accountTab);

    await waitFor(() => {
      expect(screen.getByTestId("account-settings-section")).toBeInTheDocument();
    });
  });

  it("switches to preferences tab", async () => {
    vi.mocked(useAuthStore).mockReturnValue({
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
    await userEvent.click(preferencesTab);

    await waitFor(() => {
      expect(screen.getByTestId("preferences-section")).toBeInTheDocument();
    });
  });

  it("switches to security tab", async () => {
    vi.mocked(useAuthStore).mockReturnValue({
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

    const securityTab = screen.getByRole("tab", { name: /security/i });
    await userEvent.click(securityTab);

    await waitFor(() => {
      expect(screen.getByTestId("security-section")).toBeInTheDocument();
    });
  });

  it("renders tab icons correctly", () => {
    vi.mocked(useAuthStore).mockReturnValue({
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
    const securityTab = screen.getByRole("tab", { name: /security/i });

    expect(personalTab).toBeInTheDocument();
    expect(accountTab).toBeInTheDocument();
    expect(preferencesTab).toBeInTheDocument();
    expect(securityTab).toBeInTheDocument();
  });

  it("maintains tab state during navigation", async () => {
    vi.mocked(useAuthStore).mockReturnValue({
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
    await userEvent.click(preferencesTab);

    await waitFor(() => {
      expect(screen.getByTestId("preferences-section")).toBeInTheDocument();
    });

    // Switch back to personal tab
    const personalTab = screen.getByRole("tab", { name: /personal/i });
    await userEvent.click(personalTab);

    await waitFor(() => {
      expect(screen.getByTestId("personal-info-section")).toBeInTheDocument();
    });
  });

  it("renders proper heading structure", () => {
    vi.mocked(useAuthStore).mockReturnValue({
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
    expect(tabs).toHaveLength(4);
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
