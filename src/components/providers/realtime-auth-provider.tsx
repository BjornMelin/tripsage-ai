/**
 * @fileoverview React provider that synchronizes Supabase Realtime authentication with the current Supabase session token.
 */

"use client";

import { useEffect } from "react";

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
        if (process.env.NODE_ENV === "development") {
          console.error("Failed to get initial session:", error);
        }
      }
    }

    initializeRealtimeAuthHandler().catch((error: unknown) => {
      // Allow UI to operate; realtime auth will refresh when a valid token exists.
      if (process.env.NODE_ENV === "development") {
        console.error("initializeRealtimeAuthHandler failed:", error);
      }
    });

    return () => {
      isMounted = false;
      cleanupClientAuth?.();
      cleanupSubscription?.();
    };
  }, []);

  return null;
}

export default RealtimeAuthProvider;
