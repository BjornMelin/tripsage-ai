/**
 * @fileoverview UI state management store using Zustand with TypeScript validation.
 *
 * This module composes multiple slices for better maintainability and tree-shaking.
 */

import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import {
  createCommandPaletteSlice,
  DEFAULT_COMMAND_PALETTE_STATE,
} from "./command-palette";
import { createFeaturesSlice } from "./features";
import { createLoadingSlice } from "./loading";
import { createModalSlice, DEFAULT_MODAL_STATE } from "./modal";
import { createNavigationSlice, DEFAULT_NAVIGATION_STATE } from "./navigation";
import { createNotificationsSlice } from "./notifications";
import { createSidebarSlice, DEFAULT_SIDEBAR_STATE } from "./sidebar";
import { createThemeSlice } from "./theme";
import type { UiState } from "./types";

export const useUiStore = create<UiState>()(
  devtools(
    persist(
      (...args) => {
        const [set, get] = args;

        // Compose all slices
        const themeSlice = createThemeSlice(...args);
        const sidebarSlice = createSidebarSlice(...args);
        const navigationSlice = createNavigationSlice(...args);
        const loadingSlice = createLoadingSlice(...args);
        const notificationsSlice = createNotificationsSlice(...args);
        const modalSlice = createModalSlice(...args);
        const commandPaletteSlice = createCommandPaletteSlice(...args);
        const featuresSlice = createFeaturesSlice(...args);

        return {
          // Spread all slices
          ...themeSlice,
          ...sidebarSlice,
          ...navigationSlice,
          ...loadingSlice,
          ...notificationsSlice,
          ...modalSlice,
          ...commandPaletteSlice,
          ...featuresSlice,

          // Computed properties (getters) - defined at the top level where get() is available
          get isDarkMode() {
            const { theme } = get();
            if (theme === "system") {
              if (typeof window === "undefined") return false;
              try {
                const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
                return mediaQuery?.matches ?? false;
              } catch {
                return false;
              }
            }
            return theme === "dark";
          },

          get isLoading() {
            return Object.values(get().loadingStates).some(
              (state) => state === "loading"
            );
          },

          // Utility actions
          reset: () => {
            set({
              commandPalette: DEFAULT_COMMAND_PALETTE_STATE,
              loadingStates: {},
              modal: DEFAULT_MODAL_STATE,
              navigation: DEFAULT_NAVIGATION_STATE,
              notifications: [],
              sidebar: DEFAULT_SIDEBAR_STATE,
            });
          },

          get unreadNotificationCount() {
            return get().notifications.filter((n) => !n.isRead).length;
          },
        };
      },
      {
        name: "ui-storage",
        partialize: (state) => ({
          features: state.features,
          sidebar: {
            isCollapsed: state.sidebar.isCollapsed,
            isPinned: state.sidebar.isPinned,
          },
          theme: state.theme,
        }),
      }
    ),
    { name: "UIStore" }
  )
);
