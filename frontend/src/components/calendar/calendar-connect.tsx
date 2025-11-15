/**
 * @fileoverview Server Component wrapper for calendar connection.
 *
 * Provides a server-side wrapper that checks calendar connection status
 * and renders appropriate UI.
 */

import { createServerSupabase } from "@/lib/supabase/server";
import { CalendarStatus } from "./calendar-status";

/**
 * Props for CalendarConnect component.
 */
export interface CalendarConnectProps {
  /** Optional className for styling */
  className?: string;
}

/**
 * CalendarConnect component.
 *
 * Server Component that checks calendar connection status and renders
 * the CalendarStatus component.
 */
export async function CalendarConnect({ className }: CalendarConnectProps) {
  const supabase = await createServerSupabase();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return (
      <div className={className}>
        <p className="text-sm text-muted-foreground">
          Please sign in to connect your calendar.
        </p>
      </div>
    );
  }

  return <CalendarStatus className={className} />;
}
