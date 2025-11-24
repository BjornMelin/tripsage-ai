/**
 * @fileoverview Optional Upstash emulator helpers.
 *
 * Reads and validates Upstash emulator config from env vars. No-op unless
 * UPSTASH_USE_EMULATOR=1. When enabled, requires UPSTASH_EMULATOR_URL and
 * UPSTASH_QSTASH_DEV_URL to be set; throws if missing.
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
    redisUrl: process.env.UPSTASH_EMULATOR_URL,
  };
}

export function startUpstashEmulators(): EmulatorConfig {
  const config = getEmulatorConfig();
  if (!config.enabled) return config;

  if (!config.redisUrl) {
    throw new Error(
      "UPSTASH_USE_EMULATOR=1 but UPSTASH_EMULATOR_URL is not set; provide http://host:port"
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
