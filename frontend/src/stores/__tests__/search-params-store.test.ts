import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSearchParamsStore } from "../search-params-store";

describe("Search Params Store", () => {
  beforeEach(() => {
    act(() => {
      useSearchParamsStore.setState({
        currentSearchType: null,
        flightParams: {},
        accommodationParams: {},
        activityParams: {},
        destinationParams: {},
        validationErrors: {
          flight: null,
          accommodation: null,
          activity: null,
          destination: null,
        },
        isValidating: {
          flight: false,
          accommodation: false,
          activity: false,
          destination: false,
        },
      });
    });
  });

  describe("Search Type Management", () => {
    it("initializes with null search type", () => {
      const { result } = renderHook(() => useSearchParamsStore());
      expect(result.current.currentSearchType).toBeNull();
    });

    it("sets search type and initializes default params", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");
      expect(result.current.flightParams).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: "economy",
        directOnly: false,
        preferredAirlines: [],
        excludedAirlines: [],
      });
    });

    it("switches between search types", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");

      act(() => {
        result.current.setSearchType("accommodation");
      });

      expect(result.current.currentSearchType).toBe("accommodation");
      expect(result.current.accommodationParams).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        rooms: 1,
        amenities: [],
      });
    });

    it("resets all parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");

      act(() => {
        result.current.reset();
      });

      expect(result.current.currentSearchType).toBeNull();
    });
  });

  describe("Flight Parameters", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useSearchParamsStore());
      act(() => {
        result.current.setSearchType("flight");
      });
    });

    it("updates flight parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
          departureDate: "2025-07-15",
          returnDate: "2025-07-22",
          adults: 2,
          cabinClass: "business",
        });
      });

      const params = result.current.flightParams;
      expect(params.origin).toBe("NYC");
      expect(params.destination).toBe("LAX");
      expect(params.departureDate).toBe("2025-07-15");
      expect(params.returnDate).toBe("2025-07-22");
      expect(params.adults).toBe(2);
      expect(params.cabinClass).toBe("business");
    });

    it("resets flight parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
          adults: 3,
        });
      });

      expect(result.current.flightParams.origin).toBe("NYC");

      act(() => {
        result.current.resetParams("flight");
      });

      const defaultParams = {
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: "economy",
        directOnly: false,
        preferredAirlines: [],
        excludedAirlines: [],
      };

      expect(result.current.flightParams).toEqual(defaultParams);
    });
  });

  describe("Accommodation Parameters", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useSearchParamsStore());
      act(() => {
        result.current.setSearchType("accommodation");
      });
    });

    it("updates accommodation parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.updateAccommodationParams({
          destination: "Paris",
          checkIn: "2025-08-01",
          checkOut: "2025-08-07",
          adults: 2,
          rooms: 2,
          propertyType: "hotel",
          amenities: ["wifi", "pool"],
        });
      });

      const params = result.current.accommodationParams;
      expect(params.destination).toBe("Paris");
      expect(params.checkIn).toBe("2025-08-01");
      expect(params.checkOut).toBe("2025-08-07");
      expect(params.adults).toBe(2);
      expect(params.rooms).toBe(2);
      expect(params.propertyType).toBe("hotel");
      expect(params.amenities).toEqual(["wifi", "pool"]);
    });

    it("resets accommodation parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.updateAccommodationParams({
          destination: "Paris",
          adults: 3,
        });
      });

      expect(result.current.accommodationParams.destination).toBe("Paris");

      act(() => {
        result.current.resetParams("accommodation");
      });

      const defaultParams = {
        adults: 1,
        children: 0,
        infants: 0,
        rooms: 1,
        amenities: [],
      };

      expect(result.current.accommodationParams).toEqual(defaultParams);
    });
  });

  describe("Activity Parameters", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useSearchParamsStore());
      act(() => {
        result.current.setSearchType("activity");
      });
    });

    it("updates activity parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.updateActivityParams({
          destination: "Tokyo",
          date: "2025-09-15",
          duration: { min: 120, max: 240 },
          category: "cultural",
          difficulty: "moderate",
        });
      });

      const params = result.current.activityParams;
      expect(params.destination).toBe("Tokyo");
      expect(params.date).toBe("2025-09-15");
      expect(params.duration).toEqual({ min: 120, max: 240 });
      expect(params.category).toBe("cultural");
      expect(params.difficulty).toBe("moderate");
    });

    it("resets activity parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.updateActivityParams({
          destination: "Tokyo",
          category: "cultural",
        });
      });

      expect(result.current.activityParams.destination).toBe("Tokyo");

      act(() => {
        result.current.resetParams("activity");
      });

      const defaultParams = {
        adults: 1,
        children: 0,
        infants: 0,
      };

      expect(result.current.activityParams).toEqual(defaultParams);
    });
  });

  describe("Destination Parameters", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useSearchParamsStore());
      act(() => {
        result.current.setSearchType("destination");
      });
    });

    it("updates destination parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.updateDestinationParams({
          query: "Europe",
          limit: 20,
          types: ["locality", "country", "landmark"],
          countryCode: "FR",
        });
      });

      const params = result.current.destinationParams;
      expect(params.query).toBe("Europe");
      expect(params.limit).toBe(20);
      expect(params.types).toEqual(["locality", "country", "landmark"]);
      expect(params.countryCode).toBe("FR");
    });

    it("resets destination parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.updateDestinationParams({
          query: "Asia",
          limit: 30,
        });
      });

      expect(result.current.destinationParams.query).toBe("Asia");

      act(() => {
        result.current.resetParams("destination");
      });

      const defaultParams = {
        query: "",
        limit: 10,
        types: ["locality", "country"],
      };

      expect(result.current.destinationParams).toEqual(defaultParams);
    });
  });

  describe.skip("Current Parameters Getter", () => {
    it("returns null when no search type is set", () => {
      const { result } = renderHook(() => useSearchParamsStore());
      expect(result.current.currentParams).toBeNull();
    });

    it("returns flight params when search type is flight", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
        });
      });

      const params = result.current.currentParams;
      expect(params).toMatchObject({
        origin: "NYC",
        destination: "LAX",
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: "economy",
        directOnly: false,
        preferredAirlines: [],
        excludedAirlines: [],
      });
    });

    it("returns accommodation params when search type is accommodation", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("accommodation");
        result.current.updateAccommodationParams({
          destination: "Paris",
          adults: 2,
        });
      });

      const params = result.current.currentParams;
      expect(params).toMatchObject({
        destination: "Paris",
        adults: 2,
        children: 0,
        infants: 0,
        rooms: 1,
        amenities: [],
      });
    });
  });

  describe("Validation", () => {
    it("validates current parameters successfully", async () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
          departureDate: "2025-07-15",
          adults: 2,
        });
      });

      await act(async () => {
        const isValid = await result.current.validateCurrentParams();
        expect(isValid).toBe(true);
      });

      expect(result.current.validationErrors).toEqual({
        flight: null,
        accommodation: null,
        activity: null,
        destination: null,
      });
    });

    it("handles validation errors", async () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
        // Don't set required parameters
      });

      await act(async () => {
        const isValid = await result.current.validateCurrentParams();
        expect(isValid).toBe(false);
      });

      expect(Object.keys(result.current.validationErrors).length).toBeGreaterThan(0);
    });

    it("sets validation state during validation", async () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
      });

      const validatePromise = act(async () => {
        return result.current.validateCurrentParams();
      });

      expect(result.current.isValidating).toBe(true);

      await validatePromise;

      expect(result.current.isValidating).toBe(false);
    });
  });

  describe("Parameter Reset", () => {
    it("resets all parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({ origin: "NYC" });
        result.current.setSearchType("accommodation");
        result.current.updateAccommodationParams({ destination: "Paris" });
      });

      expect(result.current.flightParams.origin).toBe("NYC");
      expect(result.current.accommodationParams.destination).toBe("Paris");

      act(() => {
        result.current.reset();
      });

      expect(result.current.flightParams).toEqual({});
      expect(result.current.accommodationParams).toEqual({});
      expect(result.current.activityParams).toEqual({});
      expect(result.current.destinationParams).toEqual({});
      expect(result.current.currentSearchType).toBeNull();
    });
  });
});
