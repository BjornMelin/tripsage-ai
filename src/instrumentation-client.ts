/**
 * @fileoverview Client instrumentation entrypoint (Next.js 15.3+) for BotID.
 */

import { ensureBotIdClientInitialized } from "@/lib/security/botid-client";

try {
  ensureBotIdClientInitialized();
} catch (error) {
  // Avoid blocking hydration if BotID initialization fails.
  if (process.env.NODE_ENV === "development") {
    console.error("[BotID] Client initialization failed:", error);
  }
  globalThis.tripsageBotIdClientInitFailed = true;
}
