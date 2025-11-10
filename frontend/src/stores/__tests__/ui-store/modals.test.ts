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
import { resetUiStore } from "./_shared";

describe("UI Store - Modals", () => {
  beforeEach(() => {
    resetUiStore();
  });

  describe("Modal Management", () => {
    it("opens modal with component and props", () => {
      const { result } = renderHook(() => useUiStore());

      const modalProps = { mode: "edit", userId: "123" };

      act(() => {
        result.current.openModal("UserEditModal", modalProps, {
          closeOnOverlayClick: false,
          size: "lg",
        });
      });

      expect(result.current.modal.isOpen).toBe(true);
      expect(result.current.modal.component).toBe("UserEditModal");
      expect(result.current.modal.props).toEqual(modalProps);
      expect(result.current.modal.size).toBe("lg");
      expect(result.current.modal.closeOnOverlayClick).toBe(false);
    });

    it("opens modal with default options", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.openModal("BasicModal");
      });

      expect(result.current.modal.isOpen).toBe(true);
      expect(result.current.modal.component).toBe("BasicModal");
      expect(result.current.modal.props).toEqual({});
      expect(result.current.modal.size).toBe("md");
      expect(result.current.modal.closeOnOverlayClick).toBe(true);
    });

    it("closes modal and resets state", () => {
      const { result } = renderHook(() => useUiStore());

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
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.openModal("TestModal", { initial: true });
      });

      act(() => {
        result.current.updateModalProps({ additional: "data", updated: true });
      });

      expect(result.current.modal.isOpen).toBe(true);
      expect(result.current.modal.props).toEqual({
        additional: "data",
        initial: true,
        updated: true,
      });
    });
  });

  describe("Command Palette Management", () => {
    it("opens command palette", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.openCommandPalette();
      });

      expect(result.current.commandPalette.isOpen).toBe(true);
    });

    it("closes command palette and resets state", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.openCommandPalette();
        result.current.setCommandPaletteQuery("test query");
        result.current.setCommandPaletteResults([
          {
            action: () => {
              /* empty callback for test */
            },
            id: "1",
            title: "Test Result",
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
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.setCommandPaletteQuery("search term");
      });

      expect(result.current.commandPalette.query).toBe("search term");
    });

    it("sets command palette results", () => {
      const { result } = renderHook(() => useUiStore());

      const results = [
        {
          action: () => {
            /* empty callback for test */
          },
          category: "commands",
          description: "First result",
          id: "1",
          title: "Result 1",
        },
        {
          action: () => {
            /* empty callback for test */
          },
          id: "2",
          title: "Result 2",
        },
      ];

      act(() => {
        result.current.setCommandPaletteResults(results);
      });

      expect(result.current.commandPalette.results).toEqual(results);
    });
  });

  describe("Complex Scenarios", () => {
    it("handles command palette workflow", () => {
      const { result } = renderHook(() => useUiStore());

      act(() => {
        result.current.openCommandPalette();
      });

      expect(result.current.commandPalette.isOpen).toBe(true);

      act(() => {
        result.current.setCommandPaletteQuery("user");
      });

      const mockResults = [
        {
          action: () => {
            /* empty callback for test */
          },
          category: "user",
          description: "Modify user account settings",
          icon: "user",
          id: "user-1",
          title: "Edit User Profile",
        },
        {
          action: () => {
            /* empty callback for test */
          },
          category: "admin",
          description: "Manage all users",
          icon: "users",
          id: "user-2",
          title: "User Management",
        },
      ];

      act(() => {
        result.current.setCommandPaletteResults(mockResults);
      });

      expect(result.current.commandPalette.results).toHaveLength(2);
      expect(result.current.commandPalette.query).toBe("user");

      act(() => {
        result.current.closeCommandPalette();
      });

      expect(result.current.commandPalette.isOpen).toBe(false);
      expect(result.current.commandPalette.query).toBe("");
      expect(result.current.commandPalette.results).toHaveLength(0);
    });
  });
});
