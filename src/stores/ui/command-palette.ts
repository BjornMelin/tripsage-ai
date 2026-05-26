/**
 * @fileoverview Command palette slice for UI store.
 */

import type { StateCreator } from "zustand";
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
