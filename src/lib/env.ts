/**
 * @fileoverview Canonical server-only environment access entrypoint.
 */

// NOTE: This module intentionally does not export any client-safe env access.
// Client code must import from `@/lib/env/client` to prevent accidental
// server-secret bundling.

import "server-only";

export { getRuntimeEnv } from "@/lib/env/runtime-env";
export {
  env,
  getGoogleMapsBrowserKey,
  getGoogleMapsServerKey,
  getServerEnv,
  getServerEnvVar,
  getServerEnvVarWithFallback,
} from "@/lib/env/server";

export {
  getBotIdEnableCsv,
  getIdempotencyFailOpenDefault,
  isTelemetrySilent,
  isTrustProxyEnabled,
  isVercelRuntime,
} from "@/lib/env/server-flags";
