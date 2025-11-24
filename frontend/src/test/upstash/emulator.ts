/**
 * @fileoverview Optional Upstash emulator harness.
 *
 * For now this is a stub that simply checks required env vars and returns
 * connection info. Tests can opt-in by setting `UPSTASH_USE_EMULATOR=1` and
 * providing URLs/tokens. If env is missing, callers should skip gracefully.
 */

/** Emulator configuration. */
export type UpstashEmulatorConfig = {
  redisUrl: string;
  redisToken: string;
  qstashUrl?: string;
  qstashToken?: string;
};

/**
 * Loads emulator configuration from environment variables.
 *
 * @returns Emulator configuration or null if emulator is not enabled.
 */
export function loadEmulatorConfig(): UpstashEmulatorConfig | null {
  if (process.env.UPSTASH_USE_EMULATOR !== "1") return null;
  const redisUrl = process.env.UPSTASH_EMULATOR_URL;
  const redisToken = process.env.UPSTASH_EMULATOR_TOKEN;
  if (!redisUrl || !redisToken) return null;
  return {
    qstashToken: process.env.UPSTASH_QSTASH_DEV_TOKEN,
    qstashUrl: process.env.UPSTASH_QSTASH_DEV_URL,
    redisToken,
    redisUrl,
  };
}
