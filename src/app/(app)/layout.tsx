/**
 * @fileoverview Authenticated app layout wrapper for client-side providers.
 */

import { Providers } from "./providers";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <Providers>{children}</Providers>;
}
