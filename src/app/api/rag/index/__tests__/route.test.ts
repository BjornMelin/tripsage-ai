/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRouteParamsContext,
  makeJsonRequest,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";
import { TEST_USER_ID } from "@/test/helpers/ids";

vi.mock("server-only", () => ({}));

const MOCK_HANDLE_RAG_INDEX = vi.hoisted(() => vi.fn());

vi.mock("../_handler", () => ({
  handleRagIndex: MOCK_HANDLE_RAG_INDEX,
}));

describe("/api/rag/index route", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: TEST_USER_ID });
    MOCK_HANDLE_RAG_INDEX.mockReset();
    MOCK_HANDLE_RAG_INDEX.mockResolvedValue(
      new Response(JSON.stringify({ indexed: 1, success: true }), {
        headers: { "content-type": "application/json" },
        status: 200,
      })
    );
  });

  it("accepts payloads above the default 64KB limit", async () => {
    const content = "a".repeat(100_000);

    const { POST } = await import("../route");
    const req = makeJsonRequest("/api/rag/index", {
      documents: [{ content }],
      namespace: "default",
    });

    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    expect(MOCK_HANDLE_RAG_INDEX).toHaveBeenCalled();
  });
});
