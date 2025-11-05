import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSearchParamsStore, selectCurrentParamsFrom } from "../search-params-store";

describe("Search Params Store", () => {
  beforeEach(() => {
    useSearchParamsStore.setState({
      accommodationParams: {},
      activityParams: {},
      currentSearchType: null,
      destinationParams: {},
      flightParams: {},
      isValidating: {
        accommodation: false,
        activity: false,
        destination: false,
        flight: false,
      },
      validationErrors: {
        accommodation: null,
        activity: null,
        destination: null,
        flight: null,
      },
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
        cabinClass: "economy",
        children: 0,
        directOnly: false,
        excludedAirlines: [],
        infants: 0,
        preferredAirlines: [],
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
        amenities: [],
        children: 0,
        infants: 0,
        rooms: 1,
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
          adults: 2,
          cabinClass: "business",
          departureDate: "2025-07-15",
          destination: "LAX",
          origin: "NYC",
          returnDate: "2025-07-22",
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
          adults: 3,
          destination: "LAX",
          origin: "NYC",
        });
      });

      expect(result.current.flightParams.origin).toBe("NYC");

      act(() => {
        result.current.resetParams("flight");
      });

      const defaultParams = {
        adults: 1,
        cabinClass: "economy",
        children: 0,
        directOnly: false,
        excludedAirlines: [],
        infants: 0,
        preferredAirlines: [],
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
          adults: 2,
          amenities: ["wifi", "pool"],
          checkIn: "2025-08-01",
          checkOut: "2025-08-07",
          destination: "Paris",
          propertyType: "hotel",
          rooms: 2,
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
          adults: 3,
          destination: "Paris",
        });
      });

      expect(result.current.accommodationParams.destination).toBe("Paris");

      act(() => {
        result.current.resetParams("accommodation");
      });

      const defaultParams = {
        adults: 1,
        amenities: [],
        children: 0,
        infants: 0,
        rooms: 1,
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
          category: "cultural",
          date: "2025-09-15",
          destination: "Tokyo",
          difficulty: "moderate",
          duration: { max: 240, min: 120 },
        });
      });

      const params = result.current.activityParams;
      expect(params.destination).toBe("Tokyo");
      expect(params.date).toBe("2025-09-15");
      expect(params.duration).toEqual({ max: 240, min: 120 });
      expect(params.category).toBe("cultural");
      expect(params.difficulty).toBe("moderate");
    });

    it("resets activity parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.updateActivityParams({
          category: "cultural",
          destination: "Tokyo",
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
          countryCode: "FR",
          limit: 20,
          query: "Europe",
          types: ["locality", "country", "landmark"],
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
          limit: 30,
          query: "Asia",
        });
      });

      expect(result.current.destinationParams.query).toBe("Asia");

      act(() => {
        result.current.resetParams("destination");
      });

      const defaultParams = {
        limit: 10,
        query: "",
        types: ["locality", "country"],
      };

      expect(result.current.destinationParams).toEqual(defaultParams);
    });
  });

  describe("Current Parameters Getter", () => {
    it("returns null when no search type is set", () => {
      const { result } = renderHook(() => useSearchParamsStore());
      expect(result.current.currentParams).toBeNull();
    });

    it("returns flight params when search type is flight", async () => {
      const { result } = renderHook(() => useSearchParamsStore());

      await act(async () => {
        result.current.setSearchType("flight");
        await result.current.updateFlightParams({
          destination: "LAX",
          origin: "NYC",
        });
      });

      const params = selectCurrentParamsFrom(useSearchParamsStore.getState());
      expect(params).toMatchObject({
        adults: 1,
        cabinClass: "economy",
        children: 0,
        destination: "LAX",
        directOnly: false,
        excludedAirlines: [],
        infants: 0,
        origin: "NYC",
        preferredAirlines: [],
      });
    });

    it("returns accommodation params when search type is accommodation", async () => {
      const { result } = renderHook(() => useSearchParamsStore());

      await act(async () => {
        result.current.setSearchType("accommodation");
        const success = await result.current.updateAccommodationParams({
          adults: 2,
          checkIn: "2025-07-01",
          checkOut: "2025-07-07",
          destination: "Paris",
        });
        expect(success).toBe(true);
      });

      const params = selectCurrentParamsFrom(useSearchParamsStore.getState());
      expect(params).toMatchObject({
        adults: 2,
        amenities: [],
        children: 0,
        destination: "Paris",
        infants: 0,
        rooms: 1,
      });
    });
  });

  describe("Validation", () => {
    it("validates current parameters successfully", async () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
      });
      await act(async () => {
        await result.current.updateFlightParams({
          adults: 2,
          departureDate: "2025-07-15",
          destination: "LAX",
          origin: "NYC",
        });
      });

      const isValid = await result.current.validateCurrentParams();
      expect(isValid).toBe(true);

      expect(result.current.validationErrors).toEqual({
        accommodation: null,
        activity: null,
        destination: null,
        flight: null,
      });
    });

    it("handles validation errors", async () => {
      const { result } = renderHook(() => useSearchParamsStore());
      act(() => {
        result.current.setSearchType("flight");
      });
      // Force invalid value against schema (adults must be >=1)
      const updated = await result.current.updateFlightParams({ adults: 0 });
      expect(updated).toBe(false);
      // State should remain at previous valid defaults
      expect(result.current.flightParams.adults).toBe(1);
    });

    it("validates without toggling isValidating flags", async () => {
      const { result } = renderHook(() => useSearchParamsStore());
      act(() => {
        result.current.setSearchType("flight");
      });
      const before = { ...result.current.isValidating };
      const validateResult = await result.current.validateCurrentParams();
      expect(typeof validateResult).toBe("boolean");
      expect(result.current.isValidating).toEqual(before);
    });

    describe("Parameter Reset", () => {
      it("resets all parameters", async () => {
        const { result } = renderHook(() => useSearchParamsStore());

        act(() => {
          result.current.setSearchType("flight");
        });
        await act(async () => {
          await result.current.updateFlightParams({ origin: "NYC" });
        });
        act(() => {
          result.current.setSearchType("accommodation");
        });
        await act(async () => {
          await result.current.updateAccommodationParams({ destination: "Paris" });
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
});
