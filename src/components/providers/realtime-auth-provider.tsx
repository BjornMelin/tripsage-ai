/**
 * @fileoverview React provider that synchronizes Supabase Realtime authentication with the current Supabase session token.
 */

"use client";

import { useEffect } from "react";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

/**
 * Keeps Supabase Realtime authorized with the latest access token, reacting to
 * authentication lifecycle events and cleaning up on unmount.
 *
 * @returns This component renders nothing; it purely manages side effects.
 */
export function RealtimeAuthProvider(): null {
  useEffect(() => {
    let isMounted = true;
    let cleanupSubscription: (() => void) | null = null;
    let cleanupClientAuth: (() => void) | null = null;

    const normalizeRealtimeAuthError = (error: unknown): Error => {
      return error instanceof Error ? error : new Error(String(error));
    };

    const reportRealtimeAuthError = (error: unknown, action: string): void => {
      recordClientErrorOnActiveSpan(normalizeRealtimeAuthError(error), {
        action,
        context: "RealtimeAuthProvider",
      });
    };

    // biome-ignore lint/style/useNamingConvention: Not a React hook
    async function initializeRealtimeAuthHandler(): Promise<void> {
      const { getBrowserClient } = await import("@/lib/supabase");
      const supabase = getBrowserClient();
      // Null check guards against initial client render before Supabase client is hydrated
      if (!supabase || !isMounted) return;

      cleanupClientAuth = () => {
        supabase.realtime.setAuth("");
      };

      const { data: authListener } = supabase.auth.onAuthStateChange(
        (_event, session) => {
          if (!isMounted) return;
          const token = session?.access_token ?? null;
          supabase.realtime.setAuth(token ?? "");
        }
      );
      cleanupSubscription = () => {
        authListener?.subscription.unsubscribe();
      };

      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!isMounted) return;
        const token = session?.access_token ?? null;
        supabase.realtime.setAuth(token ?? "");
      } catch (error: unknown) {
        // Allow UI to operate; realtime auth will refresh when a valid token exists.
        reportRealtimeAuthError(error, "getInitialSession");
      }
    }

    initializeRealtimeAuthHandler().catch((error: unknown) => {
      // Allow UI to operate; realtime auth will refresh when a valid token exists.
      reportRealtimeAuthError(error, "initialize");
    });

    return () => {
      isMounted = false;
      cleanupSubscription?.();
      cleanupClientAuth?.();
    };
  }, []);

  return null;
}

export default RealtimeAuthProvider;
