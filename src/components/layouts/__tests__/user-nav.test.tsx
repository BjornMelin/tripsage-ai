/** @vitest-environment jsdom */

import type { AuthUser } from "@schemas/stores";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UserNav } from "../user-nav";

const { logoutMock, refreshMock, replaceMock, toastMock } = vi.hoisted(() => ({
  logoutMock: vi.fn(async () => undefined),
  refreshMock: vi.fn(),
  replaceMock: vi.fn(),
  toastMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: refreshMock, replace: replaceMock }),
}));

vi.mock("@/features/auth/store/auth/auth-core", () => ({
  useAuthCore: (selector: (state: { logout: typeof logoutMock }) => unknown) =>
    selector({ logout: logoutMock }),
}));

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: toastMock }),
}));

describe("UserNav", () => {
  const mockUser: AuthUser = {
    createdAt: new Date().toISOString(),
    displayName: "Test User",
    email: "test@example.com",
    id: "123",
    isEmailVerified: true,
    updatedAt: new Date().toISOString(),
  };

  beforeEach(() => {
    logoutMock.mockReset().mockResolvedValue(undefined);
    refreshMock.mockClear();
    replaceMock.mockClear();
    toastMock.mockClear();
  });

  it("renders user avatar and name", () => {
    render(<UserNav user={mockUser} />);

    expect(screen.getByText("Test User")).toBeInTheDocument();
    // Avatar fallback should be initials
    expect(screen.getByText("TU")).toBeInTheDocument();
  });

  it("opens popover and shows menu items", async () => {
    render(<UserNav user={mockUser} />);

    const trigger = screen.getByRole("button", {
      name: "Open account menu for Test User",
    });
    await userEvent.click(trigger);

    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Security")).toBeInTheDocument();
    expect(screen.getByText("Log Out")).toBeInTheDocument();
  });

  it("logs out through the auth store and returns to login", async () => {
    render(<UserNav user={mockUser} />);

    // Open popover
    await userEvent.click(
      screen.getByRole("button", { name: "Open account menu for Test User" })
    );

    // Click logout
    await userEvent.click(screen.getByText("Log Out"));

    await waitFor(() => {
      expect(logoutMock).toHaveBeenCalledTimes(1);
      expect(replaceMock).toHaveBeenCalledWith("/login");
      expect(refreshMock).toHaveBeenCalledTimes(1);
    });
  });

  it("keeps the current page and reports a failed logout", async () => {
    logoutMock.mockRejectedValueOnce(new Error("Failed to log out."));
    render(<UserNav user={mockUser} />);

    await userEvent.click(screen.getByRole("button", { name: /open account menu/i }));
    await userEvent.click(screen.getByText("Log Out"));

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith({
        description: "Your session is still active. Please try again.",
        title: "Logout failed",
        variant: "destructive",
      });
    });
    expect(replaceMock).not.toHaveBeenCalled();
    expect(refreshMock).not.toHaveBeenCalled();
  });
});
