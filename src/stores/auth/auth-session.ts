/**
 * @fileoverview Auth session slice - mirrors Supabase SSR session state for UI purposes only.
 */

import type { AuthSession } from "@schemas/stores";
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { timeUntil } from "@/stores/helpers";
import { withComputed } from "@/stores/middleware/computed";

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
    withComputed(
      {
        compute: (state) => ({
          sessionTimeRemaining: timeUntil(state.session?.expiresAt ?? null),
        }),
      },
      (set) => ({
        resetSession: () => {
          set({ session: null });
        },
        session: null,
        sessionTimeRemaining: 0,
        setSession: (session) => {
          set({ session });
        },
      })
    ),
    { name: "AuthSession" }
  )
);

// Selectors
export const useSessionTimeRemaining = () =>
  useAuthSession((state) => state.sessionTimeRemaining);
