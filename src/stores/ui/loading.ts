/**
 * @fileoverview Loading state slice for UI store.
 */

"use client";

import { loadingStateSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import type { LoadingSlice, UiState } from "./types";

const logger = createStoreLogger({ storeName: "ui" });

export const createLoadingSlice: StateCreator<UiState, [], [], LoadingSlice> = (
  set,
  _get
) => ({
  clearAllLoadingStates: () => {
    set({ loadingStates: {} });
  },

  clearLoadingState: (key) => {
    set((state) => {
      const newLoadingStates = { ...state.loadingStates };
      delete newLoadingStates[key];
      return { loadingStates: newLoadingStates };
    });
  },

  // isLoading is defined as a computed getter in the main store composition
  isLoading: false,
  loadingStates: {},

  setLoadingState: (key, state) => {
    const result = loadingStateSchema.safeParse(state);
    if (result.success) {
      set((currentState) => ({
        loadingStates: {
          ...currentState.loadingStates,
          [key]: result.data,
        },
      }));
    } else {
      logger.error("Invalid loading state", {
        error: result.error,
        errorMessage: result.error.message,
        issues: result.error.issues.map((issue) => ({
          message: issue.message,
          path: issue.path.join("."),
        })),
        key,
      });
    }
  },
});
