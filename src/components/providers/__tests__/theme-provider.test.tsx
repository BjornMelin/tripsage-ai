/** @vitest-environment jsdom */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useTheme } from "@/hooks/use-theme";
import { ThemeProvider } from "../theme-provider";

function ThemeControls() {
  const { resolvedTheme, setTheme, theme } = useTheme();

  return (
    <div>
      <output aria-label="theme">{theme}</output>
      <output aria-label="resolved theme">{resolvedTheme}</output>
      <button type="button" onClick={() => setTheme("dark")}>
        Dark
      </button>
      <button type="button" onClick={() => setTheme("system")}>
        System
      </button>
    </div>
  );
}

function SetSystemDarkMode(matches: boolean): void {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn((query: string): MediaQueryList => {
      const mediaQueryList: MediaQueryList = {
        addEventListener: vi.fn(),
        addListener: vi.fn(),
        dispatchEvent: vi.fn(),
        matches: query === "(prefers-color-scheme: dark)" ? matches : false,
        media: query,
        onchange: null,
        removeEventListener: vi.fn(),
        removeListener: vi.fn(),
      };
      return mediaQueryList;
    }),
    writable: true,
  });
}

function GetThemeClassAdds(addSpy: { mock: { calls: unknown[][] } }): string[] {
  return addSpy.mock.calls
    .flatMap((call: unknown[]) => call)
    .filter(
      (className: unknown): className is string =>
        className === "light" || className === "dark"
    );
}

describe("ThemeProvider", () => {
  beforeEach(() => {
    SetSystemDarkMode(false);
    window.localStorage.clear();
    document.documentElement.className = "";
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.style.colorScheme = "";
    document.head.querySelectorAll("style").forEach((style) => {
      style.remove();
    });
  });

  it("persists selected themes and applies the html class", async () => {
    render(
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <ThemeControls />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(document.documentElement).toHaveClass("light");
    });

    fireEvent.click(screen.getByRole("button", { name: "Dark" }));

    await waitFor(() => {
      expect(screen.getByLabelText("theme")).toHaveTextContent("dark");
      expect(screen.getByLabelText("resolved theme")).toHaveTextContent("dark");
      expect(document.documentElement).toHaveClass("dark");
    });
    expect(window.localStorage.getItem("theme")).toBe("dark");
  });

  it("keeps system theme support without rendering client script tags", async () => {
    const { container } = render(
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <ThemeControls />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "System" }));

    await waitFor(() => {
      expect(screen.getByLabelText("theme")).toHaveTextContent("system");
      expect(screen.getByLabelText("resolved theme")).toHaveTextContent("light");
      expect(document.documentElement).toHaveClass("light");
    });
    expect(container.querySelector("script")).toBeNull();
  });

  it("applies persisted dark theme as the first html theme class", async () => {
    window.localStorage.setItem("theme", "dark");
    const addSpy = vi.spyOn(DOMTokenList.prototype, "add");

    render(
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <ThemeControls />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("theme")).toHaveTextContent("dark");
      expect(screen.getByLabelText("resolved theme")).toHaveTextContent("dark");
      expect(document.documentElement).toHaveClass("dark");
    });

    expect(GetThemeClassAdds(addSpy)[0]).toBe("dark");
    addSpy.mockRestore();
  });

  it("applies system dark mode as the first html theme class", async () => {
    SetSystemDarkMode(true);
    const addSpy = vi.spyOn(DOMTokenList.prototype, "add");

    render(
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <ThemeControls />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("theme")).toHaveTextContent("system");
      expect(screen.getByLabelText("resolved theme")).toHaveTextContent("dark");
      expect(document.documentElement).toHaveClass("dark");
    });

    expect(GetThemeClassAdds(addSpy)[0]).toBe("dark");
    addSpy.mockRestore();
  });
});
