/**
 * @fileoverview Feature flags slice for UI store.
 */

import type { StateCreator } from "zustand";
import type { FeatureFlags, FeaturesSlice, UiState } from "./types";

export const DEFAULT_FEATURES: FeatureFlags = {
  enableAnalytics: true,
  enableAnimations: true,
  enableBetaFeatures: false,
  enableHaptics: true,
  enableSounds: false,
};

export const createFeaturesSlice: StateCreator<UiState, [], [], FeaturesSlice> = (
  set
) => ({
  features: DEFAULT_FEATURES,

  setFeature: (feature, enabled) => {
    set((state) => ({
      features: {
        ...state.features,
        [feature]: enabled,
      },
    }));
  },

  toggleFeature: (feature) => {
    set((state) => ({
      features: {
        ...state.features,
        [feature]: !state.features[feature],
      },
    }));
  },
});
