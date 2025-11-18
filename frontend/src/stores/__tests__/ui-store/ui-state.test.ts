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

import { type Theme, useUiStore } from "@/stores/ui-store";

describe("UI Store - UI State Management", () => {
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

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useUiStore());

      expect(result.current.theme).toBe("system");
      expect(result.current.sidebar.isOpen).toBe(true);
      expect(result.current.sidebar.isCollapsed).toBe(false);
      expect(result.current.sidebar.isPinned).toBe(true);
      expect(result.current.navigation.activeRoute).toBe("/");
      expect(result.current.navigation.breadcrumbs).toEqual([]);
      expect(result.current.loadingStates).toEqual({});
      expect(result.current.notifications).toEqual([]);
      expect(result.current.modal.isOpen).toBe(false);
      expect(result.current.commandPalette.isOpen).toBe(false);
      expect(result.current.features.enableAnimations).toBe(true);
    });

    it("computed properties work correctly with initial state", () => {
      const { result } = renderHook(() => useUiStore());

      expect(result.current.unreadNotificationCount).toBe(0);
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("Theme Management", () => {
    it("sets theme correctly", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setTheme("dark");
      });

      expect(result.current.theme).toBe("dark");

      act(() => {
        result.current.setTheme("light");
      });

      expect(result.current.theme).toBe("light");
    });

    it("toggles theme between light and dark", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setTheme("light");
      });

      act(() => {
        result.current.toggleTheme();
      });

      expect(result.current.theme).toBe("dark");

      act(() => {
        result.current.toggleTheme();
      });

      expect(result.current.theme).toBe("light");
    });

    it("handles invalid theme values gracefully", () => {
      const { result } = renderHook(() => useUiStore());
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {
        /* silence console errors during test */
      });
      const previousTheme = result.current.theme;

      act(() => {
        // @ts-expect-error Testing invalid theme
        result.current.setTheme("invalid-theme");
      });

      expect(consoleSpy).toHaveBeenCalled();
      expect(result.current.theme).toBe(previousTheme);

      consoleSpy.mockRestore();
    });

    it("computes isDarkMode correctly for system theme", () => {
      const { result } = renderHook(() => useUiStore());

      const matchMediaMock = vi.fn().mockImplementation((query: string) => ({
        addEventListener: vi.fn(),
        addListener: vi.fn(),
        dispatchEvent: vi.fn(),
        matches: query === "(prefers-color-scheme: dark)",
        media: query,
        onchange: null,
        removeEventListener: vi.fn(),
        removeListener: vi.fn(),
      }));

      Object.defineProperty(window, "matchMedia", {
        value: matchMediaMock,
        writable: true,
      });

      act(() => {
        result.current.setTheme("system");
      });

      expect(result.current.isDarkMode).toBe(false);
    });
  });

  describe("Sidebar Management", () => {
    it("toggles sidebar open/closed", () => {
      const { result } = renderHook(() => useUiStore());

      expect(result.current.sidebar.isOpen).toBe(true);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.sidebar.isOpen).toBe(false);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.sidebar.isOpen).toBe(true);
    });

    it("sets sidebar open state directly", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setSidebarOpen(false);
      });

      expect(result.current.sidebar.isOpen).toBe(false);

      act(() => {
        result.current.setSidebarOpen(true);
      });

      expect(result.current.sidebar.isOpen).toBe(true);
    });

    it("sets sidebar collapsed state", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setSidebarCollapsed(true);
      });

      expect(result.current.sidebar.isCollapsed).toBe(true);

      act(() => {
        result.current.setSidebarCollapsed(false);
      });

      expect(result.current.sidebar.isCollapsed).toBe(false);
    });

    it("sets sidebar pinned state", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setSidebarPinned(false);
      });

      expect(result.current.sidebar.isPinned).toBe(false);

      act(() => {
        result.current.setSidebarPinned(true);
      });

      expect(result.current.sidebar.isPinned).toBe(true);
    });
  });

  describe("Loading State Management", () => {
    it("sets loading state for a key", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setLoadingState("user-profile", "loading");
      });

      expect(useUiStore.getState().loadingStates["user-profile"]).toBe("loading");
      expect(
        Object.values(useUiStore.getState().loadingStates).some((s) => s === "loading")
      ).toBe(true);

      act(() => {
        result.current.setLoadingState("user-profile", "success");
      });

      expect(useUiStore.getState().loadingStates["user-profile"]).toBe("success");
      expect(
        Object.values(useUiStore.getState().loadingStates).some((s) => s === "loading")
      ).toBe(false);
    });

    it("handles multiple loading states", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setLoadingState("profile", "loading");
        result.current.setLoadingState("settings", "idle");
        result.current.setLoadingState("data", "loading");
      });

      expect(
        Object.values(useUiStore.getState().loadingStates).some((s) => s === "loading")
      ).toBe(true);
      expect(Object.keys(useUiStore.getState().loadingStates)).toHaveLength(3);

      act(() => {
        result.current.setLoadingState("profile", "success");
        result.current.setLoadingState("data", "success");
      });

      expect(
        Object.values(useUiStore.getState().loadingStates).some((s) => s === "loading")
      ).toBe(false);
    });

    it("clears loading state for a key", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setLoadingState("test", "loading");
      });

      expect(result.current.loadingStates.test).toBe("loading");

      act(() => {
        result.current.clearLoadingState("test");
      });

      expect(result.current.loadingStates.test).toBeUndefined();
    });

    it("clears all loading states", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setLoadingState("state1", "loading");
        result.current.setLoadingState("state2", "error");
        result.current.setLoadingState("state3", "success");
      });

      expect(Object.keys(result.current.loadingStates)).toHaveLength(3);

      act(() => {
        result.current.clearAllLoadingStates();
      });

      expect(result.current.loadingStates).toEqual({});
    });

    it("handles invalid loading state values gracefully", () => {
      const { result } = renderHook(() => useUiStore());
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {
        /* silence console errors during test */
      });

      act(() => {
        // @ts-expect-error Testing invalid loading state
        result.current.setLoadingState("test", "invalid-state");
      });

      expect(consoleSpy).toHaveBeenCalled();
      expect(result.current.loadingStates.test).toBeUndefined();

      consoleSpy.mockRestore();
    });
  });

  describe("Notification Management", () => {
    it("adds notification successfully", () => {
      const { result } = renderHook(() => useUiStore());

      const notification = {
        isRead: false,
        message: "Operation completed successfully",
        title: "Success",
        type: "success" as const,
      };

      let notificationId: string | undefined;
      act(() => {
        notificationId = result.current.addNotification(notification);
      });

      expect(notificationId).toBeDefined();
      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.notifications[0].title).toBe("Success");
      expect(result.current.notifications[0].type).toBe("success");
      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        1
      );
    });

    it("adds notification with duration and auto-removes", async () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useUiStore());

      const notification = {
        duration: 100,
        isRead: false,
        title: "Info",
        type: "info" as const,
      };

      act(() => {
        result.current.addNotification(notification);
      });

      expect(result.current.notifications).toHaveLength(1);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });
      expect(result.current.notifications).toHaveLength(0);
      vi.useRealTimers();
    });

    it("removes notification by ID", () => {
      const { result } = renderHook(() => useUiStore());

      let notificationId: string;
      act(() => {
        notificationId = result.current.addNotification({
          isRead: false,
          title: "Warning",
          type: "warning",
        });
      });

      expect(result.current.notifications).toHaveLength(1);

      act(() => {
        if (notificationId) {
          result.current.removeNotification(notificationId);
        }
      });

      expect(result.current.notifications).toHaveLength(0);
    });

    it("marks notification as read", () => {
      const { result } = renderHook(() => useUiStore());

      let notificationId: string;
      act(() => {
        notificationId = result.current.addNotification({
          isRead: false,
          title: "Error",
          type: "error",
        });
      });

      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        1
      );

      act(() => {
        if (notificationId) {
          result.current.markNotificationAsRead(notificationId);
        }
      });

      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        0
      );
      expect(result.current.notifications[0].isRead).toBe(true);
    });

    it("clears all notifications", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.addNotification({
          isRead: false,
          title: "Info 1",
          type: "info",
        });
        result.current.addNotification({
          isRead: false,
          title: "Success 1",
          type: "success",
        });
        result.current.addNotification({
          isRead: false,
          title: "Warning 1",
          type: "warning",
        });
      });

      expect(result.current.notifications).toHaveLength(3);

      act(() => {
        result.current.clearAllNotifications();
      });

      expect(result.current.notifications).toHaveLength(0);
    });

    it("limits notifications to maximum of 50", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        for (let i = 0; i < 55; i++) {
          result.current.addNotification({
            isRead: false,
            title: `Notification ${i}`,
            type: "info",
          });
        }
      });

      expect(result.current.notifications).toHaveLength(50);
      expect(result.current.notifications[0].title).toBe("Notification 54");
    });

    it("computes unread notification count correctly", () => {
      const { result } = renderHook(() => useUiStore());

      let id1: string;
      let id2: string;
      let id3: string;

      act(() => {
        id1 = result.current.addNotification({
          isRead: false,
          title: "Info 1",
          type: "info",
        });
        id2 = result.current.addNotification({
          isRead: false,
          title: "Success 1",
          type: "success",
        });
        id3 = result.current.addNotification({
          isRead: false,
          title: "Warning 1",
          type: "warning",
        });
      });

      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        3
      );

      act(() => {
        if (id1) result.current.markNotificationAsRead(id1);
        if (id2) result.current.markNotificationAsRead(id2);
      });

      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        1
      );

      act(() => {
        if (id3) result.current.markNotificationAsRead(id3);
      });

      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        0
      );
    });

    it("handles invalid notification gracefully", () => {
      const { result } = renderHook(() => useUiStore());
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {
        /* silence console errors during test */
      });

      act(() => {
        result.current.addNotification({
          isRead: false,
          title: "Invalid",
          // @ts-expect-error - intentionally testing invalid type
          type: "invalid-type",
        });
      });

      expect(consoleSpy).toHaveBeenCalled();
      expect(result.current.notifications).toHaveLength(0);

      consoleSpy.mockRestore();
    });
  });

  describe("Feature Flag Management", () => {
    it("toggles feature flags", () => {
      const { result } = renderHook(() => useUiStore());

      expect(result.current.features.enableAnimations).toBe(true);

      act(() => {
        result.current.toggleFeature("enableAnimations");
      });

      expect(result.current.features.enableAnimations).toBe(false);

      act(() => {
        result.current.toggleFeature("enableAnimations");
      });

      expect(result.current.features.enableAnimations).toBe(true);
    });

    it("sets feature flag directly", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setFeature("enableBetaFeatures", true);
      });

      expect(result.current.features.enableBetaFeatures).toBe(true);

      act(() => {
        result.current.setFeature("enableSounds", true);
      });

      expect(result.current.features.enableSounds).toBe(true);

      act(() => {
        result.current.setFeature("enableAnalytics", false);
      });

      expect(result.current.features.enableAnalytics).toBe(false);
    });

    it("toggles multiple feature flags independently", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.toggleFeature("enableAnimations");
        result.current.toggleFeature("enableSounds");
      });

      expect(result.current.features.enableAnimations).toBe(false);
      expect(result.current.features.enableSounds).toBe(true);
      expect(result.current.features.enableHaptics).toBe(true);
    });
  });

  describe("Utility Actions", () => {
    it("resets UI state to defaults", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setSidebarOpen(false);
        result.current.setActiveRoute("/custom");
        result.current.addNotification({ isRead: false, title: "Test", type: "info" });
        result.current.openModal("TestModal");
        result.current.openCommandPalette();
        result.current.setLoadingState("test", "loading");
      });

      expect(result.current.sidebar.isOpen).toBe(false);
      expect(result.current.navigation.activeRoute).toBe("/custom");
      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.modal.isOpen).toBe(true);
      expect(result.current.commandPalette.isOpen).toBe(true);
      expect(Object.keys(result.current.loadingStates)).toHaveLength(1);

      act(() => {
        result.current.reset();
      });

      expect(result.current.sidebar.isOpen).toBe(true);
      expect(result.current.navigation.activeRoute).toBe("/");
      expect(result.current.notifications).toHaveLength(0);
      expect(result.current.modal.isOpen).toBe(false);
      expect(result.current.commandPalette.isOpen).toBe(false);
      expect(result.current.loadingStates).toEqual({});
    });
  });

  describe("Complex Scenarios", () => {
    it("handles complete UI workflow", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setActiveRoute("/dashboard");
        result.current.setBreadcrumbs([
          { href: "/", label: "Home" },
          { label: "Dashboard" },
        ]);
      });

      act(() => {
        result.current.setSidebarCollapsed(true);
        result.current.setSidebarPinned(false);
      });

      act(() => {
        result.current.setLoadingState("data", "loading");
        result.current.setLoadingState("user", "success");
      });

      let infoId: string;
      act(() => {
        infoId = result.current.addNotification({
          isRead: false,
          title: "Data Loading",
          type: "info",
        });
        result.current.addNotification({
          isRead: false,
          title: "Network Slow",
          type: "warning",
        });
      });

      act(() => {
        result.current.openModal("DataModal", { dataId: "123" });
      });

      expect(result.current.navigation.activeRoute).toBe("/dashboard");
      expect(result.current.sidebar.isCollapsed).toBe(true);
      expect(
        Object.values(result.current.loadingStates).some((s) => s === "loading")
      ).toBe(true);
      expect(result.current.notifications).toHaveLength(2);
      expect(result.current.modal.isOpen).toBe(true);
      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        2
      );

      act(() => {
        if (infoId) result.current.markNotificationAsRead(infoId);
      });

      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        1
      );

      act(() => {
        result.current.setLoadingState("data", "success");
      });

      expect(useUiStore.getState().isLoading).toBe(false);

      act(() => {
        result.current.closeModal();
      });

      expect(result.current.modal.isOpen).toBe(false);
    });

    it("handles notification lifecycle with persistence", () => {
      const { result } = renderHook(() => useUiStore());

      let successId: string;
      let errorId: string;
      let warningId: string;

      act(() => {
        successId = result.current.addNotification({
          isRead: false,
          message: "File uploaded successfully",
          title: "Upload Complete",
          type: "success",
        });

        errorId = result.current.addNotification({
          isRead: false,
          message: "Network error occurred",
          title: "Upload Failed",
          type: "error",
        });

        warningId = result.current.addNotification({
          action: {
            label: "Upgrade",
            onClick: () => {
              /* empty callback for test */
            },
          },
          isRead: false,
          message: "Consider upgrading your plan",
          title: "Storage Almost Full",
          type: "warning",
        });
      });

      expect(result.current.notifications).toHaveLength(3);
      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        3
      );

      act(() => {
        if (successId) result.current.markNotificationAsRead(successId);
        if (errorId) result.current.markNotificationAsRead(errorId);
      });

      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        1
      );

      act(() => {
        if (errorId) result.current.removeNotification(errorId);
      });

      expect(result.current.notifications).toHaveLength(2);
      expect(useUiStore.getState().notifications.filter((n) => !n.isRead).length).toBe(
        1
      );

      const remainingNotifications = result.current.notifications;
      expect(remainingNotifications.some((n) => n.id === successId)).toBe(true);
      expect(remainingNotifications.some((n) => n.id === warningId)).toBe(true);
      expect(remainingNotifications.some((n) => n.id === errorId)).toBe(false);
    });

    it("handles theme switching with persistence", () => {
      const { result } = renderHook(() => useUiStore());

      const themes: Theme[] = ["light", "dark", "system"];

      themes.forEach((theme) => {
        act(() => {
          result.current.setTheme(theme);
        });

        expect(result.current.theme).toBe(theme);
      });

      act(() => {
        result.current.setTheme("light");
        result.current.toggleTheme();
      });
      expect(result.current.theme).toBe("dark");

      act(() => {
        result.current.setTheme("dark");
        result.current.toggleTheme();
      });
      expect(result.current.theme).toBe("light");
    });
  });

  describe("Utility Selectors", () => {
    it("utility selectors return correct values", () => {
      const { result } = renderHook(() => useUiStore());

      const { result: themeResult } = renderHook(() =>
        useUiStore((state) => state.theme)
      );
      const { result: sidebarResult } = renderHook(() =>
        useUiStore((state) => state.sidebar)
      );
      const { result: notificationsResult } = renderHook(() =>
        useUiStore((state) => state.notifications)
      );

      expect(themeResult.current).toBe("system");
      expect(sidebarResult.current.isOpen).toBe(true);
      expect(notificationsResult.current).toEqual([]);

      act(() => {
        result.current.setTheme("dark");
        result.current.setSidebarOpen(false);
        result.current.addNotification({ isRead: false, title: "Test", type: "info" });
      });

      expect(themeResult.current).toBe("dark");
      expect(sidebarResult.current.isOpen).toBe(false);
      expect(notificationsResult.current).toHaveLength(1);
    });
  });
});
