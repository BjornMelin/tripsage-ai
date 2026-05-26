/**
 * @fileoverview Next.js client instrumentation entrypoint for BotID.
 */

import { patchPerformanceMeasureForPrerender } from "@/lib/performance/patch-performance-measure";
import { ensureBotIdClientInitialized } from "@/lib/security/botid-client";

patchPerformanceMeasureForPrerender();
ensureBotIdClientInitialized();
