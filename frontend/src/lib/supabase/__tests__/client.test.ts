import { createBrowserClient } from "@supabase/ssr";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createClient } from "../client";

// Mock the @supabase/ssr module
vi.mock("@supabase/ssr", () => ({
  createBrowserClient: vi.fn(),
}));

describe("Supabase Browser Client", () => {
  const mockSupabaseUrl = "https://test.supabase.co";
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

    const mockClient = { auth: {}, from: vi.fn() };
    vi.mocked(createBrowserClient).mockReturnValue(mockClient as any);

    const client = createClient();

    expect(createBrowserClient).toHaveBeenCalledWith(
      mockSupabaseUrl,
      mockSupabaseAnonKey
    );
    expect(client).toBe(mockClient);
  });

  it("should throw an error when NEXT_PUBLIC_SUPABASE_URL is missing", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    expect(() => createClient()).toThrow(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );

    expect(createBrowserClient).not.toHaveBeenCalled();
  });

  it("should throw an error when NEXT_PUBLIC_SUPABASE_ANON_KEY is missing", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

    expect(() => createClient()).toThrow(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );

    expect(createBrowserClient).not.toHaveBeenCalled();
  });

  it("should throw an error when both environment variables are missing", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

    expect(() => createClient()).toThrow(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );

    expect(createBrowserClient).not.toHaveBeenCalled();
  });

  it("should throw error when environment variables are undefined", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", undefined);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", undefined);

    expect(() => createClient()).toThrow(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );

    expect(createBrowserClient).not.toHaveBeenCalled();
  });

  it("should handle production-like environment variables", () => {
    const prodUrl = "https://abcdefghijklmnop.supabase.co";
    const prodKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-key";

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", prodUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", prodKey);

    const mockClient = { auth: {}, from: vi.fn() };
    vi.mocked(createBrowserClient).mockReturnValue(mockClient as any);

    const client = createClient();

    expect(createBrowserClient).toHaveBeenCalledWith(prodUrl, prodKey);
    expect(client).toBe(mockClient);
  });

  it("should handle local development environment variables", () => {
    const localUrl = "http://localhost:54321";
    const localKey = "local-anon-key";

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", localUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", localKey);

    const mockClient = { auth: {}, from: vi.fn() };
    vi.mocked(createBrowserClient).mockReturnValue(mockClient as any);

    const client = createClient();

    expect(createBrowserClient).toHaveBeenCalledWith(localUrl, localKey);
    expect(client).toBe(mockClient);
  });

  it("should create new client instance on each call", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const mockClient1 = { auth: {}, from: vi.fn(), id: 1 };
    const mockClient2 = { auth: {}, from: vi.fn(), id: 2 };

    vi.mocked(createBrowserClient)
      .mockReturnValueOnce(mockClient1 as any)
      .mockReturnValueOnce(mockClient2 as any);

    const client1 = createClient();
    const client2 = createClient();

    expect(createBrowserClient).toHaveBeenCalledTimes(2);
    expect(client1).toBe(mockClient1);
    expect(client2).toBe(mockClient2);
  });

  it("should handle client creation errors from createBrowserClient", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const error = new Error("Failed to create Supabase client");
    vi.mocked(createBrowserClient).mockImplementation(() => {
      throw error;
    });

    expect(() => createClient()).toThrow("Failed to create Supabase client");
  });

  it("should validate URL format by passing it to createBrowserClient", () => {
    const invalidUrl = "not-a-url";
    const validKey = "test-anon-key";

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", invalidUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", validKey);

    const mockClient = { auth: {}, from: vi.fn() };
    vi.mocked(createBrowserClient).mockReturnValue(mockClient as any);

    const client = createClient();

    // The client creation should still work - URL validation is handled by Supabase
    expect(createBrowserClient).toHaveBeenCalledWith(invalidUrl, validKey);
    expect(client).toBe(mockClient);
  });

  it("should handle empty string but defined environment variables", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    expect(() => createClient()).toThrow(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );
  });

  it("should handle client with complex auth methods", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    const mockAuth = {
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      getUser: vi.fn(),
      onAuthStateChange: vi.fn(),
    };
    const mockClient = {
      auth: mockAuth,
      from: vi.fn(),
      storage: { from: vi.fn() },
      realtime: { channel: vi.fn() },
    };
    vi.mocked(createBrowserClient).mockReturnValue(mockClient as any);

    const client = createClient();

    expect(client.auth).toBe(mockAuth);
    expect(client.from).toBeDefined();
    expect(client.storage).toBeDefined();
    expect(client.realtime).toBeDefined();
  });
});
