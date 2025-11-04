/**
 * @fileoverview Typed wrappers for Supabase Vault RPCs used by BYOK routes.
 */
import "server-only";

import type { TypedAdminSupabase } from "./admin";
import { createAdminSupabase } from "./admin";

export type SupportedService = "openai" | "openrouter" | "anthropic" | "xai";

/**
 * Type helper for Supabase RPC calls with proper typing.
 * Supabase RPC types are not fully generated, so we use a minimal type assertion.
 */
type SupabaseRpcClient = {
  rpc: (
    name: string,
    params: Record<string, unknown>
  ) => Promise<{ data?: unknown; error: unknown | null }>;
};

function normalizeService(service: string): SupportedService {
  const s = service.trim().toLowerCase();
  if (s === "openai" || s === "openrouter" || s === "anthropic" || s === "xai") {
    return s;
  }
  throw new Error(`Invalid service: ${service}`);
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
  const { error } = await (supabase as unknown as SupabaseRpcClient).rpc(
    "insert_user_api_key",
    {
      // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
      p_api_key: apiKey,
      // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
      p_service: svc,
      // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
      p_user_id: userId,
    }
  );
  if (error) throw error;
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
  const { error } = await (supabase as unknown as SupabaseRpcClient).rpc(
    "delete_user_api_key",
    {
      // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
      p_service: svc,
      // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
      p_user_id: userId,
    }
  );
  if (error) throw error;
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
  const { data, error } = await (supabase as unknown as SupabaseRpcClient).rpc(
    "get_user_api_key",
    {
      // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
      p_service: svc,
      // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
      p_user_id: userId,
    }
  );
  if (error) throw error;
  return typeof data === "string" ? data : null;
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
  const { error } = await (supabase as unknown as SupabaseRpcClient).rpc(
    "touch_user_api_key",
    {
      // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
      p_service: svc,
      // biome-ignore lint/style/useNamingConvention: Database RPC parameter names use snake_case
      p_user_id: userId,
    }
  );
  if (error) throw error;
}
