/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { resetApiRouteMocks } from "@/test/helpers/api-route";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";
import { GET as MSG_GET, POST as MSG_POST } from "../[id]/messages/route";
import { DELETE as SESS_ID_DELETE, GET as SESS_ID_GET } from "../[id]/route";
import { GET as SESS_GET, POST as SESS_POST } from "../route";

vi.mock("server-only", () => ({}));

vi.mock("@/lib/telemetry/span", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/telemetry/span")>();
  const spanMock = {
    addEvent: vi.fn(),
    end: vi.fn(),
    recordException: vi.fn(),
    setAttribute: vi.fn(),
    setStatus: vi.fn(),
  };
  return {
    ...actual,
    recordTelemetryEvent: vi.fn(),
    sanitizeAttributes: vi.fn((attrs) => attrs),
    withTelemetrySpan: vi.fn((_name, _attrs, fn) => fn(spanMock)),
  };
});

describe("/api/chat/sessions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetApiRouteMocks();
  });
  it("creates and lists sessions", async () => {
    const resCreate = await SESS_POST(
      createMockNextRequest({
        body: { title: "Trip" },
        method: "POST",
        url: "http://x/sessions",
      }),
      createRouteParamsContext()
    );
    expect(resCreate.status).toBe(201);
    const { id } = (await resCreate.json()) as { id: string };
    expect(typeof id).toBe("string");

    const resList = await SESS_GET(
      createMockNextRequest({
        method: "GET",
        url: "http://x/sessions",
      }),
      createRouteParamsContext()
    );
    expect(resList.status).toBe(200);
    const list = (await resList.json()) as Array<{ id: string }>;
    expect(list.length).toBe(1);
    expect(list[0].id).toBe(id);
  });

  it("gets and deletes a session", async () => {
    // create
    const resCreate = await SESS_POST(
      createMockNextRequest({
        body: {},
        method: "POST",
        url: "http://x/sessions",
      }),
      createRouteParamsContext()
    );
    const { id } = (await resCreate.json()) as { id: string };
    // get
    const resGet = await SESS_ID_GET(
      createMockNextRequest({
        method: "GET",
        url: "http://x/",
      }),
      {
        params: Promise.resolve({ id }),
      }
    );
    expect(resGet.status).toBe(200);
    // delete
    const resDel = await SESS_ID_DELETE(
      createMockNextRequest({
        method: "DELETE",
        url: "http://x/",
      }),
      {
        params: Promise.resolve({ id }),
      }
    );
    expect(resDel.status).toBe(204);
  });

  it("creates and lists messages for a session", async () => {
    // create session
    const resCreate = await SESS_POST(
      createMockNextRequest({
        body: {},
        method: "POST",
        url: "http://x/sessions",
      }),
      createRouteParamsContext()
    );
    const { id } = (await resCreate.json()) as { id: string };

    // post message
    const resMsg = await MSG_POST(
      createMockNextRequest({
        body: {
          content: "hi",
          role: "user",
        },
        method: "POST",
        url: `http://x/sessions/${id}/messages`,
      }),
      {
        params: Promise.resolve({ id }),
      }
    );
    expect(resMsg.status).toBe(201);

    // list messages
    const resList = await MSG_GET(
      createMockNextRequest({
        method: "GET",
        url: "http://x/",
      }),
      {
        params: Promise.resolve({ id }),
      }
    );
    expect(resList.status).toBe(200);
    const msgs = (await resList.json()) as Array<unknown>;
    expect(Array.isArray(msgs)).toBe(true);
  });

  describe("POST /api/chat/sessions/[id]/messages validation", () => {
    it("rejects empty content", async () => {
      const resCreate = await SESS_POST(
        createMockNextRequest({
          body: {},
          method: "POST",
          url: "http://x/sessions",
        }),
        createRouteParamsContext()
      );
      const { id } = (await resCreate.json()) as { id: string };

      const resMsg = await MSG_POST(
        createMockNextRequest({
          body: {
            content: "",
            role: "user",
          },
          method: "POST",
          url: `http://x/sessions/${id}/messages`,
        }),
        {
          params: Promise.resolve({ id }),
        }
      );
      expect(resMsg.status).toBe(400);
      const error = (await resMsg.json()) as { error: string; reason: string };
      expect(error.error).toBe("invalid_request");
      expect(error.reason).toBe("Request validation failed");
    });

    it("rejects missing content", async () => {
      const resCreate = await SESS_POST(
        createMockNextRequest({
          body: {},
          method: "POST",
          url: "http://x/sessions",
        }),
        createRouteParamsContext()
      );
      const { id } = (await resCreate.json()) as { id: string };

      const resMsg = await MSG_POST(
        createMockNextRequest({
          body: {
            role: "user",
          },
          method: "POST",
          url: `http://x/sessions/${id}/messages`,
        }),
        {
          params: Promise.resolve({ id }),
        }
      );
      expect(resMsg.status).toBe(400);
      const error = (await resMsg.json()) as { error: string; reason: string };
      expect(error.error).toBe("invalid_request");
      expect(error.reason).toBe("Request validation failed");
    });

    it("rejects invalid role", async () => {
      const resCreate = await SESS_POST(
        createMockNextRequest({
          body: {},
          method: "POST",
          url: "http://x/sessions",
        }),
        createRouteParamsContext()
      );
      const { id } = (await resCreate.json()) as { id: string };

      const resMsg = await MSG_POST(
        createMockNextRequest({
          body: {
            content: "test message",
            role: "invalid-role",
          },
          method: "POST",
          url: `http://x/sessions/${id}/messages`,
        }),
        {
          params: Promise.resolve({ id }),
        }
      );
      expect(resMsg.status).toBe(400);
      const error = (await resMsg.json()) as { error: string; reason: string };
      expect(error.error).toBe("invalid_request");
      expect(error.reason).toBe("Request validation failed");
    });

    it("accepts valid request with content and role", async () => {
      const resCreate = await SESS_POST(
        createMockNextRequest({
          body: {},
          method: "POST",
          url: "http://x/sessions",
        }),
        createRouteParamsContext()
      );
      const { id } = (await resCreate.json()) as { id: string };

      const resMsg = await MSG_POST(
        createMockNextRequest({
          body: {
            content: "test message",
            role: "user",
          },
          method: "POST",
          url: `http://x/sessions/${id}/messages`,
        }),
        {
          params: Promise.resolve({ id }),
        }
      );
      expect(resMsg.status).toBe(201);
    });

    it("validation passes for content without role, but handler requires role", async () => {
      const resCreate = await SESS_POST(
        createMockNextRequest({
          body: {},
          method: "POST",
          url: "http://x/sessions",
        }),
        createRouteParamsContext()
      );
      const { id } = (await resCreate.json()) as { id: string };

      const resMsg = await MSG_POST(
        createMockNextRequest({
          body: {
            content: "test message",
          },
          method: "POST",
          url: `http://x/sessions/${id}/messages`,
        }),
        {
          params: Promise.resolve({ id }),
        }
      );
      // Schema validation passes (role is optional), but handler enforces role requirement
      expect(resMsg.status).toBe(400);
      const error = (await resMsg.json()) as { error: string; reason: string };
      expect(error.error).toBe("bad_request");
      expect(error.reason).toBe("Role is required");
    });
  });
});
