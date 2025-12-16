/**
 * @fileoverview Navigation slice for UI store.
 */

import type { StateCreator } from "zustand";
import type { NavigationSlice, NavigationState, UiState } from "./types";

export const DEFAULT_NAVIGATION_STATE: NavigationState = {
  activeRoute: "/",
  breadcrumbs: [],
};

export const createNavigationSlice: StateCreator<UiState, [], [], NavigationSlice> = (
  set
) => ({
  addBreadcrumb: (breadcrumb) => {
    set((state) => ({
      navigation: {
        ...state.navigation,
        breadcrumbs: [...state.navigation.breadcrumbs, breadcrumb],
      },
    }));
  },
  navigation: DEFAULT_NAVIGATION_STATE,

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
});
