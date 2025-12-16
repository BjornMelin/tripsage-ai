/**
 * @fileoverview Selector hooks for UI store.
 */

import { useUiStore } from "./index";

// ===== THEME SELECTORS =====

/** Selector hook for the current theme setting. */
export const useTheme = () => useUiStore((state) => state.theme);

/** Selector hook for dark mode status. */
export const useIsDarkMode = () => useUiStore((state) => state.isDarkMode);

// ===== SIDEBAR SELECTORS =====

/** Selector hook for sidebar state. */
export const useSidebar = () => useUiStore((state) => state.sidebar);

// ===== NAVIGATION SELECTORS =====

/** Selector hook for navigation state. */
export const useNavigation = () => useUiStore((state) => state.navigation);

// ===== NOTIFICATIONS SELECTORS =====

/** Selector hook for notifications array. */
export const useNotifications = () => useUiStore((state) => state.notifications);

/** Selector hook for unread notification count. */
export const useUnreadNotificationCount = () =>
  useUiStore((state) => state.unreadNotificationCount);

// ===== MODAL SELECTORS =====

/** Selector hook for modal state. */
export const useModal = () => useUiStore((state) => state.modal);

// ===== COMMAND PALETTE SELECTORS =====

/** Selector hook for command palette state. */
export const useCommandPalette = () => useUiStore((state) => state.commandPalette);

// ===== LOADING SELECTORS =====

/** Selector hook for loading states map. */
export const useLoadingStates = () => useUiStore((state) => state.loadingStates);

/** Selector hook for global loading status. */
export const useIsLoading = () => useUiStore((state) => state.isLoading);

// ===== FEATURES SELECTORS =====

/** Selector hook for feature flags. */
export const useFeatures = () => useUiStore((state) => state.features);
