import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GET } from "../route";

// Mock global fetch
const MOCK_FETCH = vi.fn();
(globalThis as { fetch: typeof fetch }).fetch = MOCK_FETCH;

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
      RequestInit & { next?: { tags: string[] } },
    ];
    expect(calledUrl).toContain("/api/attachments/files?limit=10&offset=0");
    expect(options?.method).toBe("GET");
    expect(options?.headers).toMatchObject({ authorization: "Bearer token" });
    expect(options?.next?.tags).toContain("attachments");
  });
});
