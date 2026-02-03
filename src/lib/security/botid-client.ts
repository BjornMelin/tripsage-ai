/**
 * @fileoverview Client-only BotID initialization helper (CSP-safe).
 */

"use client";

import { initBotId } from "botid/client/core";
import { getBotIdProtectRules } from "@/config/botid-protect";

declare global {
  var tripsageBotIdClientInitialized: boolean | undefined;
  var tripsageBotIdClientInitFailed: boolean | undefined;
}

export function ensureBotIdClientInitialized(): void {
  // NOTE: We intentionally use `botid/client/core` rather than `botid/client`'s
  // `BotIdClient` React component because the component injects a large inline
  // script (blocked by this app's production CSP).
  if (process.env.NODE_ENV === "test") return;
  if (globalThis.tripsageBotIdClientInitialized) return;

  try {
    initBotId({ protect: getBotIdProtectRules() });
    globalThis.tripsageBotIdClientInitFailed = false;
    // A public, global flag is not a security boundary; server-side BotID
    // verification still enforces protection. This only prevents double init.
    if (process.env.NODE_ENV === "production") {
      Object.defineProperty(globalThis, "tripsageBotIdClientInitialized", {
        configurable: true,
        value: true,
        writable: false,
      });
    } else {
      globalThis.tripsageBotIdClientInitialized = true;
    }
  } catch (error) {
    // BotID client init failed; server-side verification remains enforced.
    globalThis.tripsageBotIdClientInitFailed = true;
    globalThis.tripsageBotIdClientInitialized = false;
    if (process.env.NODE_ENV === "development") {
      console.warn("[BotID] Client initialization failed:", error);
    }
  }
}
