import { createServerClient } from "@supabase/ssr";
import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { updateSession } from "../../../middleware";

// Mock Supabase SSR
vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(),
}));

// Helper function to create a properly mocked NextRequest
function createMockNextRequest(url: string, headers: Record<string, string> = {}) {
  const request = {
    url,
    nextUrl: new URL(url),
    headers: new Headers(headers),
    cookies: {
      getAll: vi.fn().mockReturnValue([]),
      set: vi.fn(),
    },
  } as any;

  return request as NextRequest;
}

describe("updateSession", () => {
  let mockRequest: NextRequest;
  let mockSupabase: any;

  beforeEach(() => {
    vi.clearAllMocks();

    // Set up environment variables
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://test.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-anon-key";

    // Mock request
    mockRequest = createMockNextRequest("http://localhost:3000/dashboard");

    // Mock Supabase client
    mockSupabase = {
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: "user123" } },
          error: null,
        }),
      },
    };

    vi.mocked(createServerClient).mockReturnValue(mockSupabase);
  });

  it("should refresh Supabase session and return response", async () => {
    const response = await updateSession(mockRequest);

    expect(createServerClient).toHaveBeenCalledWith(
      "https://test.supabase.co",
      "test-anon-key",
      expect.objectContaining({
        cookies: expect.any(Object),
      })
    );
    expect(mockSupabase.auth.getUser).toHaveBeenCalled();
    expect(response).toBeDefined();
  });

  it("should handle auth errors gracefully", async () => {
    mockSupabase.auth.getUser.mockRejectedValue(new Error("Auth error"));

    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    const response = await updateSession(mockRequest);

    expect(response).toBeDefined();
    expect(consoleSpy).toHaveBeenCalledWith("Supabase auth error:", expect.any(Error));

    consoleSpy.mockRestore();
  });

  it("should handle missing environment variables", async () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = undefined;
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = undefined;

    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    const response = await updateSession(mockRequest);

    expect(response).toBeDefined();
    expect(consoleSpy).toHaveBeenCalledWith("Missing Supabase environment variables");
    expect(createServerClient).not.toHaveBeenCalled();

    consoleSpy.mockRestore();

    // Restore env vars
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://test.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-anon-key";
  });

  it("should handle cookie operations", async () => {
    const mockCookies = [
      { name: "sb-auth-token", value: "token123" },
      { name: "sb-refresh-token", value: "refresh123" },
    ];

    // Mock request cookies
    Object.defineProperty(mockRequest, "cookies", {
      value: {
        getAll: vi.fn().mockReturnValue(mockCookies),
        set: vi.fn(),
      },
      writable: true,
    });

    let capturedCookieHandlers: any = null;
    vi.mocked(createServerClient).mockImplementation((url, key, options) => {
      capturedCookieHandlers = options.cookies;
      return mockSupabase;
    });

    await updateSession(mockRequest);

    expect(capturedCookieHandlers).toBeDefined();
    expect(capturedCookieHandlers.getAll()).toEqual(mockCookies);
  });
});
