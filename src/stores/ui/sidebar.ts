/**
 * @fileoverview Sidebar slice for UI store.
 */

import type { StateCreator } from "zustand";
import type { SidebarSlice, SidebarState, UiState } from "./types";

export const DEFAULT_SIDEBAR_STATE: SidebarState = {
  isCollapsed: false,
  isOpen: true,
  isPinned: true,
};

export const createSidebarSlice: StateCreator<UiState, [], [], SidebarSlice> = (
  set
) => ({
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
  sidebar: DEFAULT_SIDEBAR_STATE,

  toggleSidebar: () => {
    set((state) => ({
      sidebar: {
        ...state.sidebar,
        isOpen: !state.sidebar.isOpen,
      },
    }));
  },
});
