/**
 * @fileoverview UI state management store using Zustand with TypeScript validation.
 */

"use client";

import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { withComputed } from "@/stores/middleware/computed";
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

const logger = createStoreLogger({ storeName: "ui" });

let prefersDarkMediaQuery: MediaQueryList | null | undefined;
let cachedMatchMediaFn: ((query: string) => MediaQueryList) | undefined;

const getPrefersDarkMediaQuery = (): MediaQueryList | null => {
  if (typeof window === "undefined") {
    prefersDarkMediaQuery = null;
    cachedMatchMediaFn = undefined;
    return prefersDarkMediaQuery;
  }

  if (typeof window.matchMedia !== "function") {
    prefersDarkMediaQuery = null;
    cachedMatchMediaFn = undefined;
    return prefersDarkMediaQuery;
  }

  // Recreate the cached MediaQueryList when the host function changes (e.g., test mocks).
  if (prefersDarkMediaQuery !== undefined && cachedMatchMediaFn === window.matchMedia) {
    return prefersDarkMediaQuery;
  }

  try {
    prefersDarkMediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    cachedMatchMediaFn = window.matchMedia;
  } catch (error) {
    logger.warn("Failed to create prefers-color-scheme MediaQueryList", { error });
    prefersDarkMediaQuery = null;
    cachedMatchMediaFn = undefined;
  }

  return prefersDarkMediaQuery;
};

/** Compute derived UI properties. */
const computeUiState = (state: UiState): Partial<UiState> => {
  // Compute isDarkMode
  let isDarkMode = false;
  if (state.theme === "system") {
    const mediaQuery = getPrefersDarkMediaQuery();
    isDarkMode = mediaQuery?.matches ?? false;
  } else {
    isDarkMode = state.theme === "dark";
  }

  // Compute isLoading
  const isLoading = Object.values(state.loadingStates).some(
    (loadingState) => loadingState === "loading"
  );

  // Compute unreadNotificationCount
  const unreadNotificationCount = state.notifications.filter((n) => !n.isRead).length;

  return { isDarkMode, isLoading, unreadNotificationCount };
};

export const useUiStore = create<UiState>()(
  devtools(
    persist(
      withComputed({ compute: computeUiState }, (...args) => {
        const [set] = args;

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

          // Computed properties - initial values (updated via withComputed)
          isDarkMode: false,
          isLoading: false,

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
          unreadNotificationCount: 0,
        };
      }),
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
