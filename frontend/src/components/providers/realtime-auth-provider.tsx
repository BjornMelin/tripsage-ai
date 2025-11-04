"use client";

/**
 * @fileoverview React provider that synchronizes Supabase Realtime authentication
 * with the current Supabase session token.
 */

import { useEffect } from "react";
import { getBrowserClient } from "@/lib/supabase/client";
import { getAccessToken } from "@/lib/supabase/token";

/**
 * Keeps Supabase Realtime authorized with the latest access token, reacting to
 * authentication lifecycle events and cleaning up on unmount.
 *
 * @returns {null} This component renders nothing; it purely manages side effects.
 */
export function RealtimeAuthProvider(): null {
  useEffect(() => {
    const supabase = getBrowserClient();

    let isMounted = true;

    // biome-ignore lint/style/useNamingConvention: Not a React hook
    async function initializeRealtimeAuthHandler(): Promise<void> {
      try {
        const token = await getAccessToken(supabase);
        if (!isMounted) {
          return;
        }
        supabase.realtime.setAuth(token ?? "");
      } catch {
        // Allow UI to operate; realtime auth will refresh when a valid token exists.
      }
    }

    const { data: subscription } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        const token = session?.access_token ?? null;
        supabase.realtime.setAuth(token ?? "");
      }
    );

    initializeRealtimeAuthHandler();

    return () => {
      isMounted = false;
      supabase.realtime.setAuth("");
      subscription?.subscription.unsubscribe();
    };
  }, []);

  return null;
}

export default RealtimeAuthProvider;
