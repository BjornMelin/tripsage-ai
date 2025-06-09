import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// Validation schemas for UI state
const ThemeSchema = z.enum(["light", "dark", "system"]);
const NotificationTypeSchema = z.enum(["info", "success", "warning", "error"]);
const LoadingStateSchema = z.enum(["idle", "loading", "success", "error"]);

export const NotificationSchema = z.object({
  id: z.string(),
  type: NotificationTypeSchema,
  title: z.string(),
  message: z.string().optional(),
  duration: z.number().positive().optional(),
  action: z
    .object({
      label: z.string(),
      onClick: z.function().optional(),
    })
    .optional(),
  isRead: z.boolean().default(false),
  createdAt: z.string(),
});

export const LoadingStatesSchema = z.record(z.string(), LoadingStateSchema);

// Types derived from schemas
export type Theme = z.infer<typeof ThemeSchema>;
export type NotificationType = z.infer<typeof NotificationTypeSchema>;
export type LoadingState = z.infer<typeof LoadingStateSchema>;
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
interface UIState {
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
  toggleFeature: (feature: keyof UIState["features"]) => void;
  setFeature: (feature: keyof UIState["features"], enabled: boolean) => void;

  // Utility actions
  reset: () => void;
}

// Helper functions
const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

// Default states
const defaultSidebarState: SidebarState = {
  isOpen: true,
  isCollapsed: false,
  isPinned: true,
};

const defaultNavigationState: NavigationState = {
  activeRoute: "/",
  breadcrumbs: [],
};

const defaultModalState: ModalState = {
  isOpen: false,
  component: null,
  props: {},
  size: "md",
  closeOnOverlayClick: true,
};

const defaultCommandPaletteState: CommandPaletteState = {
  isOpen: false,
  query: "",
  results: [],
};

export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        theme: "system",
        get isDarkMode() {
          const { theme } = get();
          if (theme === "system") {
            return (
              typeof window !== "undefined" &&
              window.matchMedia("(prefers-color-scheme: dark)").matches
            );
          }
          return theme === "dark";
        },

        sidebar: defaultSidebarState,
        navigation: defaultNavigationState,
        loadingStates: {},
        notifications: [],
        modal: defaultModalState,
        commandPalette: defaultCommandPaletteState,

        features: {
          enableAnimations: true,
          enableSounds: false,
          enableHaptics: true,
          enableAnalytics: true,
          enableBetaFeatures: false,
        },

        // Computed properties
        get unreadNotificationCount() {
          return get().notifications.filter((n) => !n.isRead).length;
        },

        get isLoading() {
          return Object.values(get().loadingStates).some(
            (state) => state === "loading"
          );
        },

        // Theme actions
        setTheme: (theme) => {
          const result = ThemeSchema.safeParse(theme);
          if (result.success) {
            set({ theme: result.data });
          } else {
            console.error("Invalid theme:", result.error);
          }
        },

        toggleTheme: () => {
          const { theme } = get();
          const nextTheme = theme === "light" ? "dark" : "light";
          get().setTheme(nextTheme);
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

        setSidebarOpen: (isOpen) => {
          set((state) => ({
            sidebar: {
              ...state.sidebar,
              isOpen,
            },
          }));
        },

        setSidebarCollapsed: (isCollapsed) => {
          set((state) => ({
            sidebar: {
              ...state.sidebar,
              isCollapsed,
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

        addBreadcrumb: (breadcrumb) => {
          set((state) => ({
            navigation: {
              ...state.navigation,
              breadcrumbs: [...state.navigation.breadcrumbs, breadcrumb],
            },
          }));
        },

        // Loading state actions
        setLoadingState: (key, state) => {
          const result = LoadingStateSchema.safeParse(state);
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

        clearLoadingState: (key) => {
          set((state) => {
            const newLoadingStates = { ...state.loadingStates };
            delete newLoadingStates[key];
            return { loadingStates: newLoadingStates };
          });
        },

        clearAllLoadingStates: () => {
          set({ loadingStates: {} });
        },

        // Notification actions
        addNotification: (notification) => {
          const id = generateId();
          const result = NotificationSchema.safeParse({
            ...notification,
            id,
            createdAt: getCurrentTimestamp(),
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

        removeNotification: (id) => {
          set((state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          }));
        },

        markNotificationAsRead: (id) => {
          set((state) => ({
            notifications: state.notifications.map((n) =>
              n.id === id ? { ...n, isRead: true } : n
            ),
          }));
        },

        clearAllNotifications: () => {
          set({ notifications: [] });
        },

        // Modal actions
        openModal: (component, props = {}, options = {}) => {
          set({
            modal: {
              isOpen: true,
              component,
              props,
              size: options.size || "md",
              closeOnOverlayClick: options.closeOnOverlayClick ?? true,
            },
          });
        },

        closeModal: () => {
          set({ modal: defaultModalState });
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

        // Command palette actions
        openCommandPalette: () => {
          set((state) => ({
            commandPalette: {
              ...state.commandPalette,
              isOpen: true,
            },
          }));
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

        // Feature flag actions
        toggleFeature: (feature) => {
          set((state) => ({
            features: {
              ...state.features,
              [feature]: !state.features[feature],
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

        // Utility actions
        reset: () => {
          set({
            sidebar: defaultSidebarState,
            navigation: defaultNavigationState,
            loadingStates: {},
            notifications: [],
            modal: defaultModalState,
            commandPalette: defaultCommandPaletteState,
          });
        },
      }),
      {
        name: "ui-storage",
        partialize: (state) => ({
          // Only persist certain UI preferences
          theme: state.theme,
          sidebar: {
            isCollapsed: state.sidebar.isCollapsed,
            isPinned: state.sidebar.isPinned,
          },
          features: state.features,
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
