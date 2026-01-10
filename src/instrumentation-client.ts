/**
 * @fileoverview Client instrumentation entrypoint (Next.js 15.3+) for BotID.
 */

import { ensureBotIdClientInitialized } from "@/lib/security/botid-client";

ensureBotIdClientInitialized();
