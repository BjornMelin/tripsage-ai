/**
 * @fileoverview Auth session slice - mirrors Supabase SSR session state for UI purposes only.
 *
 * Supabase cookies remain the single source of truth for authentication.
 * This slice intentionally does not persist or manage access/refresh tokens.
 */

import type { AuthSession } from "@schemas/stores";
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { timeUntil } from "@/stores/helpers";

/**
 * Auth session state interface.
 */
interface AuthSessionState {
  // State
  session: AuthSession | null;

  // Computed
  sessionTimeRemaining: number;

  // Actions
  setSession: (session: AuthSession | null) => void;
  resetSession: () => void;
}

/**
 * Auth session store hook.
 */
export const useAuthSession = create<AuthSessionState>()(
  devtools(
    (set, get) => ({
      resetSession: () => {
        set({ session: null });
      },
      session: null,

      get sessionTimeRemaining() {
        return timeUntil(get().session?.expiresAt ?? null);
      },

      setSession: (session) => {
        set({ session });
      },
    }),
    { name: "AuthSession" }
  )
);

// Selectors
export const useSessionTimeRemaining = () =>
  useAuthSession((state) => state.sessionTimeRemaining);
