import {
  authCoreInitialState,
  useAuthCore,
} from "@/features/auth/store/auth/auth-core";
import { useAuthSession } from "@/features/auth/store/auth/auth-session";
import {
  authValidationInitialState,
  useAuthValidation,
} from "@/features/auth/store/auth/auth-validation";

/**
 * Resets all auth-related Zustand slices to their initial view-model state.
 *
 * This helper mirrors Supabase SSR session authority but never mutates or
 * persists tokens. Use it when all client auth view state must be discarded,
 * including test isolation and terminal flows such as confirmed account deletion.
 */
export const resetAuthState = (): void => {
  // Reset auth-core view-model state (user snapshot and flags).
  useAuthCore.setState(authCoreInitialState);

  // Clear any persisted auth-core snapshot to avoid leaking state across sessions.
  const storeWithPersist = useAuthCore as typeof useAuthCore & {
    persist?: {
      clearStorage?: () => void;
    };
  };
  storeWithPersist.persist?.clearStorage?.();

  // Reset session slice via its public API to avoid shape drift.
  const { resetSession } = useAuthSession.getState();
  resetSession();

  // Reset validation slice flags and errors.
  useAuthValidation.setState(authValidationInitialState);
};
