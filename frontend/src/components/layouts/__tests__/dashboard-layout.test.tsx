/** @vitest-environment jsdom */

import type { User } from "@supabase/supabase-js";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  DASHBOARD_NAV_ITEMS,
  DashboardLayoutView,
  fetchDashboardLayoutData,
} from "../dashboard-layout";

const REQUIRE_USER_MOCK = vi.hoisted(() => vi.fn());
const MAP_SUPABASE_USER_TO_AUTH_USER_MOCK = vi.hoisted(() => vi.fn());

vi.mock("@/lib/auth/server", () => ({
  mapSupabaseUserToAuthUser: MAP_SUPABASE_USER_TO_AUTH_USER_MOCK,
  requireUser: REQUIRE_USER_MOCK,
}));

// Mock Client Components
vi.mock("../sidebar-nav", () => ({
  SidebarNav: ({ items }: { items: { title: string }[] }) => (
    <div data-testid="sidebar-nav">{items.map((item) => item.title).join(",")}</div>
  ),
}));

vi.mock("../user-nav", () => ({
  UserNav: ({ user }: { user: { displayName: string } }) => (
    <div data-testid="user-nav">{user.displayName}</div>
  ),
}));

vi.mock("@/components/ui/theme-toggle", () => ({
  ThemeToggle: () => <div data-testid="theme-toggle">ThemeToggle</div>,
}));

describe("fetchDashboardLayoutData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns mapped user and nav items", async () => {
    const supabaseUser = {
      email: "test@example.com",
      id: "123",
    } as User;
    const mappedUser = {
      displayName: "Test User",
      email: "test@example.com",
      id: "123",
    };

    REQUIRE_USER_MOCK.mockResolvedValue({ user: supabaseUser });
    MAP_SUPABASE_USER_TO_AUTH_USER_MOCK.mockReturnValue(mappedUser);

    const result = await fetchDashboardLayoutData();

    expect(REQUIRE_USER_MOCK).toHaveBeenCalledTimes(1);
    expect(MAP_SUPABASE_USER_TO_AUTH_USER_MOCK).toHaveBeenCalledWith(supabaseUser);
    expect(result.user).toEqual(mappedUser);
    expect(result.navItems).toEqual(DASHBOARD_NAV_ITEMS);
  });
});

describe("DashboardLayoutView", () => {
  it("renders layout with provided data", () => {
    const user = {
      createdAt: "2024-01-01T00:00:00Z",
      displayName: "Test User",
      email: "test@example.com",
      id: "123",
      isEmailVerified: true,
      updatedAt: "2024-01-02T00:00:00Z",
    };

    render(
      <DashboardLayoutView navItems={DASHBOARD_NAV_ITEMS} user={user}>
        <div data-testid="child">Child Content</div>
      </DashboardLayoutView>
    );

    expect(screen.getByTestId("sidebar-nav")).toHaveTextContent("Overview");
    expect(screen.getByTestId("user-nav")).toHaveTextContent("Test User");
    expect(screen.getByTestId("theme-toggle")).toBeInTheDocument();
    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByText("TripSage AI")).toBeInTheDocument();
  });
});
