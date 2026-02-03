/**
 * @fileoverview Authenticated app layout wrapper for client-side providers.
 */

import { headers } from "next/headers";
import type { ReactNode } from "react";
import { AuthedAppShell } from "@/components/providers/app-shell";
import { Providers } from "./providers";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <AuthedAppShell nonce={nonce}>
      <Providers>{children}</Providers>
    </AuthedAppShell>
  );
}
