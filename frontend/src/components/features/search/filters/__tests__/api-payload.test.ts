/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import {
  type ActiveFilters,
  buildActivityApiPayload,
  buildFlightApiPayload,
  buildHotelApiPayload,
} from "../api-payload";
import { FILTER_IDS } from "../constants";

describe("API Payload Builders", () => {
  describe("buildFlightApiPayload", () => {
    it("returns empty object when no filters are active", () => {
      const filters: ActiveFilters = {};
      const result = buildFlightApiPayload(filters);
      expect(result).toEqual({});
    });

    it("converts direct stops filter to maxStops 0 and directOnly true", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.stops]: { value: "direct" },
      };
      const result = buildFlightApiPayload(filters);
      expect(result).toEqual({ directOnly: true, maxStops: 0 });
    });

    it("converts one stop filter to maxStops 1", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.stops]: { value: "one" },
      };
      const result = buildFlightApiPayload(filters);
      expect(result).toEqual({ directOnly: false, maxStops: 1 });
    });

    it("converts two+ stops filter to maxStops 2", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.stops]: { value: "two+" },
      };
      const result = buildFlightApiPayload(filters);
      expect(result).toEqual({ directOnly: false, maxStops: 2 });
    });

    it("ignores any stops filter", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.stops]: { value: "any" },
      };
      const result = buildFlightApiPayload(filters);
      expect(result).toEqual({});
    });

    it("extracts excluded airlines from multi-select filter", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.airlines]: { value: ["AA", "UA", "DL"] },
      };
      const result = buildFlightApiPayload(filters);
      expect(result).toEqual({ excludedAirlines: ["AA", "UA", "DL"] });
    });

    it("ignores empty airlines array", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.airlines]: { value: [] },
      };
      const result = buildFlightApiPayload(filters);
      expect(result).toEqual({});
    });

    it("extracts maxPrice from price range filter", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.priceRange]: { value: { max: 500, min: 100 } },
      };
      const result = buildFlightApiPayload(filters);
      expect(result).toEqual({ maxPrice: 500 });
    });

    it("combines multiple filters correctly", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.airlines]: { value: ["AA"] },
        [FILTER_IDS.priceRange]: { value: { max: 1000, min: 200 } },
        [FILTER_IDS.stops]: { value: "one" },
      };
      const result = buildFlightApiPayload(filters);
      expect(result).toEqual({
        directOnly: false,
        excludedAirlines: ["AA"],
        maxPrice: 1000,
        maxStops: 1,
      });
    });
  });

  describe("buildHotelApiPayload", () => {
    it("returns empty object when no filters are active", () => {
      const filters: ActiveFilters = {};
      const result = buildHotelApiPayload(filters);
      expect(result).toEqual({});
    });

    it("extracts price range filter", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.priceRange]: { value: { max: 300, min: 100 } },
      };
      const result = buildHotelApiPayload(filters);
      expect(result).toEqual({ priceRange: { max: 300, min: 100 } });
    });
  });

  describe("buildActivityApiPayload", () => {
    it("returns empty object when no filters are active", () => {
      const filters: ActiveFilters = {};
      const result = buildActivityApiPayload(filters);
      expect(result).toEqual({});
    });

    it("extracts price range filter", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.priceRange]: { value: { max: 150, min: 50 } },
      };
      const result = buildActivityApiPayload(filters);
      expect(result).toEqual({ priceRange: { max: 150, min: 50 } });
    });

    it("extracts maxDuration from duration filter", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.duration]: { value: { max: 240, min: 60 } },
      };
      const result = buildActivityApiPayload(filters);
      expect(result).toEqual({ maxDuration: 240 });
    });

    it("combines price range and duration filters", () => {
      const filters: ActiveFilters = {
        [FILTER_IDS.duration]: { value: { max: 180, min: 30 } },
        [FILTER_IDS.priceRange]: { value: { max: 200, min: 25 } },
      };
      const result = buildActivityApiPayload(filters);
      expect(result).toEqual({
        maxDuration: 180,
        priceRange: { max: 200, min: 25 },
      });
    });
  });
});
