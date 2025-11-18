import type { ReactNode } from "react";
import { requireUser } from "@/lib/auth/server";

export default async function SettingsLayout({ children }: { children: ReactNode }) {
  // Guard all settings routes behind Supabase SSR authentication.
  await requireUser({ redirectTo: "/settings" });
  return children;
}
