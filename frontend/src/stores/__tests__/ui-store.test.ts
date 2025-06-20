import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { type Theme, useUIStore } from "../ui-store";

// Mock window.matchMedia for theme detection
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock setTimeout to make tests run faster
vi.mock("global", () => ({
  setTimeout: vi.fn((fn, delay) => {
    if (delay) {
      return setTimeout(fn, 0); // Execute immediately for tests
    }
    return fn();
  }),
}));

describe("UI Store", () => {
  beforeEach(() => {
    act(() => {
      useUIStore.setState({
        theme: "system",
        sidebar: {
          isOpen: true,
          isCollapsed: false,
          isPinned: true,
        },
        navigation: {
          activeRoute: "/",
          breadcrumbs: [],
        },
        loadingStates: {},
        notifications: [],
        modal: {
          isOpen: false,
          component: null,
          props: {},
          size: "md",
          closeOnOverlayClick: true,
        },
        commandPalette: {
          isOpen: false,
          query: "",
          results: [],
        },
        features: {
          enableAnimations: true,
          enableSounds: false,
          enableHaptics: true,
          enableAnalytics: true,
          enableBetaFeatures: false,
        },
      });
    });
  });

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());

      expect(result.current.unreadNotificationCount).toBe(0);
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("Theme Management", () => {
    it("sets theme correctly", () => {
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      act(() => {
        // @ts-expect-error Testing invalid theme
        result.current.setTheme("invalid-theme");
      });

      expect(consoleSpy).toHaveBeenCalled();
      expect(result.current.theme).toBe("system"); // Should remain unchanged

      consoleSpy.mockRestore();
    });

    it("computes isDarkMode correctly for system theme", () => {
      const { result } = renderHook(() => useUIStore());

      // Mock dark mode preference
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: query === "(prefers-color-scheme: dark)",
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      act(() => {
        result.current.setTheme("system");
      });

      expect(result.current.isDarkMode).toBe(true);
    });
  });

  describe("Sidebar Management", () => {
    it("toggles sidebar open/closed", () => {
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());

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

  describe("Navigation Management", () => {
    it("sets active route", () => {
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());

      const breadcrumbs = [
        { label: "Home", href: "/" },
        { label: "Dashboard", href: "/dashboard" },
        { label: "Profile" },
      ];

      act(() => {
        result.current.setBreadcrumbs(breadcrumbs);
      });

      expect(result.current.navigation.breadcrumbs).toEqual(breadcrumbs);
    });

    it("adds breadcrumb to existing list", () => {
      const { result } = renderHook(() => useUIStore());

      const initialBreadcrumbs = [
        { label: "Home", href: "/" },
        { label: "Dashboard", href: "/dashboard" },
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

  describe("Loading State Management", () => {
    it("sets loading state for a key", () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setLoadingState("user-profile", "loading");
      });

      expect(result.current.loadingStates["user-profile"]).toBe("loading");
      expect(result.current.isLoading).toBe(true);

      act(() => {
        result.current.setLoadingState("user-profile", "success");
      });

      expect(result.current.loadingStates["user-profile"]).toBe("success");
      expect(result.current.isLoading).toBe(false);
    });

    it("handles multiple loading states", () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setLoadingState("profile", "loading");
        result.current.setLoadingState("settings", "idle");
        result.current.setLoadingState("data", "loading");
      });

      expect(result.current.isLoading).toBe(true);
      expect(Object.keys(result.current.loadingStates)).toHaveLength(3);

      act(() => {
        result.current.setLoadingState("profile", "success");
        result.current.setLoadingState("data", "success");
      });

      expect(result.current.isLoading).toBe(false);
    });

    it("clears loading state for a key", () => {
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

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
      const { result } = renderHook(() => useUIStore());

      const notification = {
        type: "success" as const,
        title: "Success",
        message: "Operation completed successfully",
        isRead: false,
      };

      let notificationId: string;
      act(() => {
        notificationId = result.current.addNotification(notification);
      });

      expect(notificationId!).toBeDefined();
      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.notifications[0].title).toBe("Success");
      expect(result.current.notifications[0].type).toBe("success");
      expect(result.current.unreadNotificationCount).toBe(1);
    });

    it("adds notification with duration and auto-removes", async () => {
      const { result } = renderHook(() => useUIStore());

      const notification = {
        type: "info" as const,
        title: "Info",
        duration: 100,
        isRead: false,
      };

      act(() => {
        result.current.addNotification(notification);
      });

      expect(result.current.notifications).toHaveLength(1);

      // Since setTimeout is mocked to execute immediately, check if removal was scheduled
      await new Promise((resolve) => {
        setTimeout(() => {
          expect(result.current.notifications).toHaveLength(0);
          resolve(undefined);
        }, 0);
      });
    });

    it("removes notification by ID", () => {
      const { result } = renderHook(() => useUIStore());

      let notificationId: string;
      act(() => {
        notificationId = result.current.addNotification({
          type: "warning",
          title: "Warning",
          isRead: false,
        });
      });

      expect(result.current.notifications).toHaveLength(1);

      act(() => {
        result.current.removeNotification(notificationId!);
      });

      expect(result.current.notifications).toHaveLength(0);
    });

    it("marks notification as read", () => {
      const { result } = renderHook(() => useUIStore());

      let notificationId: string;
      act(() => {
        notificationId = result.current.addNotification({
          type: "error",
          title: "Error",
          isRead: false,
        });
      });

      expect(result.current.unreadNotificationCount).toBe(1);

      act(() => {
        result.current.markNotificationAsRead(notificationId!);
      });

      expect(result.current.unreadNotificationCount).toBe(0);
      expect(result.current.notifications[0].isRead).toBe(true);
    });

    it("clears all notifications", () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.addNotification({
          type: "info",
          title: "Info 1",
          isRead: false,
        });
        result.current.addNotification({
          type: "success",
          title: "Success 1",
          isRead: false,
        });
        result.current.addNotification({
          type: "warning",
          title: "Warning 1",
          isRead: false,
        });
      });

      expect(result.current.notifications).toHaveLength(3);

      act(() => {
        result.current.clearAllNotifications();
      });

      expect(result.current.notifications).toHaveLength(0);
    });

    it("limits notifications to maximum of 50", () => {
      const { result } = renderHook(() => useUIStore());

      // Add 55 notifications
      act(() => {
        for (let i = 0; i < 55; i++) {
          result.current.addNotification({
            type: "info",
            title: `Notification ${i}`,
            isRead: false,
          });
        }
      });

      // Should keep only the latest 50
      expect(result.current.notifications).toHaveLength(50);
      expect(result.current.notifications[0].title).toBe("Notification 54");
    });

    it("computes unread notification count correctly", () => {
      const { result } = renderHook(() => useUIStore());

      let id1: string;
      let id2: string;
      let id3: string;

      act(() => {
        id1 = result.current.addNotification({
          type: "info",
          title: "Info 1",
          isRead: false,
        });
        id2 = result.current.addNotification({
          type: "success",
          title: "Success 1",
          isRead: false,
        });
        id3 = result.current.addNotification({
          type: "warning",
          title: "Warning 1",
          isRead: false,
        });
      });

      expect(result.current.unreadNotificationCount).toBe(3);

      act(() => {
        result.current.markNotificationAsRead(id1!);
        result.current.markNotificationAsRead(id2!);
      });

      expect(result.current.unreadNotificationCount).toBe(1);

      act(() => {
        result.current.markNotificationAsRead(id3!);
      });

      expect(result.current.unreadNotificationCount).toBe(0);
    });

    it("handles invalid notification gracefully", () => {
      const { result } = renderHook(() => useUIStore());
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      act(() => {
        result.current.addNotification({
          // @ts-expect-error - intentionally testing invalid type
          type: "invalid-type",
          title: "Invalid",
          isRead: false,
        });
      });

      expect(consoleSpy).toHaveBeenCalled();
      expect(result.current.notifications).toHaveLength(0);

      consoleSpy.mockRestore();
    });
  });

  describe("Modal Management", () => {
    it("opens modal with component and props", () => {
      const { result } = renderHook(() => useUIStore());

      const modalProps = { userId: "123", mode: "edit" };

      act(() => {
        result.current.openModal("UserEditModal", modalProps, {
          size: "lg",
          closeOnOverlayClick: false,
        });
      });

      expect(result.current.modal.isOpen).toBe(true);
      expect(result.current.modal.component).toBe("UserEditModal");
      expect(result.current.modal.props).toEqual(modalProps);
      expect(result.current.modal.size).toBe("lg");
      expect(result.current.modal.closeOnOverlayClick).toBe(false);
    });

    it("opens modal with default options", () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.openModal("SimpleModal");
      });

      expect(result.current.modal.isOpen).toBe(true);
      expect(result.current.modal.component).toBe("SimpleModal");
      expect(result.current.modal.props).toEqual({});
      expect(result.current.modal.size).toBe("md");
      expect(result.current.modal.closeOnOverlayClick).toBe(true);
    });

    it("closes modal and resets state", () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.openModal("TestModal", { test: true });
      });

      expect(result.current.modal.isOpen).toBe(true);

      act(() => {
        result.current.closeModal();
      });

      expect(result.current.modal.isOpen).toBe(false);
      expect(result.current.modal.component).toBeNull();
      expect(result.current.modal.props).toEqual({});
    });

    it("updates modal props without closing", () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.openModal("TestModal", { initial: true });
      });

      act(() => {
        result.current.updateModalProps({ updated: true, additional: "data" });
      });

      expect(result.current.modal.isOpen).toBe(true);
      expect(result.current.modal.props).toEqual({
        initial: true,
        updated: true,
        additional: "data",
      });
    });
  });

  describe("Command Palette Management", () => {
    it("opens command palette", () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.openCommandPalette();
      });

      expect(result.current.commandPalette.isOpen).toBe(true);
    });

    it("closes command palette and resets state", () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.openCommandPalette();
        result.current.setCommandPaletteQuery("test query");
        result.current.setCommandPaletteResults([
          {
            id: "1",
            title: "Test Result",
            action: () => {},
          },
        ]);
      });

      expect(result.current.commandPalette.isOpen).toBe(true);
      expect(result.current.commandPalette.query).toBe("test query");
      expect(result.current.commandPalette.results).toHaveLength(1);

      act(() => {
        result.current.closeCommandPalette();
      });

      expect(result.current.commandPalette.isOpen).toBe(false);
      expect(result.current.commandPalette.query).toBe("");
      expect(result.current.commandPalette.results).toHaveLength(0);
    });

    it("sets command palette query", () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setCommandPaletteQuery("search term");
      });

      expect(result.current.commandPalette.query).toBe("search term");
    });

    it("sets command palette results", () => {
      const { result } = renderHook(() => useUIStore());

      const results = [
        {
          id: "1",
          title: "Result 1",
          description: "First result",
          action: () => {},
          category: "commands",
        },
        {
          id: "2",
          title: "Result 2",
          action: () => {},
        },
      ];

      act(() => {
        result.current.setCommandPaletteResults(results);
      });

      expect(result.current.commandPalette.results).toEqual(results);
    });
  });

  describe("Feature Flag Management", () => {
    it("toggles feature flags", () => {
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());

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
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.toggleFeature("enableAnimations");
        result.current.toggleFeature("enableSounds");
      });

      expect(result.current.features.enableAnimations).toBe(false);
      expect(result.current.features.enableSounds).toBe(true);
      expect(result.current.features.enableHaptics).toBe(true); // Should remain unchanged
    });
  });

  describe("Utility Actions", () => {
    it("resets UI state to defaults", () => {
      const { result } = renderHook(() => useUIStore());

      // Modify state
      act(() => {
        result.current.setSidebarOpen(false);
        result.current.setActiveRoute("/custom");
        result.current.addNotification({ type: "info", title: "Test", isRead: false });
        result.current.openModal("TestModal");
        result.current.openCommandPalette();
        result.current.setLoadingState("test", "loading");
      });

      // Verify state was modified
      expect(result.current.sidebar.isOpen).toBe(false);
      expect(result.current.navigation.activeRoute).toBe("/custom");
      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.modal.isOpen).toBe(true);
      expect(result.current.commandPalette.isOpen).toBe(true);
      expect(Object.keys(result.current.loadingStates)).toHaveLength(1);

      // Reset
      act(() => {
        result.current.reset();
      });

      // Verify reset
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
      const { result } = renderHook(() => useUIStore());

      // Set up navigation
      act(() => {
        result.current.setActiveRoute("/dashboard");
        result.current.setBreadcrumbs([
          { label: "Home", href: "/" },
          { label: "Dashboard" },
        ]);
      });

      // Configure sidebar
      act(() => {
        result.current.setSidebarCollapsed(true);
        result.current.setSidebarPinned(false);
      });

      // Set loading states
      act(() => {
        result.current.setLoadingState("data", "loading");
        result.current.setLoadingState("user", "success");
      });

      // Add notifications
      let infoId: string;
      let _warningId: string;
      act(() => {
        infoId = result.current.addNotification({
          type: "info",
          title: "Data Loading",
          isRead: false,
        });
        _warningId = result.current.addNotification({
          type: "warning",
          title: "Network Slow",
          isRead: false,
        });
      });

      // Open modal
      act(() => {
        result.current.openModal("DataModal", { dataId: "123" });
      });

      // Verify all state
      expect(result.current.navigation.activeRoute).toBe("/dashboard");
      expect(result.current.sidebar.isCollapsed).toBe(true);
      expect(result.current.isLoading).toBe(true);
      expect(result.current.notifications).toHaveLength(2);
      expect(result.current.modal.isOpen).toBe(true);
      expect(result.current.unreadNotificationCount).toBe(2);

      // Mark notification as read
      act(() => {
        result.current.markNotificationAsRead(infoId!);
      });

      expect(result.current.unreadNotificationCount).toBe(1);

      // Complete loading
      act(() => {
        result.current.setLoadingState("data", "success");
      });

      expect(result.current.isLoading).toBe(false);

      // Close modal
      act(() => {
        result.current.closeModal();
      });

      expect(result.current.modal.isOpen).toBe(false);
    });

    it("handles command palette workflow", () => {
      const { result } = renderHook(() => useUIStore());

      // Open command palette
      act(() => {
        result.current.openCommandPalette();
      });

      expect(result.current.commandPalette.isOpen).toBe(true);

      // Set query
      act(() => {
        result.current.setCommandPaletteQuery("user");
      });

      // Simulate search results
      const mockResults = [
        {
          id: "user-1",
          title: "Edit User Profile",
          description: "Modify user account settings",
          action: () => {},
          category: "user",
          icon: "user",
        },
        {
          id: "user-2",
          title: "User Management",
          description: "Manage all users",
          action: () => {},
          category: "admin",
          icon: "users",
        },
      ];

      act(() => {
        result.current.setCommandPaletteResults(mockResults);
      });

      expect(result.current.commandPalette.results).toHaveLength(2);
      expect(result.current.commandPalette.query).toBe("user");

      // Close command palette
      act(() => {
        result.current.closeCommandPalette();
      });

      expect(result.current.commandPalette.isOpen).toBe(false);
      expect(result.current.commandPalette.query).toBe("");
      expect(result.current.commandPalette.results).toHaveLength(0);
    });

    it("handles notification lifecycle with persistence", () => {
      const { result } = renderHook(() => useUIStore());

      // Add different types of notifications
      let successId: string;
      let errorId: string;
      let warningId: string;

      act(() => {
        successId = result.current.addNotification({
          type: "success",
          title: "Upload Complete",
          message: "File uploaded successfully",
          isRead: false,
        });

        errorId = result.current.addNotification({
          type: "error",
          title: "Upload Failed",
          message: "Network error occurred",
          isRead: false,
        });

        warningId = result.current.addNotification({
          type: "warning",
          title: "Storage Almost Full",
          message: "Consider upgrading your plan",
          isRead: false,
          action: {
            label: "Upgrade",
            onClick: () => {},
          },
        });
      });

      expect(result.current.notifications).toHaveLength(3);
      expect(result.current.unreadNotificationCount).toBe(3);

      // Mark some as read
      act(() => {
        result.current.markNotificationAsRead(successId!);
        result.current.markNotificationAsRead(errorId!);
      });

      expect(result.current.unreadNotificationCount).toBe(1);

      // Remove one notification
      act(() => {
        result.current.removeNotification(errorId!);
      });

      expect(result.current.notifications).toHaveLength(2);
      expect(result.current.unreadNotificationCount).toBe(1);

      // Verify remaining notifications
      const remainingNotifications = result.current.notifications;
      expect(remainingNotifications.some((n) => n.id === successId)).toBe(true);
      expect(remainingNotifications.some((n) => n.id === warningId)).toBe(true);
      expect(remainingNotifications.some((n) => n.id === errorId)).toBe(false);
    });

    it("handles theme switching with persistence", () => {
      const { result } = renderHook(() => useUIStore());

      // Test theme switching sequence
      const themes: Theme[] = ["light", "dark", "system"];

      themes.forEach((theme) => {
        act(() => {
          result.current.setTheme(theme);
        });

        expect(result.current.theme).toBe(theme);
      });

      // Test toggle behavior starting from each theme
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
      const { result } = renderHook(() => useUIStore());

      // Test individual selectors
      const { result: themeResult } = renderHook(() =>
        useUIStore((state) => state.theme)
      );
      const { result: sidebarResult } = renderHook(() =>
        useUIStore((state) => state.sidebar)
      );
      const { result: notificationsResult } = renderHook(() =>
        useUIStore((state) => state.notifications)
      );

      expect(themeResult.current).toBe("system");
      expect(sidebarResult.current.isOpen).toBe(true);
      expect(notificationsResult.current).toEqual([]);

      // Modify state and test again
      act(() => {
        result.current.setTheme("dark");
        result.current.setSidebarOpen(false);
        result.current.addNotification({ type: "info", title: "Test", isRead: false });
      });

      expect(themeResult.current).toBe("dark");
      expect(sidebarResult.current.isOpen).toBe(false);
      expect(notificationsResult.current).toHaveLength(1);
    });
  });
});
