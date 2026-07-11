/**
 * @fileoverview Next.js client instrumentation entrypoint for BotID.
 */

import { patchPerformanceMeasureForPrerender } from "@/lib/performance/patch-performance-measure";
import {
  ensureBotIdClientInitialized,
  shouldInitializeBotIdClientFromDocument,
} from "@/lib/security/botid-client";

patchPerformanceMeasureForPrerender();
if (shouldInitializeBotIdClientFromDocument()) {
  ensureBotIdClientInitialized();
}
