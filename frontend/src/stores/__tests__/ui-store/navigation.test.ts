/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Ensure matchMedia is mocked before importing the store
Object.defineProperty(window, "matchMedia", {
  configurable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    addEventListener: vi.fn(),
    addListener: vi.fn(),
    dispatchEvent: vi.fn(),
    matches: false,
    media: query,
    onchange: null,
    removeEventListener: vi.fn(),
    removeListener: vi.fn(),
  })),
  writable: true,
});

import { useUiStore } from "@/stores/ui-store";

describe("UI Store - Navigation", () => {
  beforeEach(() => {
    act(() => {
      useUiStore.getState().reset();
      useUiStore.setState({
        features: {
          enableAnalytics: true,
          enableAnimations: true,
          enableBetaFeatures: false,
          enableHaptics: true,
          enableSounds: false,
        },
        theme: "system",
      });
    });
  });

  describe("Navigation Management", () => {
    it("sets active route", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setActiveRoute("/dashboard");
      });

      expect(result.current.navigation.activeRoute).toBe("/dashboard");

      act(() => {
        result.current.setActiveRoute("/profile");
      });

      expect(result.current.navigation.activeRoute).toBe("/profile");
    });

    it("sets breadcrumbs", () => {
      const { result } = renderHook(() => useUiStore());

      const breadcrumbs = [
        { href: "/", label: "Home" },
        { href: "/dashboard", label: "Dashboard" },
        { label: "Profile" },
      ];

      act(() => {
        result.current.setBreadcrumbs(breadcrumbs);
      });

      expect(result.current.navigation.breadcrumbs).toEqual(breadcrumbs);
    });

    it("adds breadcrumb to existing list", () => {
      const { result } = renderHook(() => useUiStore());

      const initialBreadcrumbs = [
        { href: "/", label: "Home" },
        { href: "/dashboard", label: "Dashboard" },
      ];

      act(() => {
        result.current.setBreadcrumbs(initialBreadcrumbs);
      });

      act(() => {
        result.current.addBreadcrumb({ label: "Profile" });
      });

      expect(result.current.navigation.breadcrumbs).toHaveLength(3);
      expect(result.current.navigation.breadcrumbs[2].label).toBe("Profile");
    });
  });
});
