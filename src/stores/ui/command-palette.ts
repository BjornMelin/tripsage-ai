/**
 * @fileoverview Command palette slice for UI store.
 */

import type { StateCreator } from "zustand";
import { useUiStore } from "./index";
import type { CommandPaletteSlice, CommandPaletteState, UiState } from "./types";

export const DEFAULT_COMMAND_PALETTE_STATE: CommandPaletteState = {
  isOpen: false,
  query: "",
  results: [],
};

export const createCommandPaletteSlice: StateCreator<
  UiState,
  [],
  [],
  CommandPaletteSlice
> = (set) => ({
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
  commandPalette: DEFAULT_COMMAND_PALETTE_STATE,

  openCommandPalette: () => {
    set((state) => ({
      commandPalette: {
        ...state.commandPalette,
        isOpen: true,
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
});

// ===== SELECTOR HOOKS =====

/** Select whether the command palette is open */
export const useCommandPaletteOpen = () => useUiStore((s) => s.commandPalette.isOpen);

/** Select the command palette query */
export const useCommandPaletteQuery = () => useUiStore((s) => s.commandPalette.query);

/** Select the command palette results */
export const useCommandPaletteResults = () =>
  useUiStore((s) => s.commandPalette.results);
