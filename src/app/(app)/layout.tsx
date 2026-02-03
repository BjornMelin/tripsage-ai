/**
 * @fileoverview Authenticated app layout wrapper for client-side providers.
 */

import { headers } from "next/headers";
import type { ReactNode } from "react";
import { AuthedAppShell } from "@/components/providers/app-shell";
import { Providers } from "./providers";

/**
 * Authenticated app layout wrapper with CSP nonce support.
 *
 * Reads the `x-nonce` header via `headers()` on the server and passes it to
 * `AuthedAppShell` for CSP-aware theming.
 *
 * @param children - The child elements to render.
 * @returns The authenticated app layout wrapper around providers and children.
 */
export default async function AppLayout({ children }: { children: ReactNode }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <AuthedAppShell nonce={nonce}>
      <Providers>{children}</Providers>
    </AuthedAppShell>
  );
}
