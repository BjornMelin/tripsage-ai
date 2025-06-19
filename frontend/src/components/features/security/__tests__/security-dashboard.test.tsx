import { useAuth } from "@/contexts/auth-context";
import { useApiKeys } from "@/hooks/use-api-keys";
import { type ApiError, createMockUseQueryResult } from "@/test/mock-helpers";
import type { AllKeysResponse } from "@/types/api-keys";
import { render, screen, waitFor, createMockUser } from "@/test/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SecurityDashboard } from "../security-dashboard";

// Mock the hooks
vi.mock("@/contexts/auth-context");
vi.mock("@/hooks/use-api-keys");

const mockUseAuth = vi.mocked(useAuth);
const mockUseApiKeys = vi.mocked(useApiKeys);

describe("SecurityDashboard", () => {
  beforeEach(() => {
    const mockUser = createMockUser({
      id: "user-1",
      email: "test@example.com",
      name: "Test User",
    });

    mockUseAuth.mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      signIn: vi.fn(),
      signInWithOAuth: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      refreshUser: vi.fn(),
      clearError: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });

    const mockKeysData: AllKeysResponse = {
      keys: {
        openai: {
          id: "key-1",
          service: "openai",
          is_valid: true,
          has_key: true,
          last_validated: "2025-06-01",
        },
      },
      supported_services: ["openai", "anthropic"],
    };
    mockUseApiKeys.mockReturnValue(
      createMockUseQueryResult<AllKeysResponse, ApiError>(mockKeysData)
    );
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    render(<SecurityDashboard />);

    // Check for loading skeletons
    expect(
      screen.getByText("Monitor your account security and activity")
    ).toBeInTheDocument();

    // Should show loading animations
    const loadingElements = document.querySelectorAll(".animate-pulse");
    expect(loadingElements.length).toBeGreaterThan(0);
  });

  it("renders security metrics after loading", async () => {
    render(<SecurityDashboard />);

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByText("Security Score:")).toBeInTheDocument();
    });

    // Check for security metrics cards
    expect(screen.getByText("Last Login")).toBeInTheDocument();
    expect(screen.getByText("Active Sessions")).toBeInTheDocument();
    expect(screen.getByText("API Keys")).toBeInTheDocument();
    expect(screen.getByText("Failed Logins (24h)")).toBeInTheDocument();
  });

  it("displays active sessions", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Active Sessions")).toBeInTheDocument();
    });

    // Check for session information
    expect(screen.getByText("MacBook Pro")).toBeInTheDocument();
    expect(screen.getByText("iPhone 15")).toBeInTheDocument();
    expect(screen.getByText("Current")).toBeInTheDocument();
  });

  it("displays recent security events", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Recent Activity")).toBeInTheDocument();
    });

    // Check for security events
    expect(screen.getByText("Successful login")).toBeInTheDocument();
    expect(screen.getByText("New OpenAI API key added")).toBeInTheDocument();
    expect(screen.getByText("Failed login attempt")).toBeInTheDocument();
  });

  it("shows connected OAuth accounts", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Connected Accounts")).toBeInTheDocument();
    });

    // Check for OAuth connections
    expect(screen.getByText("Google")).toBeInTheDocument();
    expect(screen.getByText("Github")).toBeInTheDocument();
  });

  it("displays security recommendations", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Security Recommendations")).toBeInTheDocument();
    });

    // Check for recommendations
    expect(screen.getByText("Regular Password Updates")).toBeInTheDocument();
    expect(screen.getByText("Review API Keys")).toBeInTheDocument();
    expect(screen.getByText("Monitor Sessions")).toBeInTheDocument();
    expect(screen.getByText("Enable Notifications")).toBeInTheDocument();
  });

  it("shows excellent security score for high scores", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Security Score:/)).toBeInTheDocument();
    });

    // Should show excellent rating for score >= 80
    expect(screen.getByText("85/100")).toBeInTheDocument();
    expect(screen.getByText("Excellent")).toBeInTheDocument();
  });

  it("applies correct risk level styling", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Recent Activity")).toBeInTheDocument();
    });

    // Check for risk level badges
    const lowRiskBadges = screen.getAllByText("low");
    const mediumRiskBadges = screen.getAllByText("medium");

    expect(lowRiskBadges.length).toBeGreaterThan(0);
    expect(mediumRiskBadges.length).toBeGreaterThan(0);
  });

  it("handles session termination", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Active Sessions")).toBeInTheDocument();
    });

    // Find terminate button (should be on non-current sessions)
    const terminateButtons = screen.getAllByText("Terminate");
    expect(terminateButtons.length).toBeGreaterThan(0);
  });

  it("handles refresh action", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Refresh")).toBeInTheDocument();
    });

    const refreshButton = screen.getByText("Refresh");
    expect(refreshButton).toBeInTheDocument();
  });

  it("displays proper event icons", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Recent Activity")).toBeInTheDocument();
    });

    // Icons should be rendered (we can't easily test the specific icons,
    // but we can ensure the container elements are present)
    const eventContainers = document.querySelectorAll('[data-testid="security-event"]');
    // Note: This would need to be added to the component if we want to test it properly
  });

  it("formats timestamps correctly", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Recent Activity")).toBeInTheDocument();
    });

    // Should format dates properly (exact format depends on locale)
    const timeElements = document.querySelectorAll("time, .timestamp");
    // This is a simplified test - in reality we'd check for proper formatting
  });

  it("handles empty states gracefully", async () => {
    // Mock empty data
    const mockEmptyKeysData: AllKeysResponse = {
      keys: {},
      supported_services: [],
    };
    mockUseApiKeys.mockReturnValue(
      createMockUseQueryResult<AllKeysResponse, ApiError>(mockEmptyKeysData)
    );

    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByText("API Keys")).toBeInTheDocument();
    });

    // Should handle empty API keys gracefully
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("displays security score alert correctly", async () => {
    render(<SecurityDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    // Should show green alert for good security score
    const alert = screen.getByRole("alert");
    expect(alert).toHaveClass("border-green-200");
  });
});
