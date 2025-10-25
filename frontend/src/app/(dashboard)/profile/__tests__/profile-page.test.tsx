import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/stores/auth-store";
import { useUserProfileStore } from "@/stores/user-store";
import ProfilePage from "../page";

// Mock the stores and profile components
vi.mock("@/stores/user-store");
vi.mock("@/stores/auth-store");
vi.mock("@/components/features/profile/personal-info-section", () => ({
  PersonalInfoSection: () => (
    <div data-testid="personal-info-section">Personal Info Section</div>
  ),
}));
vi.mock("@/components/features/profile/account-settings-section", () => ({
  AccountSettingsSection: () => (
    <div data-testid="account-settings-section">Account Settings Section</div>
  ),
}));
vi.mock("@/components/features/profile/preferences-section", () => ({
  PreferencesSection: () => (
    <div data-testid="preferences-section">Preferences Section</div>
  ),
}));
vi.mock("@/components/features/profile/security-section", () => ({
  SecuritySection: () => <div data-testid="security-section">Security Section</div>,
}));

const mockUser = {
  id: "1",
  email: "test@example.com",
  firstName: "John",
  lastName: "Doe",
  displayName: "John Doe",
  isEmailVerified: true,
};

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state when user data is loading", () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: true,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: null,
      isLoading: false,
    } as any);

    render(<ProfilePage />);

    // Check for accessible loading skeletons
    const statuses = screen.getAllByRole("status", { name: /loading content/i });
    expect(statuses.length).toBeGreaterThan(0);
  });

  it("renders not found state when user is not logged in", () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: null,
      isLoading: false,
    } as any);

    render(<ProfilePage />);

    expect(screen.getByText("Profile Not Found")).toBeInTheDocument();
    expect(screen.getByText("Please log in to view your profile.")).toBeInTheDocument();
  });

  it("renders profile page with tabs when user is logged in", () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: mockUser as any,
      isAuthenticated: true,
      isLoading: false,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: { id: "p1", email: mockUser.email, createdAt: "", updatedAt: "" } as any,
      isLoading: false,
    } as any);

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
      user: mockUser as any,
      isAuthenticated: true,
      isLoading: false,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: { id: "p1", email: mockUser.email, createdAt: "", updatedAt: "" } as any,
      isLoading: false,
    } as any);

    render(<ProfilePage />);

    expect(screen.getByTestId("personal-info-section")).toBeInTheDocument();
  });

  it("switches to account settings tab", async () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: mockUser as any,
      isAuthenticated: true,
      isLoading: false,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: { id: "p1", email: mockUser.email, createdAt: "", updatedAt: "" } as any,
      isLoading: false,
    } as any);

    render(<ProfilePage />);

    const accountTab = screen.getByRole("tab", { name: /account/i });
    await userEvent.click(accountTab);

    await waitFor(() => {
      expect(screen.getByTestId("account-settings-section")).toBeInTheDocument();
    });
  });

  it("switches to preferences tab", async () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: mockUser as any,
      isAuthenticated: true,
      isLoading: false,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: { id: "p1", email: mockUser.email, createdAt: "", updatedAt: "" } as any,
      isLoading: false,
    } as any);

    render(<ProfilePage />);

    const preferencesTab = screen.getByRole("tab", { name: /preferences/i });
    await userEvent.click(preferencesTab);

    await waitFor(() => {
      expect(screen.getByTestId("preferences-section")).toBeInTheDocument();
    });
  });

  it("switches to security tab", async () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: mockUser as any,
      isAuthenticated: true,
      isLoading: false,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: { id: "p1", email: mockUser.email, createdAt: "", updatedAt: "" } as any,
      isLoading: false,
    } as any);

    render(<ProfilePage />);

    const securityTab = screen.getByRole("tab", { name: /security/i });
    await userEvent.click(securityTab);

    await waitFor(() => {
      expect(screen.getByTestId("security-section")).toBeInTheDocument();
    });
  });

  it("renders tab icons correctly", () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: mockUser as any,
      isAuthenticated: true,
      isLoading: false,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: { id: "p1", email: mockUser.email, createdAt: "", updatedAt: "" } as any,
      isLoading: false,
    } as any);

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
      user: mockUser as any,
      isAuthenticated: true,
      isLoading: false,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: { id: "p1", email: mockUser.email, createdAt: "", updatedAt: "" } as any,
      isLoading: false,
    } as any);

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
      user: mockUser as any,
      isAuthenticated: true,
      isLoading: false,
    } as any);
    vi.mocked(useUserProfileStore).mockReturnValue({
      profile: { id: "p1", email: mockUser.email, createdAt: "", updatedAt: "" } as any,
      isLoading: false,
    } as any);

    render(<ProfilePage />);

    // Check heading hierarchy
    const mainHeading = screen.getByRole("heading", { level: 1, name: /profile/i });
    expect(mainHeading).toBeInTheDocument();
  });

  it("has accessible tab structure", () => {
    vi.mocked(useUserProfileStore).mockReturnValue({
      user: mockUser,
      isLoading: false,
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
      user: null,
      isLoading: true,
    });

    render(<ProfilePage />);

    // Check that accessible loading skeletons are present
    const statuses = screen.getAllByRole("status", { name: /loading content/i });
    expect(statuses.length).toBeGreaterThan(0);
  });

  // Removed brittle class assertions for container spacing; UI semantics are validated above.
});
