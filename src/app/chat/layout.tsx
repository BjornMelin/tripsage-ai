import type { ReactNode } from "react";
import { requireUser } from "@/lib/auth/server";

export default async function ChatLayout({ children }: { children: ReactNode }) {
  // Guard chat UI behind Supabase SSR authentication.
  await requireUser({ redirectTo: "/chat" });
  return children;
}
