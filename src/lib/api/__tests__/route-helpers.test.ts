/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import {
  buildRateLimitKey,
  forbiddenResponse,
  getClientIpFromHeaders,
  notFoundResponse,
  parseNumericId,
  parseStringId,
  unauthorizedResponse,
} from "@/lib/api/route-helpers";

describe("route-helpers", () => {
  describe("getClientIpFromHeaders", () => {
    it("prefers x-real-ip (Vercel's canonical IP header)", () => {
      const req = {
        headers: new Headers({
          "x-forwarded-for": "203.0.113.10, 198.51.100.2",
          "x-real-ip": "198.51.100.5",
        }),
      } as unknown as NextRequest;
      expect(getClientIpFromHeaders(req)).toBe("198.51.100.5");
    });

    it("falls back to first IP from x-forwarded-for when x-real-ip is absent", () => {
      const req = {
        headers: new Headers({
          "x-forwarded-for": "203.0.113.10, 198.51.100.2",
        }),
      } as unknown as NextRequest;
      expect(getClientIpFromHeaders(req)).toBe("203.0.113.10");
    });

    it("falls back to 'unknown' when no IP headers exist", () => {
      const req = {
        headers: new Headers(),
      } as unknown as NextRequest;
      expect(getClientIpFromHeaders(req)).toBe("unknown");
      expect(buildRateLimitKey(req)).toContain("unknown");
    });

    it("trims whitespace from x-real-ip", () => {
      const req = {
        headers: new Headers({
          "x-real-ip": "  192.168.1.1  ",
        }),
      } as unknown as NextRequest;
      expect(getClientIpFromHeaders(req)).toBe("192.168.1.1");
    });

    it("trims whitespace from x-forwarded-for entries", () => {
      const req = {
        headers: new Headers({
          "x-forwarded-for": "  203.0.113.10  , 198.51.100.2",
        }),
      } as unknown as NextRequest;
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
