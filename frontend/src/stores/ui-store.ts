import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// Validation schemas for UI state
const THEME_SCHEMA = z.enum(["light", "dark", "system"]);
const NOTIFICATION_TYPE_SCHEMA = z.enum(["info", "success", "warning", "error"]);
const LOADING_STATE_SCHEMA = z.enum(["idle", "loading", "success", "error"]);

export const NotificationSchema = z.object({
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

export const LoadingStatesSchema = z.record(z.string(), LOADING_STATE_SCHEMA);

// Types derived from schemas
export type Theme = z.infer<typeof THEME_SCHEMA>;
export type NotificationType = z.infer<typeof NOTIFICATION_TYPE_SCHEMA>;
export type LoadingState = z.infer<typeof LOADING_STATE_SCHEMA>;
export type Notification = z.infer<typeof NotificationSchema>;
export type LoadingStates = z.infer<typeof LoadingStatesSchema>;

// Sidebar and navigation state
export interface SidebarState {
  isOpen: boolean;
  isCollapsed: boolean;
  isPinned: boolean;
}

export interface NavigationState {
  activeRoute: string;
  breadcrumbs: Array<{
    label: string;
    href?: string;
  }>;
}

// Modal and dialog state
export interface ModalState {
  isOpen: boolean;
  component: string | null;
  props?: Record<string, unknown>;
  size?: "sm" | "md" | "lg" | "xl" | "full";
  closeOnOverlayClick?: boolean;
}

// Command palette state
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

// Complete UI store interface
interface UiState {
  // Theme and appearance
  theme: Theme;
  isDarkMode: boolean;

  // Layout state
  sidebar: SidebarState;
  navigation: NavigationState;

  // Loading states for different operations
  loadingStates: LoadingStates;

  // Notifications system
  notifications: Notification[];

  // Modals and dialogs
  modal: ModalState;

  // Command palette
  commandPalette: CommandPaletteState;

  // Feature flags and capabilities
  features: {
    enableAnimations: boolean;
    enableSounds: boolean;
    enableHaptics: boolean;
    enableAnalytics: boolean;
    enableBetaFeatures: boolean;
  };

  // Computed properties
  unreadNotificationCount: number;
  isLoading: boolean;

  // Theme actions
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;

  // Sidebar actions
  toggleSidebar: () => void;
  setSidebarOpen: (isOpen: boolean) => void;
  setSidebarCollapsed: (isCollapsed: boolean) => void;
  setSidebarPinned: (isPinned: boolean) => void;

  // Navigation actions
  setActiveRoute: (route: string) => void;
  setBreadcrumbs: (breadcrumbs: NavigationState["breadcrumbs"]) => void;
  addBreadcrumb: (breadcrumb: NavigationState["breadcrumbs"][0]) => void;

  // Loading state actions
  setLoadingState: (key: string, state: LoadingState) => void;
  clearLoadingState: (key: string) => void;
  clearAllLoadingStates: () => void;

  // Notification actions
  addNotification: (notification: Omit<Notification, "id" | "createdAt">) => string;
  removeNotification: (id: string) => void;
  markNotificationAsRead: (id: string) => void;
  clearAllNotifications: () => void;

  // Modal actions
  openModal: (
    component: string,
    props?: Record<string, unknown>,
    options?: Partial<ModalState>
  ) => void;
  closeModal: () => void;
  updateModalProps: (props: Record<string, unknown>) => void;

  // Command palette actions
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  setCommandPaletteQuery: (query: string) => void;
  setCommandPaletteResults: (results: CommandPaletteState["results"]) => void;

  // Feature flag actions
  toggleFeature: (feature: keyof UiState["features"]) => void;
  setFeature: (feature: keyof UiState["features"], enabled: boolean) => void;

  // Utility actions
  reset: () => void;
}

// Helper functions
const GENERATE_ID = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const GET_CURRENT_TIMESTAMP = () => new Date().toISOString();

// Default states
const DEFAULT_SIDEBAR_STATE: SidebarState = {
  isCollapsed: false,
  isOpen: true,
  isPinned: true,
};

const DEFAULT_NAVIGATION_STATE: NavigationState = {
  activeRoute: "/",
  breadcrumbs: [],
};

const DEFAULT_MODAL_STATE: ModalState = {
  closeOnOverlayClick: true,
  component: null,
  isOpen: false,
  props: {},
  size: "md",
};

const DEFAULT_COMMAND_PALETTE_STATE: CommandPaletteState = {
  isOpen: false,
  query: "",
  results: [],
};

export const useUIStore = create<UiState>()(
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
          const result = NotificationSchema.safeParse({
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
export const useTheme = () => useUIStore((state) => state.theme);
export const useIsDarkMode = () => useUIStore((state) => state.isDarkMode);
export const useSidebar = () => useUIStore((state) => state.sidebar);
export const useNavigation = () => useUIStore((state) => state.navigation);
export const useNotifications = () => useUIStore((state) => state.notifications);
export const useUnreadNotificationCount = () =>
  useUIStore((state) => state.unreadNotificationCount);
export const useModal = () => useUIStore((state) => state.modal);
export const useCommandPalette = () => useUIStore((state) => state.commandPalette);
export const useLoadingStates = () => useUIStore((state) => state.loadingStates);
export const useIsLoading = () => useUIStore((state) => state.isLoading);
export const useFeatures = () => useUIStore((state) => state.features);
