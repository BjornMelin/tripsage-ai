/**
 * @fileoverview Client component for initiating Google Calendar OAuth connection.
 */

"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

/**
 * CalendarConnectClient component.
 *
 * Client component that initiates Google OAuth flow for calendar access.
 */
export function CalendarConnectClient() {
  const [isConnecting, setIsConnecting] = useState(false);
  const supabase = createClient();

  const handleConnect = async () => {
    setIsConnecting(true);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        options: {
          redirectTo: `${window.location.origin}/auth/callback?next=/dashboard`,
          scopes: "https://www.googleapis.com/auth/calendar.events",
        },
        provider: "google",
      });

      if (error) {
        console.error("OAuth error:", error);
        alert(`Failed to connect: ${error.message}`);
        setIsConnecting(false);
      }
      // If successful, user will be redirected to OAuth flow
    } catch (error) {
      console.error("Connection error:", error);
      alert("Failed to connect calendar");
      setIsConnecting(false);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Connect your Google Calendar to sync events, check availability, and export
        itineraries.
      </p>
      <Button onClick={handleConnect} disabled={isConnecting}>
        {isConnecting ? "Connecting..." : "Connect Google Calendar"}
      </Button>
    </div>
  );
}
