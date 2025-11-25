/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DashboardLayout } from "../dashboard-layout";

// Mock dependencies
vi.mock("@/lib/auth/server", () => ({
  requireUser: vi.fn(() => Promise.resolve({ user: { id: "123", email: "test@example.com" } })),
  mapSupabaseUserToAuthUser: vi.fn((user) => ({
    id: user.id,
    email: user.email,
    displayName: "Test User",
  })),
}));

// Mock Client Components
vi.mock("../sidebar-nav", () => ({
  SidebarNav: () => <div data-testid="sidebar-nav">SidebarNav</div>,
}));

vi.mock("../user-nav", () => ({
  UserNav: ({ user }: { user: any }) => <div data-testid="user-nav">{user.displayName}</div>,
}));

vi.mock("@/components/ui/theme-toggle", () => ({
  ThemeToggle: () => <div data-testid="theme-toggle">ThemeToggle</div>,
}));

describe("DashboardLayout", () => {
  it("renders layout with user data", async () => {
    // Since DashboardLayout is an async Server Component, we need to await it
    const Layout = await DashboardLayout({ children: <div data-testid="child">Child Content</div> });
    
    // In a real Server Component test environment, we might need more setup,
    // but for unit testing the logic, we can render the result.
    render(Layout);

    expect(screen.getByTestId("sidebar-nav")).toBeInTheDocument();
    expect(screen.getByTestId("user-nav")).toHaveTextContent("Test User");
    expect(screen.getByTestId("theme-toggle")).toBeInTheDocument();
    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByText("TripSage AI")).toBeInTheDocument();
  });
});
