/**
 * @fileoverview Client component for initiating Google Calendar OAuth connection.
 */

"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useToast } from "@/components/ui/use-toast";
import { createClient } from "@/lib/supabase";

/**
 * CalendarConnectClient component.
 *
 * Client component that initiates Google OAuth flow for calendar access.
 */
export function CalendarConnectClient() {
  const [isConnecting, setIsConnecting] = useState(false);
  const { toast } = useToast();
  const supabase = useMemo(() => createClient(), []);

  const handleConnect = async () => {
    setIsConnecting(true);
    try {
      const redirectUrl =
        process.env.NEXT_PUBLIC_SITE_URL ||
        process.env.NEXT_PUBLIC_APP_URL ||
        window.location.origin;
      const { error } = await supabase.auth.signInWithOAuth({
        options: {
          redirectTo: `${redirectUrl}/auth/callback?next=/dashboard`,
          scopes: "https://www.googleapis.com/auth/calendar.events",
        },
        provider: "google",
      });

      if (error) {
        console.error("OAuth error:", error);
        toast({
          description: error.message || "Failed to connect Google Calendar",
          title: "Connection failed",
          variant: "destructive",
        });
        setIsConnecting(false);
      } else {
        toast({
          description: "Please authorize calendar access in the popup window.",
          title: "Redirecting to Google",
        });
        // If successful, user will be redirected to OAuth flow
      }
    } catch (error) {
      console.error("Connection error:", error);
      toast({
        description: "Failed to connect calendar. Please try again.",
        title: "Connection error",
        variant: "destructive",
      });
      setIsConnecting(false);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Connect your Google Calendar to sync events, check availability, and export
        itineraries.
      </p>
      <Button
        onClick={handleConnect}
        disabled={isConnecting}
        className="w-full sm:w-auto"
      >
        {isConnecting ? (
          <>
            <LoadingSpinner size="sm" className="mr-2" />
            Connecting...
          </>
        ) : (
          "Connect Google Calendar"
        )}
      </Button>
    </div>
  );
}
