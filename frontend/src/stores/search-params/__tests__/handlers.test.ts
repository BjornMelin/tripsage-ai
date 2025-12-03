/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { getHandler } from "../registry";
// Import handlers to trigger registration
import "../handlers/accommodation-handler";
import "../handlers/activity-handler";
import "../handlers/destination-handler";
import "../handlers/flight-handler";

describe("search-params/handlers", () => {
  describe("flight handler", () => {
    const handler = getHandler("flight");

    describe("getDefaults", () => {
      it("returns default flight params", () => {
        const defaults = handler.getDefaults();
        expect(defaults).toEqual({
          adults: 1,
          cabinClass: "economy",
          children: 0,
          directOnly: false,
          excludedAirlines: [],
          infants: 0,
          preferredAirlines: [],
        });
      });
    });

    describe("validate", () => {
      it("validates valid params", () => {
        const result = handler.validate({
          adults: 2,
          destination: "LAX",
          origin: "NYC",
        });
        expect(result.success).toBe(true);
      });

      it("rejects invalid adults count", () => {
        const result = handler.validate({ adults: 0 });
        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error).toBeTruthy();
        }
      });
    });

    describe("hasRequiredParams", () => {
      it("returns true when origin, destination, departureDate present", () => {
        expect(
          handler.hasRequiredParams({
            departureDate: "2025-07-15",
            destination: "LAX",
            origin: "NYC",
          })
        ).toBe(true);
      });

      it("returns false when origin missing", () => {
        expect(
          handler.hasRequiredParams({
            departureDate: "2025-07-15",
            destination: "LAX",
          })
        ).toBe(false);
      });

      it("returns false when destination missing", () => {
        expect(
          handler.hasRequiredParams({
            departureDate: "2025-07-15",
            origin: "NYC",
          })
        ).toBe(false);
      });

      it("returns false when departureDate missing", () => {
        expect(
          handler.hasRequiredParams({
            destination: "LAX",
            origin: "NYC",
          })
        ).toBe(false);
      });
    });

    describe("mergeParams", () => {
      it("merges updates into current params", () => {
        const current = { adults: 1, origin: "NYC" };
        const updates = { destination: "LAX" };
        const result = handler.mergeParams(current, updates);
        expect(result).toEqual({ adults: 1, destination: "LAX", origin: "NYC" });
      });
    });
  });

  describe("accommodation handler", () => {
    const handler = getHandler("accommodation");

    describe("getDefaults", () => {
      it("returns default accommodation params", () => {
        const defaults = handler.getDefaults();
        expect(defaults).toEqual({
          adults: 1,
          amenities: [],
          children: 0,
          infants: 0,
          rooms: 1,
        });
      });
    });

    describe("hasRequiredParams", () => {
      it("returns true when destination, checkIn, checkOut present", () => {
        expect(
          handler.hasRequiredParams({
            checkIn: "2025-07-01",
            checkOut: "2025-07-07",
            destination: "Paris",
          })
        ).toBe(true);
      });

      it("returns false when destination missing", () => {
        expect(
          handler.hasRequiredParams({
            checkIn: "2025-07-01",
            checkOut: "2025-07-07",
          })
        ).toBe(false);
      });
    });
  });

  describe("activity handler", () => {
    const handler = getHandler("activity");

    describe("getDefaults", () => {
      it("returns default activity params", () => {
        const defaults = handler.getDefaults();
        expect(defaults).toEqual({
          adults: 1,
          children: 0,
          infants: 0,
        });
      });
    });

    describe("hasRequiredParams", () => {
      it("returns true when destination present", () => {
        expect(handler.hasRequiredParams({ destination: "Tokyo" })).toBe(true);
      });

      it("returns false when destination missing", () => {
        expect(handler.hasRequiredParams({})).toBe(false);
      });

      it("returns false when destination empty", () => {
        expect(handler.hasRequiredParams({ destination: "" })).toBe(false);
      });
    });
  });

  describe("destination handler", () => {
    const handler = getHandler("destination");

    describe("getDefaults", () => {
      it("returns default destination params", () => {
        const defaults = handler.getDefaults();
        expect(defaults).toEqual({
          limit: 10,
          query: "",
          types: ["locality", "country"],
        });
      });
    });

    describe("hasRequiredParams", () => {
      it("returns true when query has content", () => {
        expect(handler.hasRequiredParams({ query: "Europe" })).toBe(true);
      });

      it("returns false when query missing", () => {
        expect(handler.hasRequiredParams({})).toBe(false);
      });

      it("returns false when query empty", () => {
        expect(handler.hasRequiredParams({ query: "" })).toBe(false);
      });

      it("returns false when query only whitespace", () => {
        expect(handler.hasRequiredParams({ query: "   " })).toBe(false);
      });
    });

    describe("validate", () => {
      it("validates valid destination params", () => {
        const result = handler.validate({ limit: 20, query: "Europe" });
        expect(result.success).toBe(true);
      });

      it("rejects limit below 1", () => {
        const result = handler.validate({ limit: 0, query: "Europe" });
        expect(result.success).toBe(false);
      });

      it("rejects limit above 50", () => {
        const result = handler.validate({ limit: 100, query: "Europe" });
        expect(result.success).toBe(false);
      });
    });
  });
});
