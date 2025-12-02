/**
 * @fileoverview Google Places Autocomplete component with session tokens.
 *
 * Client-side autocomplete component using Places Autocomplete Data API with
 * session token lifecycle management and debounced input handling.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { getGoogleMapsBrowserKey } from "@/lib/env/client";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

declare global {
  interface Window {
    google?: typeof google;
  }
}

interface PlacesAutocompleteProps {
  onPlaceSelect: (place: {
    placeId: string;
    displayName: string;
    formattedAddress?: string;
    location?: { lat: number; lng: number };
  }) => void;
  placeholder?: string;
  locationBias?: {
    lat: number;
    lng: number;
    radiusMeters: number;
  };
  includedTypes?: string[];
  className?: string;
}

/**
 * Google Places Autocomplete component with session tokens.
 *
 * @param props Autocomplete configuration props.
 */
export function PlacesAutocomplete({
  onPlaceSelect,
  placeholder = "Search places...",
  locationBias,
  includedTypes,
  className,
}: PlacesAutocompleteProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<
    Array<{
      placePrediction: {
        placeId: string;
        text: string;
      };
    }>
  >([]);
  const [sessionToken, setSessionToken] =
    useState<google.maps.places.AutocompleteSessionToken | null>(null);
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isLoaded || typeof window === "undefined") return;

    const apiKey = getGoogleMapsBrowserKey();

    if (!apiKey) {
      if (process.env.NODE_ENV === "development") {
        console.warn(
          "Google Maps browser API key not configured. Set NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY."
        );
      } else {
        recordClientErrorOnActiveSpan(
          new Error("Google Maps browser API key not configured"),
          { action: "checkApiKey", context: "PlacesAutocomplete" }
        );
      }
      setErrorMessage("Maps configuration error. Please try again later.");
      return;
    }

    // Load Maps JS API script if not already loaded
    if (window.google?.maps) {
      setIsLoaded(true);
    } else {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&loading=async&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = () => {
        setIsLoaded(true);
      };
      document.head.appendChild(script);
    }
  }, [isLoaded]);

  useEffect(() => {
    if (!isLoaded || !window.google?.maps?.places) return;

    const initAutocomplete = async () => {
      const placesLibrary = await window.google.maps.importLibrary("places");
      // @ts-expect-error - AutocompleteSessionToken may not be fully typed
      const AutocompleteSessionToken = placesLibrary.AutocompleteSessionToken;
      const newToken = new AutocompleteSessionToken();
      setSessionToken(newToken);
    };

    initAutocomplete().catch((error) => {
      recordClientErrorOnActiveSpan(
        error instanceof Error ? error : new Error(String(error)),
        { action: "initAutocomplete", context: "PlacesAutocomplete" }
      );
    });
  }, [isLoaded]);

  const handleInputChange = (value: string) => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    if (!value.trim()) {
      setSuggestions([]);
      return;
    }

    const timer = setTimeout(async () => {
      if (!isLoaded || !window.google?.maps?.places || !sessionToken) return;

      try {
        const placesLibrary = await window.google.maps.importLibrary("places");
        // @ts-expect-error - AutocompleteSuggestion may not be fully typed
        const AutocompleteSuggestion = placesLibrary.AutocompleteSuggestion;

        const request: Record<string, unknown> = {
          input: value,
          sessionToken,
        };

        if (locationBias) {
          request.locationRestriction = {
            east: locationBias.lng + 0.01,
            north: locationBias.lat + 0.01,
            south: locationBias.lat - 0.01,
            west: locationBias.lng - 0.01,
          };
        }

        if (includedTypes && includedTypes.length > 0) {
          request.includedPrimaryTypes = includedTypes.slice(0, 5);
        }

        const { suggestions: newSuggestions } =
          await AutocompleteSuggestion.fetchAutocompleteSuggestions(request);

        setSuggestions(newSuggestions);
      } catch (error) {
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error(String(error)),
          { action: "fetchSuggestions", context: "PlacesAutocomplete" }
        );
        setSuggestions([]);
      }
    }, 300); // 300ms debounce

    setDebounceTimer(timer);
  };

  const handlePlaceSelect = async (placePrediction: {
    placeId: string;
    text: string;
    toPlace?: () => unknown;
  }) => {
    if (!isLoaded || !window.google?.maps?.places) return;

    try {
      // @ts-expect-error - toPlace may not be fully typed
      const place = placePrediction.toPlace() as {
        fetchFields: (options: { fields: string[] }) => Promise<void>;
        displayName?: { text?: string };
        formattedAddress?: string;
        location?: { lat: () => number; lng: () => number };
        id?: string;
      };
      await place.fetchFields({
        fields: ["displayName", "formattedAddress", "location"],
      });

      onPlaceSelect({
        displayName: place.displayName?.text ?? "",
        formattedAddress: place.formattedAddress,
        location: place.location
          ? {
              lat: place.location.lat(),
              lng: place.location.lng(),
            }
          : undefined,
        placeId: place.id ?? "",
      });

      setErrorMessage(null);

      // Terminate session and create new token
      const placesLibrary = await window.google.maps.importLibrary("places");
      // @ts-expect-error - AutocompleteSessionToken may not be fully typed
      const AutocompleteSessionToken = placesLibrary.AutocompleteSessionToken;
      const newToken = new AutocompleteSessionToken();
      setSessionToken(newToken);
      setSuggestions([]);
    } catch (error) {
      recordClientErrorOnActiveSpan(
        error instanceof Error ? error : new Error(String(error)),
        { action: "handlePlaceSelect", context: "PlacesAutocomplete" }
      );
      setErrorMessage("Failed to select place. Please try again.");
      setSuggestions([]);
    }
  };

  return (
    <div className={`relative ${className ?? ""}`}>
      <input
        ref={inputRef}
        type="text"
        placeholder={placeholder}
        onChange={(e) => {
          handleInputChange(e.target.value);
        }}
        className="w-full rounded-md border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {errorMessage ? (
        <p className="mt-2 text-sm text-red-600" role="alert">
          {errorMessage}
        </p>
      ) : null}
      {suggestions.length > 0 && (
        <ul className="absolute z-10 mt-1 w-full rounded-md border border-gray-300 bg-white shadow-lg">
          {suggestions.map((suggestion, index) => (
            <li
              key={suggestion.placePrediction.placeId ?? index}
              onClick={() => handlePlaceSelect(suggestion.placePrediction)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  handlePlaceSelect(suggestion.placePrediction);
                }
              }}
              className="cursor-pointer px-4 py-2 hover:bg-gray-100"
            >
              {suggestion.placePrediction.text.toString()}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
