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

type AutocompleteSuggestion = google.maps.places.AutocompleteSuggestion;
type AutocompleteRequest = google.maps.places.AutocompleteRequest;
type PlacePrediction = google.maps.places.PlacePrediction;

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
  const isMountedRef = useRef(true);
  const [isLoaded, setIsLoaded] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([]);
  const [sessionToken, setSessionToken] =
    useState<google.maps.places.AutocompleteSessionToken | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

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
      const placesLibrary: google.maps.PlacesLibrary =
        await window.google.maps.importLibrary("places");
      const { AutocompleteSessionToken } = placesLibrary;
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
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!value.trim()) {
      setSuggestions([]);
      setActiveIndex(-1);
      return;
    }

    const timer = setTimeout(async () => {
      if (
        !isMountedRef.current ||
        !isLoaded ||
        !window.google?.maps?.places ||
        !sessionToken
      )
        return;

      try {
        const placesLibrary: google.maps.PlacesLibrary =
          await window.google.maps.importLibrary("places");
        const { AutocompleteSuggestion } = placesLibrary;

        const request: AutocompleteRequest = {
          input: value,
          sessionToken: sessionToken ?? undefined,
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

        if (isMountedRef.current) {
          setSuggestions(newSuggestions ?? []);
          setActiveIndex(-1);
        }
      } catch (error) {
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error(String(error)),
          { action: "fetchSuggestions", context: "PlacesAutocomplete" }
        );
        if (isMountedRef.current) {
          setSuggestions([]);
          setActiveIndex(-1);
        }
      }
    }, 300); // 300ms debounce

    debounceTimerRef.current = timer;
  };

  const handlePlaceSelect = async (placePrediction: PlacePrediction | null) => {
    if (!isLoaded || !window.google?.maps?.places) return;
    if (!placePrediction) {
      setErrorMessage("Invalid place selection. Please try again.");
      return;
    }

    try {
      const place = placePrediction.toPlace();
      await place.fetchFields({
        fields: ["displayName", "formattedAddress", "location"],
      });

      setSelectedPlaceId(place.id ?? null);
      onPlaceSelect({
        displayName: place.displayName ?? "",
        formattedAddress: place.formattedAddress ?? undefined,
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
      const placesLibrary: google.maps.PlacesLibrary =
        await window.google.maps.importLibrary("places");
      const { AutocompleteSessionToken } = placesLibrary;
      const newToken = new AutocompleteSessionToken();
      setSessionToken(newToken);
      setSuggestions([]);
      setActiveIndex(-1);
    } catch (error) {
      recordClientErrorOnActiveSpan(
        error instanceof Error ? error : new Error(String(error)),
        { action: "handlePlaceSelect", context: "PlacesAutocomplete" }
      );
      setErrorMessage("Failed to select place. Please try again.");
      setSuggestions([]);
      setActiveIndex(-1);
    }
  };

  const selectableSuggestions = suggestions.filter(
    (
      suggestion
    ): suggestion is AutocompleteSuggestion & { placePrediction: PlacePrediction } =>
      suggestion.placePrediction != null
  );

  useEffect(() => {
    if (!selectableSuggestions.length) {
      setActiveIndex(-1);
      return;
    }
    if (activeIndex >= selectableSuggestions.length) {
      setActiveIndex(selectableSuggestions.length - 1);
    }
  }, [activeIndex, selectableSuggestions.length]);

  const getOptionId = (
    suggestion: (typeof selectableSuggestions)[number],
    index: number
  ) => suggestion.placePrediction.placeId ?? `places-option-${index}`;

  const listboxId = "places-autocomplete-listbox";

  const activeOptionId =
    activeIndex >= 0 && selectableSuggestions[activeIndex]
      ? getOptionId(selectableSuggestions[activeIndex], activeIndex)
      : undefined;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        event.target instanceof Node &&
        !containerRef.current.contains(event.target)
      ) {
        setSuggestions([]);
        setActiveIndex(-1);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <div ref={containerRef} className={`relative ${className ?? ""}`}>
      <input
        ref={inputRef}
        type="text"
        placeholder={placeholder}
        onChange={(e) => {
          handleInputChange(e.target.value);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActiveIndex((prev) => {
              const count = selectableSuggestions.length;
              if (count === 0) return -1;
              if (prev < 0) return 0;
              return (prev + 1) % count;
            });
            return;
          }
          if (e.key === "ArrowUp") {
            e.preventDefault();
            setActiveIndex((prev) => {
              const count = selectableSuggestions.length;
              if (count === 0) return -1;
              if (prev <= 0) return count - 1;
              return prev - 1;
            });
            return;
          }
          if (e.key === "Enter" && activeIndex >= 0) {
            e.preventDefault();
            const selected = selectableSuggestions[activeIndex];
            if (selected) {
              handlePlaceSelect(selected.placePrediction);
            }
            return;
          }
          if (e.key === "Escape") {
            setSuggestions([]);
            setActiveIndex(-1);
            return;
          }
        }}
        aria-activedescendant={activeOptionId}
        aria-expanded={selectableSuggestions.length > 0}
        aria-controls={selectableSuggestions.length > 0 ? listboxId : undefined}
        aria-autocomplete="list"
        aria-haspopup="listbox"
        role="combobox"
        className="w-full rounded-md border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {errorMessage ? (
        <p className="mt-2 text-sm text-red-700" role="alert">
          {errorMessage}
        </p>
      ) : null}
      {selectableSuggestions.length > 0 && (
        <div
          className="absolute z-10 mt-1 w-full rounded-md border border-gray-300 bg-white shadow-lg"
          role="listbox"
          id={listboxId}
          onMouseLeave={() => setActiveIndex(-1)}
        >
          {selectableSuggestions.map((suggestion, index) => {
            const optionId = getOptionId(suggestion, index);
            const isActive = index === activeIndex;
            const isSelected = selectedPlaceId === suggestion.placePrediction.placeId;
            const selectSuggestion = () => {
              setSelectedPlaceId(suggestion.placePrediction.placeId ?? null);
              handlePlaceSelect(suggestion.placePrediction);
            };
            return (
              <div
                key={optionId}
                id={optionId}
                role="option"
                aria-selected={isSelected}
                tabIndex={0}
                onClick={selectSuggestion}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    if (event.key === " ") {
                      event.preventDefault();
                    }
                    selectSuggestion();
                  }
                }}
                onMouseEnter={() => setActiveIndex(index)}
                className={`cursor-pointer px-4 py-2 hover:bg-gray-100 ${
                  isActive ? "bg-gray-100 font-medium" : ""
                }`}
              >
                {suggestion.placePrediction.text.text}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
