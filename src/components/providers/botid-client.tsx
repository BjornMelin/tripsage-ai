/**
 * @fileoverview Client provider that boots BotID request instrumentation.
 */

"use client";

import { useEffect } from "react";
import { ensureBotIdClientInitialized } from "@/lib/security/botid-client";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

export function BotIdClientProvider() {
  useEffect(() => {
    if (globalThis.tripsageBotIdClientInitFailed) {
      globalThis.tripsageBotIdClientInitFailed = undefined;
      recordClientErrorOnActiveSpan(new Error("BotID early initialization failed"), {
        action: "instrumentation-client",
        context: "BotIdClientProvider",
      });
    }

    try {
      ensureBotIdClientInitialized();
    } catch (error) {
      const exception =
        error instanceof Error ? error : new Error("BotID initialization failed");
      recordClientErrorOnActiveSpan(exception, {
        action: "ensureBotIdClientInitialized",
        context: "BotIdClientProvider",
      });
    }
  }, []);

  return null;
}
