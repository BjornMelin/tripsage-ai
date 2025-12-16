/**
 * @fileoverview Theme slice for UI store.
 */

import { themeSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import type { ThemeSlice, UiState } from "./types";

const logger = createStoreLogger({ storeName: "ui" });

export const createThemeSlice: StateCreator<UiState, [], [], ThemeSlice> = (
  set,
  get
) => ({
  // isDarkMode is defined as a computed getter in the main store composition
  isDarkMode: false,

  setTheme: (theme) => {
    const result = themeSchema.safeParse(theme);
    if (result.success) {
      set({ theme: result.data });
    } else {
      logger.error("Invalid theme", {
        error: result.error,
        errorMessage: result.error.message,
        issues: result.error.issues.map((issue) => ({
          message: issue.message,
          path: issue.path.join("."),
        })),
      });
    }
  },
  theme: "system",

  toggleTheme: () => {
    const { theme } = get();
    let nextTheme: "system" | "light" | "dark";

    if (theme === "light") {
      nextTheme = "dark";
    } else if (theme === "dark") {
      nextTheme = "system";
    } else {
      nextTheme = "light";
    }

    get().setTheme(nextTheme);
  },
});
