/**
 * @fileoverview Shared BotID mock helpers for deterministic test behavior.
 *
 * Route tests commonly stub `botid/server` to avoid noisy warnings and to keep
 * bot-detection behavior consistent across suites.
 */

import type { BotIdVerification } from "@/lib/security/botid";

/**
 * Deterministic "human" BotID response used across tests.
 *
 * Matches the shape used by `createMockBotIdResponse` in `src/lib/security/__tests__/botid.test.ts`.
 */
export const mockBotIdHumanResponse: BotIdVerification = {
  bypassed: true,
  isBot: false,
  isHuman: true,
  isVerifiedBot: false,
  verifiedBotCategory: undefined,
  verifiedBotName: undefined,
};
