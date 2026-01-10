/**
 * @fileoverview Client instrumentation entrypoint (Next.js 15.3+) for BotID.
 */

import { ensureBotIdClientInitialized } from "@/lib/security/botid-client";

try {
  ensureBotIdClientInitialized();
} catch {
  // Avoid blocking hydration if BotID initialization fails.
  globalThis.tripsageBotIdClientInitFailed = true;
}
