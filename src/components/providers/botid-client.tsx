/**
 * @fileoverview Client provider that boots BotID request instrumentation.
 */

"use client";

import { useEffect } from "react";
import {
  consumeBotIdClientInitFailure,
  ensureBotIdClientInitialized,
} from "@/lib/security/botid-client";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

function ReportBotIdInitFailure(error: Error, action: string): void {
  recordClientErrorOnActiveSpan(error, {
    action,
    context: "BotIdClientProvider",
  });
}

export function BotIdClientProvider() {
  useEffect(() => {
    const earlyInitError = consumeBotIdClientInitFailure();
    if (earlyInitError) {
      ReportBotIdInitFailure(earlyInitError, "instrumentation-client");
    }

    try {
      ensureBotIdClientInitialized();
      const providerInitError = consumeBotIdClientInitFailure();
      if (providerInitError) {
        ReportBotIdInitFailure(providerInitError, "ensureBotIdClientInitialized");
      }
    } catch (error) {
      const exception =
        error instanceof Error ? error : new Error("BotID initialization failed");
      ReportBotIdInitFailure(exception, "ensureBotIdClientInitialized");
    }
  }, []);

  return null;
}
