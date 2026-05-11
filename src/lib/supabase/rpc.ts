/**
 * @fileoverview Supabase RPC wrappers for Vault and gateway user settings.
 */

import "server-only";

import { hashTelemetryIdentifier } from "@/lib/telemetry/identifiers";
import type { Span, TelemetrySpanAttributes } from "@/lib/telemetry/span";
import { recordErrorOnSpan, withTelemetrySpan } from "@/lib/telemetry/span";
import type { TypedAdminSupabase } from "./admin";
import { createAdminSupabase } from "./admin";

export type SupportedService =
  | "openai"
  | "openrouter"
  | "anthropic"
  | "xai"
  | "gateway";

type RpcOperation = "delete" | "gateway_config" | "get" | "health" | "insert" | "touch";

type RpcTelemetryResult<T> = { ok: true; value: T } | { error: Error; ok: false };

function normalizeService(service: string): SupportedService {
  const s = service.trim().toLowerCase();
  if (s === "openai" || s === "openrouter" || s === "anthropic" || s === "xai") {
    return s;
  }
  if (s === "gateway") return s;
  throw new Error(`Invalid service: ${service}`);
}

function toRpcError(error: unknown): Error {
  if (error instanceof Error) return error;
  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof error.message === "string"
  ) {
    const rpcError = new Error(error.message);
    Object.defineProperty(rpcError, "cause", {
      configurable: true,
      value: error,
    });
    const metadataKeys = new Set(["code", "details", "hint", "status"]);
    for (const [key, value] of Object.entries(error)) {
      if (metadataKeys.has(key)) {
        Object.defineProperty(rpcError, key, {
          configurable: true,
          enumerable: true,
          value,
        });
      }
    }
    return rpcError;
  }
  return new Error("Supabase RPC failed");
}

function buildRpcSpanAttributes(input: {
  operation: RpcOperation;
  rpcName: string;
  service?: string;
  userId?: string;
}): TelemetrySpanAttributes {
  const attributes: TelemetrySpanAttributes = {
    "keys.operation": input.operation,
    "rpc.name": input.rpcName,
    "rpc.system": "supabase",
  };

  if (input.service) {
    attributes["keys.service"] = input.service;
  }

  const userIdHash = input.userId ? hashTelemetryIdentifier(input.userId) : null;
  if (userIdHash) {
    attributes["keys.user_id_hash"] = userIdHash;
  }

  return attributes;
}

function sanitizedRpcSpanError(rpcName: string): Error {
  return new Error(`Supabase RPC ${rpcName} failed`);
}

async function runRpcWithTelemetry<T>(
  input: {
    operation: RpcOperation;
    rpcName: string;
    service?: string;
    userId?: string;
  },
  execute: (span: Span) => Promise<T>
): Promise<T> {
  const result = await withTelemetrySpan<RpcTelemetryResult<T>>(
    `supabase.rpc.${input.rpcName}`,
    { attributes: buildRpcSpanAttributes(input) },
    async (span) => {
      try {
        const value = await execute(span);
        span.setAttribute("rpc.error", false);
        return { ok: true, value };
      } catch (error) {
        span.setAttribute("rpc.error", true);
        recordErrorOnSpan(span, sanitizedRpcSpanError(input.rpcName));
        return { error: toRpcError(error), ok: false };
      }
    }
  );

  if (!result.ok) {
    throw result.error;
  }
  return result.value;
}

/**
 * Insert or replace a user's API key for a given provider using Vault RPC.
 *
 * @param userId The Supabase auth user id owning the key.
 * @param service Provider identifier (openai|openrouter|anthropic|xai).
 * @param apiKey Plaintext API key to store in Vault.
 * @param client Optional preconfigured admin Supabase client for testing.
 * @returns Resolves when the RPC succeeds.
 * @throws Error when RPC execution fails or service is invalid.
 */
export async function insertUserApiKey(
  userId: string,
  service: string,
  apiKey: string,
  client?: TypedAdminSupabase
): Promise<void> {
  const svc = normalizeService(service);
  const supabase = client ?? createAdminSupabase();
  await runRpcWithTelemetry(
    { operation: "insert", rpcName: "insert_user_api_key", service: svc, userId },
    async () => {
      const { error } = await supabase.rpc("insert_user_api_key", {
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_api_key: apiKey,
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_service: svc,
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_user_id: userId,
      });
      if (error) throw error;
    }
  );
}

/**
 * Verify Supabase Vault decrypted-secret access through a service-role RPC.
 *
 * @param client Optional preconfigured admin Supabase client for testing.
 * @returns Resolves when Vault metadata can be queried without exposing secrets.
 * @throws Error when the health RPC fails or returns an unexpected result.
 */
export async function checkByokVaultHealth(client?: TypedAdminSupabase): Promise<void> {
  const supabase = client ?? createAdminSupabase();
  await runRpcWithTelemetry(
    { operation: "health", rpcName: "check_byok_vault_health", service: "vault" },
    async () => {
      const { data, error } = await supabase.rpc("check_byok_vault_health");
      if (error) throw error;
      if (data !== true) {
        throw new Error("BYOK Vault health RPC returned an unexpected result");
      }
    }
  );
}

/**
 * Delete a user's API key for a given provider and remove its Vault secret.
 *
 * @param userId The Supabase auth user id owning the key.
 * @param service Provider identifier (openai|openrouter|anthropic|xai).
 * @param client Optional preconfigured admin Supabase client for testing.
 * @returns Resolves when the RPC succeeds.
 * @throws Error when RPC execution fails or service is invalid.
 */
export async function deleteUserApiKey(
  userId: string,
  service: string,
  client?: TypedAdminSupabase
): Promise<void> {
  const svc = normalizeService(service);
  const supabase = client ?? createAdminSupabase();
  await runRpcWithTelemetry(
    { operation: "delete", rpcName: "delete_user_api_key", service: svc, userId },
    async () => {
      const { error } = await supabase.rpc("delete_user_api_key", {
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_service: svc,
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_user_id: userId,
      });
      if (error) throw error;
    }
  );
}

/**
 * Retrieve a user's API key plaintext from Vault for the given provider.
 *
 * Note: Only use server-side and avoid logging the returned value.
 *
 * @param userId The Supabase auth user id owning the key.
 * @param service Provider identifier (openai|openrouter|anthropic|xai).
 * @param client Optional preconfigured admin Supabase client for testing.
 * @returns The plaintext API key or null if not found.
 * @throws Error when RPC execution fails or service is invalid.
 */
export async function getUserApiKey(
  userId: string,
  service: string,
  client?: TypedAdminSupabase
): Promise<string | null> {
  const svc = normalizeService(service);
  const supabase = client ?? createAdminSupabase();
  return await runRpcWithTelemetry(
    { operation: "get", rpcName: "get_user_api_key", service: svc, userId },
    async () => {
      const { data, error } = await supabase.rpc("get_user_api_key", {
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_service: svc,
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_user_id: userId,
      });
      if (error) throw error;
      return typeof data === "string" ? data : null;
    }
  );
}

/**
 * Update `last_used` timestamp for a user's API key metadata.
 *
 * @param userId The Supabase auth user id owning the key.
 * @param service Provider identifier (openai|openrouter|anthropic|xai).
 * @param client Optional preconfigured admin Supabase client for testing.
 * @returns Resolves when the RPC succeeds.
 * @throws Error when RPC execution fails or service is invalid.
 */
export async function touchUserApiKey(
  userId: string,
  service: string,
  client?: TypedAdminSupabase
): Promise<void> {
  const svc = normalizeService(service);
  const supabase = client ?? createAdminSupabase();
  await runRpcWithTelemetry(
    { operation: "touch", rpcName: "touch_user_api_key", service: svc, userId },
    async () => {
      const { error } = await supabase.rpc("touch_user_api_key", {
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_service: svc,
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_user_id: userId,
      });
      if (error) throw error;
    }
  );
}

/** Gateway config (base URL) helpers **/

export async function upsertUserGatewayBaseUrl(
  userId: string,
  baseUrl: string,
  client?: TypedAdminSupabase
): Promise<void> {
  const supabase = client ?? createAdminSupabase();
  await runRpcWithTelemetry(
    {
      operation: "gateway_config",
      rpcName: "upsert_user_gateway_config",
      service: "gateway",
      userId,
    },
    async () => {
      const { error } = await supabase.rpc("upsert_user_gateway_config", {
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_base_url: baseUrl,
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_user_id: userId,
      });
      if (error) throw error;
    }
  );
}

export async function getUserGatewayBaseUrl(
  userId: string,
  client?: TypedAdminSupabase
): Promise<string | null> {
  const supabase = client ?? createAdminSupabase();
  return await runRpcWithTelemetry(
    {
      operation: "gateway_config",
      rpcName: "get_user_gateway_base_url",
      service: "gateway",
      userId,
    },
    async () => {
      const { data, error } = await supabase.rpc("get_user_gateway_base_url", {
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_user_id: userId,
      });
      if (error) throw error;
      return typeof data === "string" ? data : null;
    }
  );
}

export async function deleteUserGatewayBaseUrl(
  userId: string,
  client?: TypedAdminSupabase
): Promise<void> {
  const supabase = client ?? createAdminSupabase();
  await runRpcWithTelemetry(
    {
      operation: "gateway_config",
      rpcName: "delete_user_gateway_config",
      service: "gateway",
      userId,
    },
    async () => {
      const { error } = await supabase.rpc("delete_user_gateway_config", {
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_user_id: userId,
      });
      if (error) throw error;
    }
  );
}

export async function getUserAllowGatewayFallback(
  userId: string,
  client?: TypedAdminSupabase
): Promise<boolean | null> {
  const supabase = client ?? createAdminSupabase();
  return await runRpcWithTelemetry(
    {
      operation: "gateway_config",
      rpcName: "get_user_allow_gateway_fallback",
      service: "gateway",
      userId,
    },
    async () => {
      const { data, error } = await supabase.rpc("get_user_allow_gateway_fallback", {
        // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
        p_user_id: userId,
      });
      if (error) throw error;
      return typeof data === "boolean" ? data : null;
    }
  );
}
