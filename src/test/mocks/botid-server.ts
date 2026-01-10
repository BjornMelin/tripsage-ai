/**
 * @fileoverview Test mock for `botid/server`.
 *
 * BotID is Vercel-only and depends on request context and OIDC in production.
 * In unit/integration tests we default to a deterministic "human" response.
 */

export function checkBotId(): Promise<{
  bypassed: boolean;
  isBot: boolean;
  isHuman: boolean;
  isVerifiedBot: boolean;
  verifiedBotCategory?: string;
  verifiedBotName?: string;
}> {
  return Promise.resolve({
    bypassed: false,
    isBot: false,
    isHuman: true,
    isVerifiedBot: false,
    verifiedBotCategory: undefined,
    verifiedBotName: undefined,
  });
}
