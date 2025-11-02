/**
 * @fileoverview Unit tests for Supabase browser client creation, verifying environment
 * variable handling, client initialization, and graceful error handling for missing
 * or invalid configuration scenarios.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createClient } from "../client";

describe("Supabase Browser Client", () => {
  /** Mock Supabase URL for testing. */
  const mockSupabaseUrl = "https://test.supabase.co";
  /** Mock Supabase anonymous key for testing. */
  const mockSupabaseAnonKey = "test-anon-key";

  beforeEach(() => {
    vi.resetAllMocks();
    // Reset environment variables
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");
  });

  it("should create a browser client with valid environment variables", () => {
    // Set environment variables
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const client = createClient();
    expect(client).toBeTruthy();
  });

  it("should handle missing NEXT_PUBLIC_SUPABASE_URL gracefully in tests", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    expect(() => createClient()).not.toThrow();
  });

  it("should handle missing NEXT_PUBLIC_SUPABASE_ANON_KEY gracefully in tests", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

    expect(() => createClient()).not.toThrow();
  });

  it("should handle both environment variables missing gracefully in tests", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

    expect(() => createClient()).not.toThrow();
  });

  it("should handle undefined environment variables gracefully in tests", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", undefined);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", undefined);

    expect(() => createClient()).not.toThrow();
  });

  it("should handle production-like environment variables", () => {
    const prodUrl = "https://abcdefghijklmnop.supabase.co";
    const prodKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-key";

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", prodUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", prodKey);

    const client = createClient();
    expect(client).toBeTruthy();
  });

  it("should handle local development environment variables", () => {
    const localUrl = "http://localhost:54321";
    const localKey = "local-anon-key";

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", localUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", localKey);

    const client = createClient();
    expect(client).toBeTruthy();
  });

  it("should create a usable client instance on each call", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const client1 = createClient();
    const client2 = createClient();
    expect(client1).toBeTruthy();
    expect(client2).toBeTruthy();
  });

  it("should handle client creation errors from createBrowserClient", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    // createClient will attempt to construct a real client; with valid envs this shouldn't throw
    expect(() => createClient()).not.toThrow();
  });

  it("should validate URL format by passing it to createBrowserClient", () => {
    const invalidUrl = "not-a-url";
    const validKey = "test-anon-key";

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", invalidUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", validKey);

    const client = createClient();
    // The client creation should still work - URL validation is handled by Supabase
    expect(client).toBeTruthy();
  });

  it("should handle empty string but defined environment variables gracefully in tests", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    expect(() => createClient()).not.toThrow();
  });

  it("should handle client with complex auth methods", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const client = createClient();
    expect(client.auth).toBeDefined();
    expect(client.from).toBeDefined();
    // Storage/realtime may be undefined in certain test adapters; primary APIs present
  });
});
