/**
 * @fileoverview Authenticated app layout wrapper for client-side providers.
 */

import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { createServerSupabase } from "@/lib/supabase/server";
import { Providers } from "./providers";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const supabase = await createServerSupabase();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return <Providers>{children}</Providers>;
}
