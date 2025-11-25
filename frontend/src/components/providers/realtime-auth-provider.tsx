/**
 * @fileoverview React provider that synchronizes Supabase Realtime authentication
 * with the current Supabase session token.
 */

"use client";

import { useEffect } from "react";
import { getBrowserClient } from "@/lib/supabase";

/**
 * Keeps Supabase Realtime authorized with the latest access token, reacting to
 * authentication lifecycle events and cleaning up on unmount.
 *
 * @returns This component renders nothing; it purely manages side effects.
 */
export function RealtimeAuthProvider(): null {
  useEffect(() => {
    const supabase = getBrowserClient();
    // During SSR, supabase is null - skip auth setup
    if (!supabase) return;

    // Capture non-null reference for use in nested functions
    const client = supabase;
    let isMounted = true;

    // biome-ignore lint/style/useNamingConvention: Not a React hook
    async function initializeRealtimeAuthHandler(): Promise<void> {
      try {
        const {
          data: { session },
        } = await client.auth.getSession();
        const token = session?.access_token ?? null;
        if (!isMounted) {
          return;
        }
        client.realtime.setAuth(token ?? "");
      } catch {
        // Allow UI to operate; realtime auth will refresh when a valid token exists.
      }
    }

    const { data: subscription } = client.auth.onAuthStateChange((_event, session) => {
      const token = session?.access_token ?? null;
      client.realtime.setAuth(token ?? "");
    });

    initializeRealtimeAuthHandler();

    return () => {
      isMounted = false;
      client.realtime.setAuth("");
      subscription?.subscription.unsubscribe();
    };
  }, []);

  return null;
}

export default RealtimeAuthProvider;
