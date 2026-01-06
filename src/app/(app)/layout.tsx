/**
 * @fileoverview Authenticated app layout wrapper for client-side providers.
 */

import type { ReactNode } from "react";

import { Providers } from "./providers";

export default function AppLayout({ children }: { children: ReactNode }) {
  return <Providers>{children}</Providers>;
}
