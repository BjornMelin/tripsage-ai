/**
 * @fileoverview Client-only BotID initialization helper (CSP-safe).
 */

"use client";

import { initBotId } from "botid/client/core";
import { getBotIdProtectRules } from "@/config/botid-protect";

declare global {
  var tripsageBotIdClientInitialized: boolean | undefined;
  var tripsageBotIdClientInitFailed: boolean | undefined;
  var tripsageBotIdClientInitError: Error | undefined;
}

/**
 * Consumes the most recent BotID client initialization failure.
 *
 * @returns The last initialization Error or null if no failure is pending.
 */
export function consumeBotIdClientInitFailure(): Error | null {
  if (!globalThis.tripsageBotIdClientInitFailed) return null;

  const error =
    globalThis.tripsageBotIdClientInitError ??
    new Error("BotID client initialization failed");
  globalThis.tripsageBotIdClientInitFailed = undefined;
  globalThis.tripsageBotIdClientInitError = undefined;
  return error;
}

/**
 * Reads the server-rendered BotID decision before client hydration.
 *
 * The marker is not a security boundary; server-side BotID enforcement remains
 * authoritative. It prevents client instrumentation from patching local requests when
 * the canonical server environment predicate has disabled BotID.
 *
 * @returns Whether BotID client initialization is enabled.
 */
export function shouldInitializeBotIdClientFromDocument(): boolean {
  if (typeof document === "undefined") return false;
  return document.documentElement.dataset.botidEnabled === "true";
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
    const exception =
      error instanceof Error ? error : new Error("BotID client initialization failed");
    globalThis.tripsageBotIdClientInitFailed = true;
    globalThis.tripsageBotIdClientInitError = exception;
    globalThis.tripsageBotIdClientInitialized = false;
  }
}
