/** @vitest-environment jsdom */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ROUTES } from "@/lib/routes";
import { Navbar } from "../navbar";

const USE_PATHNAME_MOCK = vi.hoisted(() => vi.fn(() => "/"));

vi.mock("next/navigation", () => ({
  usePathname: () => USE_PATHNAME_MOCK(),
}));

vi.mock("@/components/ui/theme-toggle", () => ({
  ThemeToggle: () => <button type="button">Toggle theme</button>,
}));

describe("Navbar", () => {
  beforeEach(() => {
    USE_PATHNAME_MOCK.mockReturnValue("/");
  });

  it("marks the active navigation link", () => {
    USE_PATHNAME_MOCK.mockReturnValue(ROUTES.dashboard.trips);

    render(<Navbar />);

    expect(screen.getByRole("link", { name: "Trips" })).toHaveAttribute(
      "aria-current",
      "page"
    );
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute(
      "aria-current"
    );
  });

  it("opens the mobile navigation with auth actions", async () => {
    const user = userEvent.setup();

    render(<Navbar />);

    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));

    const mobileNav = screen.getByRole("navigation", {
      name: "Mobile navigation",
    });

    expect(within(mobileNav).getByRole("link", { name: "Home" })).toHaveAttribute(
      "href",
      "/"
    );
    expect(within(mobileNav).getByRole("link", { name: "Log in" })).toHaveAttribute(
      "href",
      ROUTES.login
    );
    expect(within(mobileNav).getByRole("link", { name: "Sign up" })).toHaveAttribute(
      "href",
      ROUTES.register
    );
    expect(
      screen.getByRole("button", { name: "Close navigation menu" })
    ).toHaveAttribute("aria-expanded", "true");
  });
});
