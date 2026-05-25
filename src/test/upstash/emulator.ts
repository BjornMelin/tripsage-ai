/**
 * @fileoverview Optional Upstash emulator helpers.
 *
 * Reads and validates Upstash emulator config from env vars. No-op unless
 * UPSTASH_USE_EMULATOR=1. When enabled, point the runtime Redis env
 * (UPSTASH_REDIS_REST_URL) at the emulator. QStash dev server still uses
 * UPSTASH_QSTASH_DEV_URL
 * because production QStash publishes through the managed service endpoint.
 */

type EmulatorConfig = {
  enabled: boolean;
  redisUrl?: string;
  qstashUrl?: string;
};

export function getEmulatorConfig(): EmulatorConfig {
  const enabled = process.env.UPSTASH_USE_EMULATOR === "1";
  return {
    enabled,
    qstashUrl: process.env.UPSTASH_QSTASH_DEV_URL,
    redisUrl: process.env.UPSTASH_REDIS_REST_URL,
  };
}

export function startUpstashEmulators(): EmulatorConfig {
  const config = getEmulatorConfig();
  if (!config.enabled) return config;

  if (!config.redisUrl) {
    throw new Error(
      "UPSTASH_USE_EMULATOR=1 but UPSTASH_REDIS_REST_URL is not set; provide the Redis REST emulator URL"
    );
  }

  if (!config.qstashUrl) {
    throw new Error(
      "UPSTASH_USE_EMULATOR=1 but UPSTASH_QSTASH_DEV_URL is not set; provide http://host:port"
    );
  }

  // Real container orchestration is handled externally or by CI; this helper
  // simply validates configuration to avoid silent misconfigurations.
  return config;
}

export function stopUpstashEmulators(): void {
  // No-op placeholder for symmetry; actual emulator lifecycle is managed
  // externally (docker-compose/testcontainers) when enabled.
}
