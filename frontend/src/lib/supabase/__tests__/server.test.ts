import { createServerClient } from "@supabase/ssr";
import type { ReadonlyRequestCookies } from "next/dist/server/web/spec-extension/adapters/request-cookies";
import { cookies } from "next/headers";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TypedServerSupabase } from "../server";

// Import after mocking dependencies
let createServerSupabase: () => Promise<TypedServerSupabase>;

type MockCookieStore = {
  getAll: ReturnType<typeof vi.fn>;
  set: ReturnType<typeof vi.fn>;
};

// Mock modules
vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(),
}));

vi.mock("next/headers", () => ({
  cookies: vi.fn(),
}));

describe("Supabase Server Client", () => {
  const mockSupabaseUrl = "https://test.supabase.co";
  const mockSupabaseAnonKey = "test-anon-key";

  beforeEach(async () => {
    vi.resetAllMocks();
    vi.resetModules();

    // Set environment variables
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", mockSupabaseUrl);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", mockSupabaseAnonKey);

    // Dynamically import after setting env vars
    const serverModule = await import("../server");
    createServerSupabase = serverModule.createServerSupabase;
  });

  it("should create a server client with cookie handling", async () => {
    const mockCookies = [
      { name: "cookie1", value: "value1" },
      { name: "cookie2", value: "value2" },
    ];

    const mockCookieStore: MockCookieStore = {
      getAll: vi.fn().mockReturnValue(mockCookies),
      set: vi.fn(),
    };

    vi.mocked(cookies).mockResolvedValue(
      mockCookieStore as unknown as ReadonlyRequestCookies
    );

    const mockClient = { auth: {}, from: vi.fn() };
    vi.mocked(createServerClient).mockReturnValue(
      mockClient as unknown as TypedServerSupabase
    );

    const client = await createServerSupabase();

    expect(cookies).toHaveBeenCalled();
    expect(createServerClient).toHaveBeenCalledWith(
      mockSupabaseUrl,
      mockSupabaseAnonKey,
      expect.objectContaining({
        cookies: expect.objectContaining({
          getAll: expect.any(Function),
          setAll: expect.any(Function),
        }),
      })
    );
    expect(client).toBe(mockClient);
  });

  it("should properly handle cookie operations", async () => {
    const mockCookies = [{ name: "test", value: "value" }];
    type CookieHandlers = {
      getAll: () => typeof mockCookies;
      setAll: (
        cookies: Array<{
          name: string;
          value: string;
          options?: Record<string, unknown>;
        }>
      ) => void;
    };
    const mockCookieStore: MockCookieStore = {
      getAll: vi.fn().mockReturnValue(mockCookies),
      set: vi.fn(),
    };

    vi.mocked(cookies).mockResolvedValue(
      mockCookieStore as unknown as ReadonlyRequestCookies
    );

    let capturedCookieHandlers: CookieHandlers | null = null;
    vi.mocked(createServerClient).mockImplementation((_url, _key, options) => {
      const handlers = options.cookies as CookieHandlers;
      capturedCookieHandlers = handlers;
      return { auth: {} } as unknown as TypedServerSupabase;
    });

    await createServerSupabase();

    // Test getAll - TypeScript guard ensures capturedCookieHandlers is CookieHandlers here
    if (!capturedCookieHandlers) {
      throw new Error("Cookie handlers not captured");
    }
    const handlersForTest: CookieHandlers = capturedCookieHandlers;
    const getAllResult = handlersForTest.getAll();
    expect(mockCookieStore.getAll).toHaveBeenCalled();
    expect(getAllResult).toEqual(mockCookies);

    // Test setAll
    const cookiesToSet = [
      { name: "new1", options: { httpOnly: true }, value: "val1" },
      { name: "new2", options: { secure: true }, value: "val2" },
    ];
    handlersForTest.setAll(cookiesToSet);

    expect(mockCookieStore.set).toHaveBeenCalledTimes(2);
    expect(mockCookieStore.set).toHaveBeenCalledWith("new1", "val1", {
      httpOnly: true,
    });
    expect(mockCookieStore.set).toHaveBeenCalledWith("new2", "val2", { secure: true });
  });

  it("should throw an error when environment variables are missing", async () => {
    // Clear environment variables
    Reflect.deleteProperty(process.env, "NEXT_PUBLIC_SUPABASE_URL");
    Reflect.deleteProperty(process.env, "NEXT_PUBLIC_SUPABASE_ANON_KEY");

    // Re-import module with missing env vars
    vi.resetModules();
    const serverModule = await import("../server");
    createServerSupabase = serverModule.createServerSupabase;

    const mockCookieStore: MockCookieStore = {
      getAll: vi.fn().mockReturnValue([]),
      set: vi.fn(),
    };
    vi.mocked(cookies).mockResolvedValue(
      mockCookieStore as unknown as ReadonlyRequestCookies
    );

    await expect(createServerSupabase()).rejects.toThrow(
      /Environment validation failed|Missing Supabase environment variables/
    );
  });

  it("should handle empty cookie store", async () => {
    const mockCookieStore: MockCookieStore = {
      getAll: vi.fn().mockReturnValue([]),
      set: vi.fn(),
    };
    vi.mocked(cookies).mockResolvedValue(
      mockCookieStore as unknown as ReadonlyRequestCookies
    );

    const mockClient = { auth: {}, from: vi.fn() };
    vi.mocked(createServerClient).mockReturnValue(
      mockClient as unknown as TypedServerSupabase
    );

    const client = await createServerSupabase();

    expect(client).toBe(mockClient);
    expect(mockCookieStore.getAll).toHaveBeenCalled();
  });
});

afterEach(() => {
  vi.unstubAllEnvs();
});
