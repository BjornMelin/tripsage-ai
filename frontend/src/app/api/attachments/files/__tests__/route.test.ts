/**
 * @fileoverview Unit tests for the attachment files API route.
 * Tests the GET endpoint for fetching attachment files with proper authentication
 * and pagination parameter forwarding.
 */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GET } from "../route";

// Mock global fetch
const MOCK_FETCH = vi.fn();
(globalThis as any).fetch = MOCK_FETCH;

describe("/api/attachments/files route (SSR, tagged)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MOCK_FETCH.mockResolvedValue(
      new Response(
        JSON.stringify({
          files: [{ filename: "test.pdf", id: "1" }],
          limit: 50,
          offset: 0,
          total: 1,
        }),
        { status: 200 }
      )
    );
  });

  it("forwards Authorization and sets next tags", async () => {
    const url = new URL("https://example.com/api/attachments/files?limit=10&offset=0");
    const req = {
      headers: {
        get: vi.fn((key) => (key === "authorization" ? "Bearer token" : null)),
      },
      nextUrl: url,
    } as unknown as NextRequest;

    const res = await GET(req);

    expect(res.status).toBe(200);
    expect(MOCK_FETCH).toHaveBeenCalledTimes(1);
    const [calledUrl, options] = MOCK_FETCH.mock.calls[0] as [
      string,
      RequestInit & { next?: any },
    ];
    expect(calledUrl).toContain("/api/attachments/files?limit=10&offset=0");
    expect(options?.method).toBe("GET");
    expect(options?.headers).toMatchObject({ Authorization: "Bearer token" });
    expect(options?.next?.tags).toContain("attachments");
  });
});
