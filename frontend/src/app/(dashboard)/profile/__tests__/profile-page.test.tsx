import { useUserProfileStore } from "@/stores/user-store";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProfilePage from "../page";

// Mock the stores and profile components
vi.mock("@/stores/user-store");
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
    (useUserProfileStore as any).mockReturnValue({
      user: null,
      isLoading: true,
    });

    render(<ProfilePage />);

    // Check for skeleton loading elements
    expect(screen.getAllByTestId("skeleton").length).toBeGreaterThan(0);
  });

  it("renders not found state when user is not logged in", () => {
    (useUserProfileStore as any).mockReturnValue({
      user: null,
      isLoading: false,
    });

    render(<ProfilePage />);

    expect(screen.getByText("Profile Not Found")).toBeInTheDocument();
    expect(screen.getByText("Please log in to view your profile.")).toBeInTheDocument();
  });

  it("renders profile page with tabs when user is logged in", () => {
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      isLoading: false,
    });

    render(<ProfilePage />);

    expect(screen.getByText("Profile")).toBeInTheDocument();
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
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      isLoading: false,
    });

    render(<ProfilePage />);

    expect(screen.getByTestId("personal-info-section")).toBeInTheDocument();
  });

  it("switches to account settings tab", async () => {
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      isLoading: false,
    });

    render(<ProfilePage />);

    const accountTab = screen.getByText("Account");
    fireEvent.click(accountTab);

    await waitFor(() => {
      expect(screen.getByTestId("account-settings-section")).toBeInTheDocument();
    });
  });

  it("switches to preferences tab", async () => {
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      isLoading: false,
    });

    render(<ProfilePage />);

    const preferencesTab = screen.getByText("Preferences");
    fireEvent.click(preferencesTab);

    await waitFor(() => {
      expect(screen.getByTestId("preferences-section")).toBeInTheDocument();
    });
  });

  it("switches to security tab", async () => {
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      isLoading: false,
    });

    render(<ProfilePage />);

    const securityTab = screen.getByText("Security");
    fireEvent.click(securityTab);

    await waitFor(() => {
      expect(screen.getByTestId("security-section")).toBeInTheDocument();
    });
  });

  it("renders tab icons correctly", () => {
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      isLoading: false,
    });

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
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      isLoading: false,
    });

    render(<ProfilePage />);

    // Switch to preferences tab
    const preferencesTab = screen.getByText("Preferences");
    fireEvent.click(preferencesTab);

    await waitFor(() => {
      expect(screen.getByTestId("preferences-section")).toBeInTheDocument();
    });

    // Switch back to personal tab
    const personalTab = screen.getByText("Personal");
    fireEvent.click(personalTab);

    await waitFor(() => {
      expect(screen.getByTestId("personal-info-section")).toBeInTheDocument();
    });
  });

  it("renders proper heading structure", () => {
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      isLoading: false,
    });

    render(<ProfilePage />);

    // Check heading hierarchy
    const mainHeading = screen.getByRole("heading", { level: 1 });
    expect(mainHeading).toHaveTextContent("Profile");
  });

  it("has accessible tab structure", () => {
    (useUserProfileStore as any).mockReturnValue({
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
    (useUserProfileStore as any).mockReturnValue({
      user: null,
      isLoading: true,
    });

    render(<ProfilePage />);

    // Check that loading skeletons are properly displayed
    const container = screen.getByText(/container/i).closest("div");
    const skeletons = screen.getAllByTestId("skeleton");

    expect(skeletons.length).toBeGreaterThan(3); // Multiple skeleton elements
  });

  it("displays proper container and spacing", () => {
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      isLoading: false,
    });

    render(<ProfilePage />);

    const mainContainer = screen.getByText("Profile").closest("div");
    expect(mainContainer).toHaveClass("container");
  });
});
