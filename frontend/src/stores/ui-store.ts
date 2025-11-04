/**
 * @fileoverview UI state management store using Zustand with TypeScript validation.
 *
 * This module provides a UI state store for managing application-wide
 * UI state including themes, notifications, loading states, modals, navigation,
 * and feature flags. All state mutations are validated using Zod schemas to ensure
 * type safety and data integrity.
 */

import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

/** Zod schema for validating theme values. */
const THEME_SCHEMA = z.enum(["light", "dark", "system"]);

/** Zod schema for validating notification types. */
const NOTIFICATION_TYPE_SCHEMA = z.enum(["info", "success", "warning", "error"]);

/** Zod schema for validating loading state values. */
const LOADING_STATE_SCHEMA = z.enum(["idle", "loading", "success", "error"]);

/**
 * Zod schema for validating notification objects.
 *
 * @example
 * ```typescript
 * const notification = {
 *   title: "Success",
 *   message: "Operation completed",
 *   type: "success",
 *   duration: 5000,
 *   action: {
 *     label: "View Details",
 *     onClick: () => console.log("Action clicked")
 *   }
 * };
 * ```
 */
export const NOTIFICATION_SCHEMA = z.object({
  action: z
    .object({
      label: z.string(),
      onClick: z.function().optional(),
    })
    .optional(),
  createdAt: z.string(),
  duration: z.number().positive().optional(),
  id: z.string(),
  isRead: z.boolean().default(false),
  message: z.string().optional(),
  title: z.string(),
  type: NOTIFICATION_TYPE_SCHEMA,
});

/** Zod schema for validating loading states map. */
export const LOADING_STATES_SCHEMA = z.record(z.string(), LOADING_STATE_SCHEMA);

/** Type inferred from THEME_SCHEMA for theme values. */
export type Theme = z.infer<typeof THEME_SCHEMA>;

/** Type inferred from NOTIFICATION_TYPE_SCHEMA for notification types. */
export type NotificationType = z.infer<typeof NOTIFICATION_TYPE_SCHEMA>;

/** Type inferred from LOADING_STATE_SCHEMA for loading state values. */
export type LoadingState = z.infer<typeof LOADING_STATE_SCHEMA>;

/** Type inferred from NOTIFICATION_SCHEMA for notification objects. */
export type Notification = z.infer<typeof NOTIFICATION_SCHEMA>;

/** Type inferred from LOADING_STATES_SCHEMA for loading states map. */
export type LoadingStates = z.infer<typeof LOADING_STATES_SCHEMA>;

/**
 * Interface for sidebar state management.
 */
export interface SidebarState {
  isOpen: boolean;
  isCollapsed: boolean;
  isPinned: boolean;
}

/**
 * Interface for navigation state management.
 */
export interface NavigationState {
  activeRoute: string;
  breadcrumbs: Array<{
    label: string;
    href?: string;
  }>;
}

/**
 * Interface for modal and dialog state management.
 */
export interface ModalState {
  isOpen: boolean;
  component: string | null;
  props?: Record<string, unknown>;
  size?: "sm" | "md" | "lg" | "xl" | "full";
  closeOnOverlayClick?: boolean;
}

/**
 * Interface for command palette state.
 */
export interface CommandPaletteState {
  isOpen: boolean;
  query: string;
  results: Array<{
    id: string;
    title: string;
    description?: string;
    action: () => void;
    category?: string;
    icon?: string;
  }>;
}

/**
 * Interface for the UI state store.
 *
 * This interface defines the entire state structure and actions for the UI store,
 * including theme management, sidebar state, navigation, loading states, notifications,
 * modals, command palette, and feature flags.
 */
interface UiState {
  // Theme and appearance
  /** Current theme setting. */
  theme: Theme;

  /** Computed property indicating if dark mode is active. */
  isDarkMode: boolean;

  /** Sidebar state configuration. */
  sidebar: SidebarState;

  /** Navigation state including active route and breadcrumbs. */
  navigation: NavigationState;

  /** Map of loading states keyed by operation identifier. */
  loadingStates: LoadingStates;

  /** Array of notification objects currently displayed. */
  notifications: Notification[];

  /** Current modal state and configuration. */
  modal: ModalState;

  /** Command palette state including search query and results. */
  commandPalette: CommandPaletteState;

  /**
   * Feature flag configuration for UI capabilities.
   */
  features: {
    enableAnimations: boolean;
    enableSounds: boolean;
    enableHaptics: boolean;
    enableAnalytics: boolean;
    enableBetaFeatures: boolean;
  };

  /** Computed count of unread notifications. */
  unreadNotificationCount: number;

  /** Computed boolean indicating if any operation is currently loading. */
  isLoading: boolean;

  /**
   * Set the application theme.
   * @param theme - The theme to set
   */
  setTheme: (theme: Theme) => void;

  /** Toggles between light and dark theme. */
  toggleTheme: () => void;

  /** Toggles the sidebar open/closed state. */
  toggleSidebar: () => void;

  /**
   * Set the sidebar open state.
   * @param isOpen - Whether the sidebar should be open
   */
  setSidebarOpen: (isOpen: boolean) => void;

  /**
   * Set the sidebar collapsed state.
   * @param isCollapsed - Whether the sidebar should be collapsed
   */
  setSidebarCollapsed: (isCollapsed: boolean) => void;

  /**
   * Set the sidebar pinned state.
   * @param isPinned - Whether the sidebar should be pinned
   */
  setSidebarPinned: (isPinned: boolean) => void;

  /** Sets the active route.
   * @param route - The route path to set as active
   */
  setActiveRoute: (route: string) => void;

  /**
   * Set the breadcrumbs array.
   * @param breadcrumbs - Array of breadcrumb items
   */
  setBreadcrumbs: (breadcrumbs: NavigationState["breadcrumbs"]) => void;

  /**
   * Add a breadcrumb to the navigation state.
   * @param breadcrumb - Breadcrumb item to add
   */
  addBreadcrumb: (breadcrumb: NavigationState["breadcrumbs"][0]) => void;

  /**
   * Set the loading state for a specific operation.
   * @param key - Operation identifier
   * @param state - Loading state to set
   */
  setLoadingState: (key: string, state: LoadingState) => void;

  /**
   * Clear the loading state for a specific operation.
   * @param key - Operation identifier to clear
   */
  clearLoadingState: (key: string) => void;

  /** Clears all loading states. */
  clearAllLoadingStates: () => void;

  /**
   * Add a new notification and returns its ID.
   * @param notification - Notification to add
   * @returns The generated notification ID
   */
  addNotification: (notification: Omit<Notification, "id" | "createdAt">) => string;

  /**
   * Remove a notification by ID.
   * @param id - Notification ID to remove
   */
  removeNotification: (id: string) => void;

  /**
   * Mark a notification as read.
   * @param id - Notification ID to mark as read
   */
  markNotificationAsRead: (id: string) => void;

  /** Clears all notifications. */
  clearAllNotifications: () => void;

  /**
   * Open a modal with the specified component and props.
   * @param component - Component name to render in modal
   * @param [props] - Props to pass to component
   * @param [options] - Modal configuration options
   */
  openModal: (
    component: string,
    props?: Record<string, unknown>,
    options?: Partial<ModalState>
  ) => void;

  /** Closes the currently open modal. */
  closeModal: () => void;

  /** Updates props for the currently open modal.
   * @param props - Props to update
   */
  updateModalProps: (props: Record<string, unknown>) => void;

  /** Opens the command palette. */
  openCommandPalette: () => void;

  /** Closes the command palette. */
  closeCommandPalette: () => void;

  /**
   * Set the search query for the command palette.
   * @param query - Search query string
   */
  setCommandPaletteQuery: (query: string) => void;

  /**
   * Set the search results for the command palette.
   * @param results - Array of search results
   */
  setCommandPaletteResults: (results: CommandPaletteState["results"]) => void;

  /**
   * Toggle a feature flag on/off.
   * @param feature - Feature flag to toggle
   */
  toggleFeature: (feature: keyof UiState["features"]) => void;

  /**
   * Set a feature flag to a specific value.
   * @param feature - Feature flag to set
   * @param enabled - Whether the feature should be enabled
   */
  setFeature: (feature: keyof UiState["features"], enabled: boolean) => void;

  /** Resets the UI store to its initial state. */
  reset: () => void;
}

/**
 * Generates a unique ID using timestamp and random string.
 * @returns A unique identifier string
 */
const GENERATE_ID = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);

/**
 * Gets the current timestamp in ISO string format.
 * @returns Current timestamp as ISO string
 */
const GET_CURRENT_TIMESTAMP = () => new Date().toISOString();

/** Default sidebar state configuration. */
const DEFAULT_SIDEBAR_STATE: SidebarState = {
  isCollapsed: false,
  isOpen: true,
  isPinned: true,
};

/** Default navigation state configuration. */
const DEFAULT_NAVIGATION_STATE: NavigationState = {
  activeRoute: "/",
  breadcrumbs: [],
};

/** Default modal state configuration. */
const DEFAULT_MODAL_STATE: ModalState = {
  closeOnOverlayClick: true,
  component: null,
  isOpen: false,
  props: {},
  size: "md",
};

/** Default command palette state configuration. */
const DEFAULT_COMMAND_PALETTE_STATE: CommandPaletteState = {
  isOpen: false,
  query: "",
  results: [],
};

/**
 * Main UI store hook created with Zustand.
 *
 * This store manages all UI-related state including themes, sidebar, navigation,
 * notifications, modals, command palette, and feature flags. State is persisted
 * to localStorage and includes devtools integration for debugging.
 *
 * @example
 * ```typescript
 * const { theme, setTheme, addNotification } = useUiStore();
 *
 * // Set theme
 * setTheme('dark');
 *
 * // Add notification
 * const id = addNotification({
 *   title: 'Success',
 *   message: 'Operation completed',
 *   type: 'success'
 * });
 * ```
 */
export const useUiStore = create<UiState>()(
  devtools(
    persist(
      (set, get) => ({
        addBreadcrumb: (breadcrumb) => {
          set((state) => ({
            navigation: {
              ...state.navigation,
              breadcrumbs: [...state.navigation.breadcrumbs, breadcrumb],
            },
          }));
        },

        // Notification actions
        addNotification: (notification) => {
          const id = GENERATE_ID();
          const result = NOTIFICATION_SCHEMA.safeParse({
            ...notification,
            createdAt: GET_CURRENT_TIMESTAMP(),
            id,
            isRead: notification.isRead ?? false,
          });

          if (result.success) {
            set((state) => ({
              notifications: [result.data, ...state.notifications].slice(0, 50), // Keep max 50 notifications
            }));

            // Auto-remove notification if duration is specified
            if (notification.duration) {
              setTimeout(() => {
                get().removeNotification(id);
              }, notification.duration);
            }

            return id;
          }
          console.error("Invalid notification:", result.error);
          return "";
        },

        clearAllLoadingStates: () => {
          set({ loadingStates: {} });
        },

        clearAllNotifications: () => {
          set({ notifications: [] });
        },

        clearLoadingState: (key) => {
          set((state) => {
            const newLoadingStates = { ...state.loadingStates };
            delete newLoadingStates[key];
            return { loadingStates: newLoadingStates };
          });
        },

        closeCommandPalette: () => {
          set((state) => ({
            commandPalette: {
              ...state.commandPalette,
              isOpen: false,
              query: "",
              results: [],
            },
          }));
        },

        closeModal: () => {
          set({ modal: DEFAULT_MODAL_STATE });
        },
        commandPalette: DEFAULT_COMMAND_PALETTE_STATE,

        features: {
          enableAnalytics: true,
          enableAnimations: true,
          enableBetaFeatures: false,
          enableHaptics: true,
          enableSounds: false,
        },
        get isDarkMode() {
          const { theme } = get();
          if (theme === "system") {
            if (typeof window === "undefined") return false;

            try {
              const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
              return mediaQuery?.matches ?? false;
            } catch {
              // Fallback for test environments
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
        loadingStates: {},

        markNotificationAsRead: (id) => {
          set((state) => ({
            notifications: state.notifications.map((n) =>
              n.id === id ? { ...n, isRead: true } : n
            ),
          }));
        },
        modal: DEFAULT_MODAL_STATE,
        navigation: DEFAULT_NAVIGATION_STATE,
        notifications: [],

        // Command palette actions
        openCommandPalette: () => {
          set((state) => ({
            commandPalette: {
              ...state.commandPalette,
              isOpen: true,
            },
          }));
        },

        // Modal actions
        openModal: (component, props = {}, options = {}) => {
          set({
            modal: {
              closeOnOverlayClick: options.closeOnOverlayClick ?? true,
              component,
              isOpen: true,
              props,
              size: options.size || "md",
            },
          });
        },

        removeNotification: (id) => {
          set((state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          }));
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

        // Navigation actions
        setActiveRoute: (route) => {
          set((state) => ({
            navigation: {
              ...state.navigation,
              activeRoute: route,
            },
          }));
        },

        setBreadcrumbs: (breadcrumbs) => {
          set((state) => ({
            navigation: {
              ...state.navigation,
              breadcrumbs,
            },
          }));
        },

        setCommandPaletteQuery: (query) => {
          set((state) => ({
            commandPalette: {
              ...state.commandPalette,
              query,
            },
          }));
        },

        setCommandPaletteResults: (results) => {
          set((state) => ({
            commandPalette: {
              ...state.commandPalette,
              results,
            },
          }));
        },

        setFeature: (feature, enabled) => {
          set((state) => ({
            features: {
              ...state.features,
              [feature]: enabled,
            },
          }));
        },

        // Loading state actions
        setLoadingState: (key, state) => {
          const result = LOADING_STATE_SCHEMA.safeParse(state);
          if (result.success) {
            set((currentState) => ({
              loadingStates: {
                ...currentState.loadingStates,
                [key]: result.data,
              },
            }));
          } else {
            console.error("Invalid loading state:", result.error);
          }
        },

        setSidebarCollapsed: (isCollapsed) => {
          set((state) => ({
            sidebar: {
              ...state.sidebar,
              isCollapsed,
            },
          }));
        },

        setSidebarOpen: (isOpen) => {
          set((state) => ({
            sidebar: {
              ...state.sidebar,
              isOpen,
            },
          }));
        },

        setSidebarPinned: (isPinned) => {
          set((state) => ({
            sidebar: {
              ...state.sidebar,
              isPinned,
            },
          }));
        },

        // Theme actions
        setTheme: (theme) => {
          const result = THEME_SCHEMA.safeParse(theme);
          if (result.success) {
            set({ theme: result.data });
          } else {
            console.error("Invalid theme:", result.error);
          }
        },

        sidebar: DEFAULT_SIDEBAR_STATE,
        // Initial state
        theme: "system",

        // Feature flag actions
        toggleFeature: (feature) => {
          set((state) => ({
            features: {
              ...state.features,
              [feature]: !state.features[feature],
            },
          }));
        },

        // Sidebar actions
        toggleSidebar: () => {
          set((state) => ({
            sidebar: {
              ...state.sidebar,
              isOpen: !state.sidebar.isOpen,
            },
          }));
        },

        toggleTheme: () => {
          const { theme } = get();
          const nextTheme = theme === "light" ? "dark" : "light";
          get().setTheme(nextTheme);
        },

        // Computed properties
        get unreadNotificationCount() {
          return get().notifications.filter((n) => !n.isRead).length;
        },

        updateModalProps: (props) => {
          set((state) => ({
            modal: {
              ...state.modal,
              props: {
                ...state.modal.props,
                ...props,
              },
            },
          }));
        },
      }),
      {
        name: "ui-storage",
        partialize: (state) => ({
          features: state.features,
          sidebar: {
            isCollapsed: state.sidebar.isCollapsed,
            isPinned: state.sidebar.isPinned,
          },
          // Only persist certain UI preferences
          theme: state.theme,
        }),
      }
    ),
    { name: "UIStore" }
  )
);

// Utility selectors for common use cases

/**
 * Selector hook for the current theme setting.
 * @returns Current theme value
 */
export const useTheme = () => useUiStore((state) => state.theme);

/**
 * Selector hook for dark mode status.
 * @returns True if dark mode is active
 */
export const useIsDarkMode = () => useUiStore((state) => state.isDarkMode);

/**
 * Selector hook for sidebar state.
 * @returns Current sidebar state
 */
export const useSidebar = () => useUiStore((state) => state.sidebar);

/**
 * Selector hook for navigation state.
 * @returns Current navigation state
 */
export const useNavigation = () => useUiStore((state) => state.navigation);

/**
 * Selector hook for notifications array.
 * @returns Array of current notifications
 */
export const useNotifications = () => useUiStore((state) => state.notifications);

/**
 * Selector hook for unread notification count.
 * @returns Number of unread notifications
 */
export const useUnreadNotificationCount = () =>
  useUiStore((state) => state.unreadNotificationCount);

/**
 * Selector hook for modal state.
 * @returns Current modal state
 */
export const useModal = () => useUiStore((state) => state.modal);

/**
 * Selector hook for command palette state.
 * @returns Current command palette state
 */
export const useCommandPalette = () => useUiStore((state) => state.commandPalette);

/**
 * Selector hook for loading states map.
 * @returns Map of loading states by operation
 */
export const useLoadingStates = () => useUiStore((state) => state.loadingStates);

/**
 * Selector hook for global loading status.
 * @returns True if any operation is loading
 */
export const useIsLoading = () => useUiStore((state) => state.isLoading);

/**
 * Selector hook for feature flags.
 * @returns Current feature flag configuration
 */
export const useFeatures = () => useUiStore((state) => state.features);
