"use client";

import { api } from "@/lib/api/client";
import { useSearchParamsStore, useSearchResultsStore } from "@/stores/search-store";
import type { Destination, DestinationSearchParams } from "@/types/search";
import { useMutation } from "@tanstack/react-query";
import { useEffect } from "react";

interface DestinationSearchResponse {
  destinations: Destination[];
  total: number;
  hasMore: boolean;
  metadata?: {
    searchTime: number;
    source: string;
    suggestions?: string[];
  };
}

interface DestinationAutocompleteParams {
  query: string;
  types?: string[];
  limit?: number;
  sessionToken?: string;
}

interface DestinationAutocompleteResponse {
  predictions: Array<{
    placeId: string;
    description: string;
    mainText: string;
    secondaryText: string;
    types: string[];
    structuredFormatting: {
      mainText: string;
      secondaryText: string;
    };
  }>;
  status: string;
}

export function useDestinationSearch() {
  const { updateDestinationParams } = useSearchParamsStore();
  const { setSearchResults: setResults } = useSearchResultsStore();

  // Main destination search mutation
  const searchMutation = useMutation({
    mutationFn: async (params: DestinationSearchParams) => {
      try {
        const response = await api.post<DestinationSearchResponse>(
          "/api/destinations/search",
          params
        );
        return response;
      } catch (error) {
        console.error("Destination search error:", error);
        throw error;
      }
    },
  });

  // Handle search success
  useEffect(() => {
    if (searchMutation.data) {
      // Use the proper search results format expected by the store
      setResults(
        "destination",
        { destinations: searchMutation.data.destinations },
        {
          totalResults: searchMutation.data.total,
          resultsPerPage: 20,
          currentPage: 1,
          hasMoreResults: searchMutation.data.hasMore,
          searchDuration: searchMutation.data.metadata?.searchTime || 0,
          provider: "DestinationService",
          requestId: `dest_${Date.now()}`,
        }
      );
      updateDestinationParams({
        query: searchMutation.data.metadata?.source || "",
      });
    }
  }, [searchMutation.data, setResults, updateDestinationParams]);

  // Handle search error
  useEffect(() => {
    if (searchMutation.error) {
      console.error("Search failed:", searchMutation.error);
    }
  }, [searchMutation.error]);

  // Autocomplete mutation for real-time suggestions
  const autocompleteMutation = useMutation({
    mutationFn: async (params: DestinationAutocompleteParams) => {
      try {
        const response = await api.post<DestinationAutocompleteResponse>(
          "/api/destinations/autocomplete",
          params
        );
        return response;
      } catch (error) {
        console.error("Autocomplete error:", error);
        throw error;
      }
    },
  });

  // Place details mutation for getting full destination info
  const placeDetailsMutation = useMutation({
    mutationFn: async (placeId: string) => {
      try {
        const response = await api.get<Destination>(
          `/api/destinations/details/${placeId}`
        );
        return response;
      } catch (error) {
        console.error("Place details error:", error);
        throw error;
      }
    },
  });

  // Helper function to search destinations
  const searchDestinations = async (params: DestinationSearchParams) => {
    return await searchMutation.mutateAsync(params);
  };

  // Helper function to get autocomplete suggestions
  const getAutocompleteSuggestions = async (params: DestinationAutocompleteParams) => {
    return await autocompleteMutation.mutateAsync(params);
  };

  // Helper function to get place details
  const getPlaceDetails = async (placeId: string) => {
    return await placeDetailsMutation.mutateAsync(placeId);
  };

  // Generate a session token for autocomplete sessions
  const generateSessionToken = () => {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
  };

  // Mock data generator for development
  const generateMockDestinations = (query: string): Destination[] => {
    const baseDestinations = [
      {
        id: "dest_paris_fr",
        name: "Paris",
        description:
          "The City of Light, known for its art, fashion, gastronomy, and culture. Home to iconic landmarks like the Eiffel Tower and Louvre Museum.",
        formattedAddress: "Paris, France",
        types: ["locality", "political"],
        coordinates: { lat: 48.8566, lng: 2.3522 },
        photos: ["/images/destinations/paris.jpg"],
        placeId: "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
        country: "France",
        region: "Île-de-France",
        rating: 4.6,
        popularityScore: 95,
        climate: {
          season: "temperate",
          averageTemp: 12,
          rainfall: 640,
        },
        attractions: ["Eiffel Tower", "Louvre Museum", "Notre-Dame", "Arc de Triomphe"],
        bestTimeToVisit: ["Apr", "May", "Jun", "Sep", "Oct"],
      },
      {
        id: "dest_tokyo_jp",
        name: "Tokyo",
        description:
          "Japan's bustling capital, blending traditional culture with cutting-edge technology. Experience temples, skyscrapers, and incredible cuisine.",
        formattedAddress: "Tokyo, Japan",
        types: ["locality", "political"],
        coordinates: { lat: 35.6762, lng: 139.6503 },
        photos: ["/images/destinations/tokyo.jpg"],
        placeId: "ChIJ51cu8IcbXWARiRtXIothAS4",
        country: "Japan",
        region: "Kantō",
        rating: 4.7,
        popularityScore: 92,
        climate: {
          season: "subtropical",
          averageTemp: 16,
          rainfall: 1520,
        },
        attractions: [
          "Senso-ji Temple",
          "Tokyo Skytree",
          "Shibuya Crossing",
          "Imperial Palace",
        ],
        bestTimeToVisit: ["Mar", "Apr", "May", "Oct", "Nov"],
      },
      {
        id: "dest_newyork_us",
        name: "New York City",
        description:
          "The Big Apple, a global hub for art, fashion, finance, and culture. Iconic skyline with endless attractions and activities.",
        formattedAddress: "New York, NY, USA",
        types: ["locality", "political"],
        coordinates: { lat: 40.7128, lng: -74.006 },
        photos: ["/images/destinations/nyc.jpg"],
        placeId: "ChIJOwg_06VPwokRYv534QaPC8g",
        country: "United States",
        region: "New York",
        rating: 4.5,
        popularityScore: 90,
        climate: {
          season: "continental",
          averageTemp: 13,
          rainfall: 1200,
        },
        attractions: [
          "Central Park",
          "Statue of Liberty",
          "Times Square",
          "Empire State Building",
        ],
        bestTimeToVisit: ["Apr", "May", "Jun", "Sep", "Oct", "Nov"],
      },
    ];

    // Filter based on query
    return baseDestinations.filter(
      (dest) =>
        dest.name.toLowerCase().includes(query.toLowerCase()) ||
        dest.country?.toLowerCase().includes(query.toLowerCase()) ||
        dest.formattedAddress.toLowerCase().includes(query.toLowerCase())
    );
  };

  // Mock search for development
  const searchDestinationsMock = async (params: DestinationSearchParams) => {
    try {
      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 800));

      const mockDestinations = generateMockDestinations(params.query);

      const response: DestinationSearchResponse = {
        destinations: mockDestinations,
        total: mockDestinations.length,
        hasMore: false,
        metadata: {
          searchTime: 0.8,
          source: "mock",
          suggestions: ["Paris, France", "Tokyo, Japan", "New York, USA"],
        },
      };

      setResults(
        "destination",
        { destinations: response.destinations },
        {
          totalResults: response.total,
          resultsPerPage: 20,
          currentPage: 1,
          hasMoreResults: response.hasMore,
          searchDuration: response.metadata?.searchTime || 0,
          provider: "MockDestinationService",
          requestId: `mock_dest_${Date.now()}`,
        }
      );
      updateDestinationParams(params);

      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Search failed";
      console.error("Mock search failed:", errorMessage);
      throw error;
    }
  };

  return {
    // Main search function
    searchDestinations,
    searchDestinationsMock,

    // Autocomplete functions
    getAutocompleteSuggestions,
    generateSessionToken,

    // Place details function
    getPlaceDetails,

    // Mutation states
    isSearching: searchMutation.isPending,
    isAutocompleting: autocompleteMutation.isPending,
    isLoadingDetails: placeDetailsMutation.isPending,

    // Error states
    searchError: searchMutation.error,
    autocompleteError: autocompleteMutation.error,
    detailsError: placeDetailsMutation.error,

    // Reset functions
    resetSearch: () => {
      searchMutation.reset();
    },
    resetAutocomplete: () => autocompleteMutation.reset(),
    resetDetails: () => placeDetailsMutation.reset(),
  };
}
