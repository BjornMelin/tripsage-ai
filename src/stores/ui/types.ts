/**
 * @fileoverview Type definitions for UI store slices.
 */

import type { LoadingState, LoadingStates, Notification, Theme } from "@schemas/stores";

// ===== SIDEBAR TYPES =====

export interface SidebarState {
  isOpen: boolean;
  isCollapsed: boolean;
  isPinned: boolean;
}

// ===== NAVIGATION TYPES =====

export interface NavigationState {
  activeRoute: string;
  breadcrumbs: Array<{
    label: string;
    href?: string;
  }>;
}

// ===== MODAL TYPES =====

export interface ModalState {
  isOpen: boolean;
  component: string | null;
  props?: Record<string, unknown>;
  size?: "sm" | "md" | "lg" | "xl" | "full";
  closeOnOverlayClick?: boolean;
}

// ===== COMMAND PALETTE TYPES =====

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

// ===== FEATURE FLAGS =====

export interface FeatureFlags {
  enableAnimations: boolean;
  enableSounds: boolean;
  enableHaptics: boolean;
  enableAnalytics: boolean;
  enableBetaFeatures: boolean;
}

// ===== SLICE INTERFACES =====

export interface ThemeSlice {
  theme: Theme;
  isDarkMode: boolean;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

export interface SidebarSlice {
  sidebar: SidebarState;
  toggleSidebar: () => void;
  setSidebarOpen: (isOpen: boolean) => void;
  setSidebarCollapsed: (isCollapsed: boolean) => void;
  setSidebarPinned: (isPinned: boolean) => void;
}

export interface NavigationSlice {
  navigation: NavigationState;
  setActiveRoute: (route: string) => void;
  setBreadcrumbs: (breadcrumbs: NavigationState["breadcrumbs"]) => void;
  addBreadcrumb: (breadcrumb: NavigationState["breadcrumbs"][0]) => void;
}

export interface LoadingSlice {
  loadingStates: LoadingStates;
  isLoading: boolean;
  setLoadingState: (key: string, state: LoadingState) => void;
  clearLoadingState: (key: string) => void;
  clearAllLoadingStates: () => void;
}

export interface NotificationsSlice {
  notifications: Notification[];
  unreadNotificationCount: number;
  addNotification: (notification: Omit<Notification, "id" | "createdAt">) => string;
  removeNotification: (id: string) => void;
  markNotificationAsRead: (id: string) => void;
  clearAllNotifications: () => void;
}

export interface ModalSlice {
  modal: ModalState;
  openModal: (
    component: string,
    props?: Record<string, unknown>,
    options?: Partial<ModalState>
  ) => void;
  closeModal: () => void;
  updateModalProps: (props: Record<string, unknown>) => void;
}

export interface CommandPaletteSlice {
  commandPalette: CommandPaletteState;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  setCommandPaletteQuery: (query: string) => void;
  setCommandPaletteResults: (results: CommandPaletteState["results"]) => void;
}

export interface FeaturesSlice {
  features: FeatureFlags;
  toggleFeature: (feature: keyof FeatureFlags) => void;
  setFeature: (feature: keyof FeatureFlags, enabled: boolean) => void;
}

export interface UtilitySlice {
  reset: () => void;
}

// ===== COMBINED STATE =====

export type UiState = ThemeSlice &
  SidebarSlice &
  NavigationSlice &
  LoadingSlice &
  NotificationsSlice &
  ModalSlice &
  CommandPaletteSlice &
  FeaturesSlice &
  UtilitySlice;
