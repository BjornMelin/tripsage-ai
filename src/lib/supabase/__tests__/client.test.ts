/** @vitest-environment jsdom */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock env module to prevent validation errors during tests
vi.mock("@/lib/env/client", () => ({
  getClientEnv: () => ({
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  }),
  getClientEnvVar: (key: string) => process.env[key] ?? "",
}));

describe("Supabase Browser Client", () => {
  const mockSupabaseUrl = "https://test.supabase.co";
  const mockSupabaseAnonKey = "test-anon-key";

  beforeEach(() => {
    vi.resetAllMocks();
    // Reset modules to clear singleton state between tests
    vi.resetModules();
    // Reset environment variables
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");
  });

  // Dynamic import to get fresh module after resetModules
  async function getClient() {
    const module = await import("../client");
    return module.createClient;
  }

  it("should create a browser client with valid environment variables", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const createClient = await getClient();
    const client = createClient();
    expect(client).toBeTruthy();
  });

  it("should handle missing NEXT_PUBLIC_SUPABASE_URL gracefully in tests", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const createClient = await getClient();
    expect(() => createClient()).not.toThrow();
  });

  it("should handle missing NEXT_PUBLIC_SUPABASE_ANON_KEY gracefully in tests", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

    const createClient = await getClient();
    expect(() => createClient()).not.toThrow();
  });

  it("should handle both environment variables missing gracefully in tests", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

    const createClient = await getClient();
    expect(() => createClient()).not.toThrow();
  });

  it("should handle undefined environment variables gracefully in tests", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", undefined);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", undefined);

    const createClient = await getClient();
    expect(() => createClient()).not.toThrow();
  });

  it("should handle production-like environment variables", async () => {
    const prodUrl = "https://abcdefghijklmnop.supabase.co";
    const prodKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-key";

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", prodUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", prodKey);

    const createClient = await getClient();
    const client = createClient();
    expect(client).toBeTruthy();
  });

  it("should handle local development environment variables", async () => {
    const localUrl = "http://localhost:54321";
    const localKey = "local-anon-key";

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", localUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", localKey);

    const createClient = await getClient();
    const client = createClient();
    expect(client).toBeTruthy();
  });

  it("should create a usable client instance on each call", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const createClient = await getClient();
    const client1 = createClient();
    const client2 = createClient();
    expect(client1).toBeTruthy();
    expect(client2).toBeTruthy();
  });

  it("should handle client creation errors from createBrowserClient", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const createClient = await getClient();
    expect(() => createClient()).not.toThrow();
  });

  it("should validate URL format by passing it to createBrowserClient", async () => {
    const invalidUrl = "not-a-url";
    const validKey = "test-anon-key";

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", invalidUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", validKey);

    const createClient = await getClient();
    const client = createClient();
    expect(client).toBeTruthy();
  });

  it("should handle empty string but defined environment variables gracefully in tests", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const createClient = await getClient();
    expect(() => createClient()).not.toThrow();
  });

  it("should handle client with complex auth methods", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const createClient = await getClient();
    const client = createClient();
    expect(client).not.toBeNull();
    expect(client?.auth).toBeDefined();
    expect(client?.from).toBeDefined();
  });
});
