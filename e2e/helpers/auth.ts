import type { Page } from "@playwright/test";

const DEFAULT_SUPABASE_URL = "http://127.0.0.1:54329";

function getSupabaseBaseUrl(): URL {
  return new URL(process.env.NEXT_PUBLIC_SUPABASE_URL ?? DEFAULT_SUPABASE_URL);
}

function getSupabaseAuthCookieName(): string {
  const hostnamePrefix = getSupabaseBaseUrl().hostname.split(".")[0] || "local";
  // Matches @supabase/ssr default cookie naming: `sb-${projectRef}-auth-token`,
  // where `projectRef` is derived from the Supabase URL hostname prefix.
  if (!/^[a-z0-9-]+$/i.test(hostnamePrefix) || hostnamePrefix.length > 32) {
    throw new Error(
      `Unsupported Supabase hostname prefix for auth cookie name: ${hostnamePrefix}`
    );
  }
  return `sb-${hostnamePrefix}-auth-token`;
}

export async function resetTestAuth(page: Page): Promise<void> {
  await page.context().clearCookies();
}

export async function authenticateAsTestUser(page: Page): Promise<void> {
  const nowSeconds = Math.floor(Date.now() / 1000);
  const nowIso = new Date(nowSeconds * 1000).toISOString();

  const session = {
    // biome-ignore lint/style/useNamingConvention: Supabase session payload uses snake_case
    access_token: "e2e-access-token",
    // biome-ignore lint/style/useNamingConvention: Supabase session payload uses snake_case
    expires_at: nowSeconds + 3600,
    // biome-ignore lint/style/useNamingConvention: Supabase session payload uses snake_case
    expires_in: 3600,
    // biome-ignore lint/style/useNamingConvention: Supabase session payload uses snake_case
    refresh_token: "e2e-refresh-token",
    // biome-ignore lint/style/useNamingConvention: Supabase session payload uses snake_case
    token_type: "bearer",
    user: {
      // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
      app_metadata: {},
      aud: "authenticated",
      // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
      created_at: nowIso,
      email: "test@example.com",
      // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
      email_confirmed_at: nowIso,
      id: "00000000-0000-0000-0000-000000000000",
      role: "authenticated",
      // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
      updated_at: nowIso,
      // biome-ignore lint/style/useNamingConvention: Supabase user payload uses snake_case
      user_metadata: { full_name: "Test User" },
    },
  };

  const encoded = Buffer.from(JSON.stringify(session), "utf8").toString("base64url");
  const value = `base64-${encoded}`;

  const e2ePort = Number.parseInt(process.env.E2E_PORT ?? "3100", 10);
  const baseUrl = `http://localhost:${e2ePort}`;

  await page.context().addCookies([
    {
      // Allow the browser client (createBrowserClient from @supabase/ssr) to read the
      // auth cookie during E2E runs so client hooks (useCurrentUserId) can enable
      // private React Query keys without relying on a real auth flow.
      httpOnly: false,
      name: getSupabaseAuthCookieName(),
      sameSite: "Lax",
      secure: false,
      url: baseUrl,
      value,
    },
  ]);
}
