"use client";

/**
 * @fileoverview React provider that synchronizes Supabase Realtime authentication
 * with the current Supabase session token.
 */

import { useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
import { getAccessToken } from "@/lib/supabase/token";

/**
 * Keeps Supabase Realtime authorized with the latest access token, reacting to
 * authentication lifecycle events and cleaning up on unmount.
 *
 * @returns {null} This component renders nothing; it purely manages side effects.
 */
export function RealtimeAuthProvider(): null {
  useEffect(() => {
    const supabase = createClient();

    let isMounted = true;

    async function initializeRealtimeAuth(): Promise<void> {
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
      async (_event, session) => {
        const token = session?.access_token ?? null;
        supabase.realtime.setAuth(token ?? "");
      }
    );

    void initializeRealtimeAuth();

    return () => {
      isMounted = false;
      supabase.realtime.setAuth("");
      subscription?.subscription.unsubscribe();
    };
  }, []);

  return null;
}

export default RealtimeAuthProvider;
