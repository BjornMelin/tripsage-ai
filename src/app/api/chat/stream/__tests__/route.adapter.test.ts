/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRouteParamsContext,
  makeJsonRequest,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";

const HANDLE_CHAT_STREAM = vi.hoisted(() =>
  vi.fn(async (..._args: unknown[]) => new Response("ok"))
);

vi.mock("../_handler", () => ({
  handleChatStream: HANDLE_CHAT_STREAM,
}));

describe("/api/chat/stream route adapter", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: "user-1" });
    HANDLE_CHAT_STREAM.mockClear();
  });

  it("returns 401 unauthenticated", async () => {
    mockApiRouteAuthUser(null);
    const mod = await import("../route");

    const req = makeJsonRequest(
      "/api/chat/stream",
      { messages: [] },
      { headers: { "x-forwarded-for": "1.2.3.4" } }
    );
    const res = await mod.POST(req, createRouteParamsContext());

    expect(res.status).toBe(401);
    expect(HANDLE_CHAT_STREAM).not.toHaveBeenCalled();
  });

  it("parses body and forwards ip/messages to handleChatStream", async () => {
    const mod = await import("../route");

    const req = makeJsonRequest(
      "/api/chat/stream",
      { messages: [] },
      { headers: { "x-forwarded-for": "1.2.3.4" } }
    );
    const res = await mod.POST(req, createRouteParamsContext());

    expect(res.status).toBe(200);
    expect(HANDLE_CHAT_STREAM).toHaveBeenCalledTimes(1);
    const call = HANDLE_CHAT_STREAM.mock.calls[0];
    expect(call).toBeDefined();
    const payload = call?.[1];
    expect(payload).toMatchObject({ ip: "1.2.3.4", messages: [] });
  });
});
