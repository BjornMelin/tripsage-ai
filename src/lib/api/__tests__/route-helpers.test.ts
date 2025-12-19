/** @vitest-environment node */

import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import {
  buildRateLimitKey,
  forbiddenResponse,
  getClientIpFromHeaders,
  notFoundResponse,
  parseJsonBody,
  parseNumericId,
  parseStringId,
  unauthorizedResponse,
} from "@/lib/api/route-helpers";
import { makeRequest } from "@/test/helpers/make-request";

describe("route-helpers", () => {
  describe("getClientIpFromHeaders", () => {
    it("prefers x-real-ip (Vercel's canonical IP header)", () => {
      const req = makeRequest({
        "x-forwarded-for": "203.0.113.10, 198.51.100.2",
        "x-real-ip": "198.51.100.5",
      });
      expect(getClientIpFromHeaders(req)).toBe("198.51.100.5");
    });

    it("falls back to first IP from x-forwarded-for when x-real-ip is absent", () => {
      const req = makeRequest({
        "x-forwarded-for": "203.0.113.10, 198.51.100.2",
      });
      expect(getClientIpFromHeaders(req)).toBe("203.0.113.10");
    });

    it("falls back to 'unknown' when no IP headers exist", () => {
      const req = makeRequest();
      expect(getClientIpFromHeaders(req)).toBe("unknown");
      expect(buildRateLimitKey(req)).toContain("unknown");
    });

    it("trims whitespace from x-real-ip", () => {
      const req = makeRequest({ "x-real-ip": "  192.168.1.1  " });
      expect(getClientIpFromHeaders(req)).toBe("192.168.1.1");
    });

    it("trims whitespace from x-forwarded-for entries", () => {
      const req = makeRequest({
        "x-forwarded-for": "  203.0.113.10  , 198.51.100.2",
      });
      expect(getClientIpFromHeaders(req)).toBe("203.0.113.10");
    });
  });

  describe("notFoundResponse", () => {
    it("returns 404 with correct error shape", async () => {
      const response = notFoundResponse("Trip");
      expect(response.status).toBe(404);

      const body = await response.json();
      expect(body).toEqual({
        error: "not_found",
        reason: "Trip not found",
      });
    });

    it("handles different entity names", async () => {
      const response = notFoundResponse("User");
      const body = await response.json();
      expect(body.reason).toBe("User not found");
    });
  });

  describe("unauthorizedResponse", () => {
    it("returns 401 with correct error shape", async () => {
      const response = unauthorizedResponse();
      expect(response.status).toBe(401);

      const body = await response.json();
      expect(body).toEqual({
        error: "unauthorized",
        reason: "Authentication required",
      });
    });
  });

  describe("forbiddenResponse", () => {
    it("returns 403 with correct error shape and custom reason", async () => {
      const response = forbiddenResponse("You do not have access to this resource");
      expect(response.status).toBe(403);

      const body = await response.json();
      expect(body).toEqual({
        error: "forbidden",
        reason: "You do not have access to this resource",
      });
    });

    it("handles different reasons", async () => {
      const response = forbiddenResponse("Admin privileges required");
      const body = await response.json();
      expect(body.reason).toBe("Admin privileges required");
    });
  });

  describe("parseJsonBody", () => {
    it("returns 413 and cancels stream when body exceeds maxBytes", async () => {
      let pulls = 0;
      let cancelled = false;

      const stream = new ReadableStream<Uint8Array>({
        cancel() {
          cancelled = true;
        },
        pull(controller) {
          pulls += 1;
          controller.enqueue(new TextEncoder().encode("aaaa"));
        },
      });

      const req = new NextRequest("https://example.com/api/test", {
        body: stream,
        // Required by Node's fetch when using a streaming request body.
        duplex: "half",
        headers: { "content-type": "application/json" },
        method: "POST",
      });

      const parsed = await parseJsonBody(req, { maxBytes: 10 });
      expect("error" in parsed).toBe(true);
      if ("error" in parsed) {
        expect(parsed.error.status).toBe(413);
        const body = await parsed.error.json();
        expect(body).toMatchObject({ error: "payload_too_large" });
      }

      expect(cancelled).toBe(true);
      expect(pulls).toBeLessThan(10);
    });

    it("returns 400 when request body has already been read", async () => {
      const json = JSON.stringify({ ok: true });
      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(json));
          controller.close();
        },
      });

      const req = new NextRequest("https://example.com/api/test", {
        body: stream,
        // Required by Node's fetch when using a streaming request body.
        duplex: "half",
        headers: { "content-type": "application/json" },
        method: "POST",
      });

      const first = await parseJsonBody(req);
      expect("body" in first).toBe(true);

      const second = await parseJsonBody(req);
      expect("error" in second).toBe(true);
      if ("error" in second) {
        expect(second.error.status).toBe(400);
        const body = await second.error.json();
        expect(body).toMatchObject({
          error: "invalid_request",
          reason: "Request body has already been read",
        });
      }
    });
  });

  describe("parseNumericId", () => {
    it("parses valid positive integer", async () => {
      const routeContext = {
        params: Promise.resolve({ id: "42" }),
      };
      const result = await parseNumericId(routeContext);
      expect("id" in result).toBe(true);
      if ("id" in result) {
        expect(result.id).toBe(42);
      }
    });

    it("returns error for non-numeric id", async () => {
      const routeContext = {
        params: Promise.resolve({ id: "abc" }),
      };
      const result = await parseNumericId(routeContext);
      expect("error" in result).toBe(true);
      if ("error" in result) {
        expect(result.error.status).toBe(400);
        const body = await result.error.json();
        expect(body.error).toBe("invalid_request");
        expect(body.reason).toContain("positive integer");
      }
    });

    it("returns error for zero", async () => {
      const routeContext = {
        params: Promise.resolve({ id: "0" }),
      };
      const result = await parseNumericId(routeContext);
      expect("error" in result).toBe(true);
    });

    it("returns error for negative number", async () => {
      const routeContext = {
        params: Promise.resolve({ id: "-5" }),
      };
      const result = await parseNumericId(routeContext);
      expect("error" in result).toBe(true);
    });

    it("handles custom param name", async () => {
      const routeContext = {
        params: Promise.resolve({ tripId: "123" }),
      };
      const result = await parseNumericId(routeContext, "tripId");
      expect("id" in result).toBe(true);
      if ("id" in result) {
        expect(result.id).toBe(123);
      }
    });
  });

  describe("parseStringId", () => {
    it("parses valid non-empty string", async () => {
      const routeContext = {
        params: Promise.resolve({ id: "abc-123" }),
      };
      const result = await parseStringId(routeContext);
      expect("id" in result).toBe(true);
      if ("id" in result) {
        expect(result.id).toBe("abc-123");
      }
    });

    it("trims whitespace", async () => {
      const routeContext = {
        params: Promise.resolve({ id: "  session-id  " }),
      };
      const result = await parseStringId(routeContext);
      expect("id" in result).toBe(true);
      if ("id" in result) {
        expect(result.id).toBe("session-id");
      }
    });

    it("returns error for empty string", async () => {
      const routeContext = {
        params: Promise.resolve({ id: "" }),
      };
      const result = await parseStringId(routeContext);
      expect("error" in result).toBe(true);
      if ("error" in result) {
        expect(result.error.status).toBe(400);
        const body = await result.error.json();
        expect(body.error).toBe("invalid_request");
        expect(body.reason).toContain("non-empty string");
      }
    });

    it("returns error for whitespace-only string", async () => {
      const routeContext = {
        params: Promise.resolve({ id: "   " }),
      };
      const result = await parseStringId(routeContext);
      expect("error" in result).toBe(true);
    });

    it("handles custom param name", async () => {
      const routeContext = {
        params: Promise.resolve({ sessionId: "sess-456" }),
      };
      const result = await parseStringId(routeContext, "sessionId");
      expect("id" in result).toBe(true);
      if ("id" in result) {
        expect(result.id).toBe("sess-456");
      }
    });

    it("includes param name in error message", async () => {
      const routeContext = {
        params: Promise.resolve({ sessionId: "" }),
      };
      const result = await parseStringId(routeContext, "sessionId");
      expect("error" in result).toBe(true);
      if ("error" in result) {
        const body = await result.error.json();
        expect(body.reason).toContain("sessionId");
      }
    });
  });
});
