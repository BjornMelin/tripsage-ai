/** @vitest-environment jsdom */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UserNav } from "../user-nav";
import type { AuthUser } from "@/domain/schemas/stores";

// Mock logoutAction
vi.mock("@/lib/auth/actions", () => ({
  logoutAction: vi.fn(),
}));

describe("UserNav", () => {
  const mockUser: AuthUser = {
    id: "123",
    email: "test@example.com",
    displayName: "Test User",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    isEmailVerified: true,
  };

  it("renders user avatar and name", () => {
    render(<UserNav user={mockUser} />);

    expect(screen.getByText("Test User")).toBeInTheDocument();
    // Avatar fallback should be initials
    expect(screen.getByText("TU")).toBeInTheDocument();
  });

  it("opens popover and shows menu items", async () => {
    render(<UserNav user={mockUser} />);

    const trigger = screen.getByRole("button");
    await userEvent.click(trigger);

    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Log out")).toBeInTheDocument();
  });

  it("calls logoutAction when logout button is clicked", async () => {
    const { logoutAction } = await import("@/lib/auth/actions");
    render(<UserNav user={mockUser} />);

    // Open popover
    await userEvent.click(screen.getByRole("button"));

    // Click logout
    await userEvent.click(screen.getByText("Log out"));

    await waitFor(() => {
      expect(logoutAction).toHaveBeenCalled();
    });
  });
});
