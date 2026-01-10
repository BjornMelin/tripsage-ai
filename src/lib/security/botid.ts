/**
 * @fileoverview BotID integration for bot detection on high-value API routes.
 */

import "server-only";

import type { IncomingHttpHeaders } from "node:http";
import { checkBotId } from "botid/server";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { createServerLogger } from "@/lib/telemetry/logger";

const botIdLogger = createServerLogger("security.botid");

/**
 * Result type from checkBotId with verified bot info.
 * The actual return type is a union, but we extract the fields we need.
 */
export interface BotIdVerification {
  isBot: boolean;
  isHuman: boolean;
  isVerifiedBot: boolean;
  bypassed: boolean;
  verifiedBotName?: string;
  verifiedBotCategory?: string;
}

/**
 * Categories of verified bots allowed through BotID protection.
 *
 * Currently allows AI assistants (ChatGPT, Perplexity, Claude web search, etc.)
 * while blocking other bot categories (search crawlers, monitors, etc.).
 *
 * @see https://vercel.com/docs/botid/verified-bots
 * @see https://bots.fyi for the full verified bot directory
 */
const ALLOWED_VERIFIED_BOT_CATEGORIES = ["ai_assistant"] as const;

type AllowedBotCategory = (typeof ALLOWED_VERIFIED_BOT_CATEGORIES)[number];

/**
 * Error thrown when a bot is detected attempting to access a protected route.
 *
 * Contains the route name and verification info for logging and debugging.
 */
export class BotDetectedError extends Error {
  public readonly status = 403 as const;
  public readonly code = "bot_detected" as const;
  public readonly routeName: string;
  public readonly verification: BotIdVerification;

  constructor(routeName: string, verification: BotIdVerification) {
    super("Automated access is not allowed.");
    this.name = "BotDetectedError";
    this.routeName = routeName;
    this.verification = verification;
    Object.setPrototypeOf(this, BotDetectedError.prototype);
  }

  /**
   * User-friendly error message for display.
   */
  get userMessage(): string {
    return "Automated access is not allowed.";
  }

  /**
   * Convert to JSON for logging (excludes sensitive verification details).
   */
  // biome-ignore lint/style/useNamingConvention: Standard JSON serialization method
  toJSON() {
    return {
      code: this.code,
      message: this.message,
      name: this.name,
      routeName: this.routeName,
      status: this.status,
    };
  }
}

/**
 * Type guard to check if an error is a BotDetectedError.
 *
 * @param error - The error to check.
 * @returns True if the error is a BotDetectedError.
 */
export function isBotDetectedError(error: unknown): error is BotDetectedError {
  return error instanceof BotDetectedError;
}

/**
 * Options for the assertHumanOrThrow function.
 */
export interface AssertHumanOptions {
  /**
   * BotID detection level.
   * - "basic": Free tier, validates browser sessions (default)
   * - "deep": Kasada-powered analysis with thousands of signals ($1/1000 calls)
   *
   * @default "basic"
   */
  level?: "basic" | "deep";

  /**
   * Whether to allow verified AI assistants (ChatGPT, Perplexity, Claude, etc.).
   * They will still be subject to rate limiting via Upstash.
   *
   * @default true
   */
  allowVerifiedAiAssistants?: boolean;

  /**
   * Request headers to pass to BotID verification.
   *
   * BotID's server SDK can attempt to infer headers from the platform runtime.
   * Passing headers explicitly makes verification deterministic across local,
   * CI, and non-Vercel environments.
   */
  headers?: Headers | IncomingHttpHeaders;
}

function toIncomingHttpHeaders(headers: Headers): IncomingHttpHeaders {
  const result: IncomingHttpHeaders = {};
  headers.forEach((value, key) => {
    result[key] = value;
  });
  return result;
}

/**
 * Asserts that the current request is from a human user, not a bot.
 *
 * This function performs BotID verification and throws a BotDetectedError
 * if a bot is detected (unless it's a verified AI assistant and that
 * option is enabled).
 *
 * @param routeName - Name of the route being protected (for logging).
 * @param options - Configuration options.
 * @throws {BotDetectedError} If a bot is detected.
 *
 * @example
 * ```typescript
 * // In a route handler:
 * await assertHumanOrThrow("chat.stream", {
 *   allowVerifiedAiAssistants: true,
 * });
 * ```
 *
 * @see https://vercel.com/docs/botid/get-started
 */
export async function assertHumanOrThrow(
  routeName: string,
  options: AssertHumanOptions = {}
): Promise<void> {
  const { level = "basic", allowVerifiedAiAssistants = true, headers } = options;

  const result = await (async () => {
    try {
      return await checkBotId({
        advancedOptions: {
          checkLevel: level === "deep" ? "deepAnalysis" : "basic",
          headers:
            headers instanceof Headers
              ? toIncomingHttpHeaders(headers)
              : (headers ?? undefined),
        },
      });
    } catch (error) {
      botIdLogger.error("botid_service_error", { error, routeName });
      emitOperationalAlertOncePerWindow({
        attributes: { routeName },
        event: "botid.service_failure",
        severity: "error",
        windowMs: 60 * 60 * 1000, // 1h
      });
      throw error;
    }
  })();

  // Normalize the result to our interface (handle union type)
  const verification: BotIdVerification = {
    bypassed: result.bypassed,
    isBot: result.isBot,
    isHuman: result.isHuman,
    isVerifiedBot: result.isVerifiedBot,
    verifiedBotCategory:
      "verifiedBotCategory" in result ? result.verifiedBotCategory : undefined,
    verifiedBotName: "verifiedBotName" in result ? result.verifiedBotName : undefined,
  };

  if (verification.isBot) {
    // Allow verified AI assistants (ChatGPT, Perplexity, Claude, etc.)
    if (
      allowVerifiedAiAssistants &&
      verification.isVerifiedBot &&
      verification.verifiedBotCategory &&
      ALLOWED_VERIFIED_BOT_CATEGORIES.includes(
        verification.verifiedBotCategory as AllowedBotCategory
      )
    ) {
      botIdLogger.info("verified_ai_assistant_allowed", {
        routeName,
        verifiedBotCategory: verification.verifiedBotCategory,
        verifiedBotName: verification.verifiedBotName,
      });
      // Return without throwing - bot is allowed but still subject to rate limiting
      return;
    }

    // Log the bot detection event
    botIdLogger.warn("bot_detected", {
      isVerifiedBot: verification.isVerifiedBot,
      routeName,
      verifiedBotCategory: verification.verifiedBotCategory,
      verifiedBotName: verification.verifiedBotName,
    });

    throw new BotDetectedError(routeName, verification);
  }
}

/**
 * Response schema for bot detection errors (403 Forbidden).
 *
 * Used for consistent error responses across protected routes.
 */
export const BOT_DETECTED_RESPONSE = {
  error: "bot_detected",
  reason: "Automated access is not allowed.",
} as const;
