/**
 * @fileoverview Shared test utilities and helpers for UI store tests.
 */

import { act } from "@testing-library/react";
import { useUiStore } from "@/stores/ui-store";

/**
 * Resets the UI store to its initial state.
 */
export const resetUiStore = (): void => {
  act(() => {
    useUiStore.getState().reset();
    useUiStore.setState({
      features: {
        enableAnalytics: true,
        enableAnimations: true,
        enableBetaFeatures: false,
        enableHaptics: true,
        enableSounds: false,
      },
      theme: "system",
    });
  });
};
