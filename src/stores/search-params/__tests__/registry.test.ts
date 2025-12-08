/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { registerAllHandlers } from "../handlers";
import { getHandler, getRegisteredTypes, hasHandler } from "../registry";

// Ensure handlers are registered for tests
registerAllHandlers();

describe("search-params/registry", () => {
  describe("getHandler", () => {
    it("returns flight handler", () => {
      const handler = getHandler("flight");
      expect(handler.searchType).toBe("flight");
      expect(typeof handler.getDefaults).toBe("function");
      expect(typeof handler.validate).toBe("function");
      expect(typeof handler.hasRequiredParams).toBe("function");
    });

    it("returns accommodation handler", () => {
      const handler = getHandler("accommodation");
      expect(handler.searchType).toBe("accommodation");
      expect(typeof handler.getDefaults).toBe("function");
      expect(typeof handler.validate).toBe("function");
      expect(typeof handler.hasRequiredParams).toBe("function");
    });

    it("returns activity handler", () => {
      const handler = getHandler("activity");
      expect(handler.searchType).toBe("activity");
      expect(typeof handler.getDefaults).toBe("function");
      expect(typeof handler.validate).toBe("function");
      expect(typeof handler.hasRequiredParams).toBe("function");
    });

    it("returns destination handler", () => {
      const handler = getHandler("destination");
      expect(handler.searchType).toBe("destination");
      expect(typeof handler.getDefaults).toBe("function");
      expect(typeof handler.validate).toBe("function");
      expect(typeof handler.hasRequiredParams).toBe("function");
    });

    it("throws for unknown search type", () => {
      expect(() => getHandler("unknown" as never)).toThrow(
        "No handler registered for search type: unknown"
      );
    });
  });

  describe("hasHandler", () => {
    it("returns true for registered types", () => {
      expect(hasHandler("flight")).toBe(true);
      expect(hasHandler("accommodation")).toBe(true);
      expect(hasHandler("activity")).toBe(true);
      expect(hasHandler("destination")).toBe(true);
    });

    it("returns false for unregistered types", () => {
      expect(hasHandler("unknown" as never)).toBe(false);
    });
  });

  describe("getRegisteredTypes", () => {
    it("returns all registered search types", () => {
      const types = getRegisteredTypes();
      expect(types).toContain("flight");
      expect(types).toContain("accommodation");
      expect(types).toContain("activity");
      expect(types).toContain("destination");
      expect(types).toHaveLength(4);
    });
  });
});
