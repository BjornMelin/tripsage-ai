/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SidebarNav } from "../sidebar-nav";

// Mock usePathname
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

describe("SidebarNav", () => {
  const items = [
    { href: "/dashboard", title: "Overview" },
    { href: "/dashboard/trips", title: "Trips" },
  ];

  it("renders navigation items", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/dashboard");

    render(<SidebarNav items={items} />);

    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Trips")).toBeInTheDocument();
  });

  it("highlights the active item (exact match)", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/dashboard");

    render(<SidebarNav items={items} />);

    const overviewLink = screen.getByText("Overview").closest("a");
    const tripsLink = screen.getByText("Trips").closest("a");

    expect(overviewLink).toHaveClass("bg-accent");
    expect(tripsLink).not.toHaveClass("bg-accent");
  });

  it("highlights the active item (nested match)", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/dashboard/trips/123");

    render(<SidebarNav items={items} />);

    const overviewLink = screen.getByText("Overview").closest("a");
    const tripsLink = screen.getByText("Trips").closest("a");

    expect(overviewLink).not.toHaveClass("bg-accent");
    expect(tripsLink).toHaveClass("bg-accent");
  });

  it("does not highlight dashboard on nested routes unrelated to dashboard root", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/dashboard/trips");

    render(<SidebarNav items={items} />);

    const overviewLink = screen.getByText("Overview").closest("a");
    expect(overviewLink).not.toHaveClass("bg-accent");
  });
});
