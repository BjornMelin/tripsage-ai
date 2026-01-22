/**
 * @fileoverview Client instrumentation entrypoint (Next.js 15.3+) for BotID.
 */

import { patchPerformanceMeasureForPrerender } from "@/lib/performance/patch-performance-measure";
import { ensureBotIdClientInitialized } from "@/lib/security/botid-client";

patchPerformanceMeasureForPrerender();
ensureBotIdClientInitialized();
