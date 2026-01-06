/**
 * @fileoverview Authenticated app layout wrapper for client-side providers.
 */

import { headers } from "next/headers";
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
    const headersList = await headers();
    const pathname = headersList.get("x-pathname") || "/dashboard";
    const nextPath = pathname.startsWith("/") ? pathname : "/dashboard";
    redirect(`/login?next=${encodeURIComponent(nextPath)}`);
  }

  return <Providers>{children}</Providers>;
}
