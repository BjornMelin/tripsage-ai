/**
 * @fileoverview Google Maps extended type definitions for the dynamic import API.
 *
 * Augments @types/google.maps to include types for the importLibrary() method.
 * The Google Maps JavaScript API uses a dynamic import pattern that isn't fully
 * covered by the base @types/google.maps package.
 *
 * @see https://developers.google.com/maps/documentation/javascript/libraries
 */

/// <reference types="@types/google.maps" />

export {};

declare global {
  namespace google.maps {
    /**
     * Dynamically loads a Maps JavaScript API library.
     *
     * This function is the recommended way to load libraries in modern
     * applications using the Dynamic Library Import feature.
     *
     * @param libraryName - The name of the library to load.
     * @returns A promise that resolves to the library module.
     */
    function importLibrary(libraryName: "maps"): Promise<MapsLibrary>;
    function importLibrary(libraryName: "marker"): Promise<MarkerLibrary>;
    function importLibrary(libraryName: "places"): Promise<PlacesLibrary>;
    function importLibrary(libraryName: "geometry"): Promise<GeometryLibrary>;
    function importLibrary(libraryName: "drawing"): Promise<DrawingLibrary>;
    function importLibrary(libraryName: "visualization"): Promise<VisualizationLibrary>;
    function importLibrary(libraryName: string): Promise<unknown>;

    /** The Maps library module returned by importLibrary("maps"). */
    interface MapsLibrary {
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      Map: typeof google.maps.Map;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      MapTypeId: typeof google.maps.MapTypeId;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      TrafficLayer: typeof google.maps.TrafficLayer;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      TransitLayer: typeof google.maps.TransitLayer;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      BicyclingLayer: typeof google.maps.BicyclingLayer;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      InfoWindow: typeof google.maps.InfoWindow;
    }

    /** The Marker library module returned by importLibrary("marker"). */
    interface MarkerLibrary {
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      AdvancedMarkerElement: typeof google.maps.marker.AdvancedMarkerElement;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      PinElement: typeof google.maps.marker.PinElement;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      Marker: typeof google.maps.Marker;
    }

    /** The Places library module returned by importLibrary("places"). */
    interface PlacesLibrary {
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      Autocomplete: typeof google.maps.places.Autocomplete;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      AutocompleteService: typeof google.maps.places.AutocompleteService;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      AutocompleteSessionToken: typeof google.maps.places.AutocompleteSessionToken;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      PlacesService: typeof google.maps.places.PlacesService;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      SearchBox: typeof google.maps.places.SearchBox;
      /**
       * AutocompleteSuggestion class for the new Places Autocomplete Data API.
       * Runtime type - not fully typed in @types/google.maps.
       */
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      AutocompleteSuggestion: AutocompleteSuggestionConstructor;
      /**
       * Place class for the new Places API.
       * Runtime type - not fully typed in @types/google.maps.
       */
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      Place: PlaceConstructor;
    }

    /** The Geometry library module returned by importLibrary("geometry"). */
    interface GeometryLibrary {
      encoding: typeof google.maps.geometry.encoding;
      poly: typeof google.maps.geometry.poly;
      spherical: typeof google.maps.geometry.spherical;
    }

    /** The Drawing library module returned by importLibrary("drawing"). */
    interface DrawingLibrary {
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      DrawingManager: typeof google.maps.drawing.DrawingManager;
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      OverlayType: typeof google.maps.drawing.OverlayType;
    }

    /** The Visualization library module returned by importLibrary("visualization"). */
    interface VisualizationLibrary {
      // biome-ignore lint/style/useNamingConvention: Google Maps API property
      HeatmapLayer: typeof google.maps.visualization.HeatmapLayer;
    }
  }
}

/**
 * AutocompleteSuggestion constructor interface.
 * @see https://developers.google.com/maps/documentation/javascript/place-autocomplete-data
 */
interface AutocompleteSuggestionConstructor {
  fetchAutocompleteSuggestions(
    request: AutocompleteSuggestionRequest
  ): Promise<AutocompleteSuggestionResponse>;
}

/** Request object for fetchAutocompleteSuggestions. */
interface AutocompleteSuggestionRequest {
  input: string;
  sessionToken?: google.maps.places.AutocompleteSessionToken;
  locationRestriction?: {
    east: number;
    north: number;
    south: number;
    west: number;
  };
  locationBias?: google.maps.LatLng | google.maps.LatLngBounds;
  includedPrimaryTypes?: string[];
  includedRegionCodes?: string[];
  language?: string;
  origin?: google.maps.LatLng;
}

/** Response object from fetchAutocompleteSuggestions. */
interface AutocompleteSuggestionResponse {
  suggestions: AutocompleteSuggestion[];
}

/** Individual autocomplete suggestion. */
interface AutocompleteSuggestion {
  placePrediction: PlacePrediction;
}

/** Place prediction from autocomplete. */
interface PlacePrediction {
  placeId: string;
  text: FormattableText;
  structuredFormat?: {
    mainText: FormattableText;
    secondaryText: FormattableText;
  };
  types?: string[];
  distanceMeters?: number;
  toPlace(): PlaceInstance;
}

/** Formattable text with highlighting support. */
interface FormattableText {
  text: string;
  matches?: Array<{ startOffset: number; endOffset: number }>;
  toString(): string;
}

/**
 * Place constructor interface.
 * @see https://developers.google.com/maps/documentation/javascript/place-class
 */
interface PlaceConstructor {
  new (options: { id: string; requestedLanguage?: string }): PlaceInstance;
  searchNearby(request: SearchNearbyRequest): Promise<{ places: PlaceInstance[] }>;
  searchByText(request: SearchByTextRequest): Promise<{ places: PlaceInstance[] }>;
}

/** Place instance with fetched data. */
interface PlaceInstance {
  id: string;
  displayName?: { text: string; languageCode?: string };
  formattedAddress?: string;
  location?: google.maps.LatLng;
  viewport?: google.maps.LatLngBounds;
  types?: string[];
  photos?: PlacePhoto[];
  priceLevel?: string;
  rating?: number;
  userRatingCount?: number;
  businessStatus?: string;
  openingHours?: PlaceOpeningHours;
  // biome-ignore lint/style/useNamingConvention: Google Maps API property
  websiteURI?: string;
  nationalPhoneNumber?: string;
  internationalPhoneNumber?: string;
  reviews?: PlaceReview[];
  fetchFields(options: { fields: string[] }): Promise<void>;
}

/** Request for searchNearby. */
interface SearchNearbyRequest {
  fields: string[];
  locationRestriction: {
    center: google.maps.LatLng | { lat: number; lng: number };
    radius: number;
  };
  includedTypes?: string[];
  excludedTypes?: string[];
  maxResultCount?: number;
  rankPreference?: "DISTANCE" | "POPULARITY";
}

/** Request for searchByText. */
interface SearchByTextRequest {
  fields: string[];
  textQuery: string;
  locationBias?: google.maps.LatLng | google.maps.LatLngBounds;
  includedType?: string;
  maxResultCount?: number;
  isOpenNow?: boolean;
  minRating?: number;
  priceLevels?: string[];
}

/** Place photo from the Places API. */
interface PlacePhoto {
  // biome-ignore lint/style/useNamingConvention: Google Maps API property
  getURI(options?: { maxWidth?: number; maxHeight?: number }): string;
  authorAttributions: PlaceAttribution[];
  widthPx: number;
  heightPx?: number;
}

/** Attribution for photos and reviews. */
interface PlaceAttribution {
  displayName: string;
  uri?: string;
  // biome-ignore lint/style/useNamingConvention: Google Maps API property
  photoURI?: string;
}

/** Opening hours information. */
interface PlaceOpeningHours {
  periods: PlaceOpeningHoursPeriod[];
  weekdayDescriptions: string[];
}

/** Single opening hours period. */
interface PlaceOpeningHoursPeriod {
  open: PlaceOpeningHoursPoint;
  close?: PlaceOpeningHoursPoint;
}

/** Time point for opening hours. */
interface PlaceOpeningHoursPoint {
  day: number;
  hour: number;
  minute: number;
}

/** User review for a place. */
interface PlaceReview {
  authorAttribution: PlaceAttribution;
  rating?: number;
  relativePublishTimeDescription?: string;
  text?: { text: string; languageCode?: string };
  publishTime?: string;
}

// Re-export types for use in components
declare global {
  export type {
    AutocompleteSuggestion,
    AutocompleteSuggestionRequest,
    AutocompleteSuggestionResponse,
    FormattableText,
    PlaceAttribution,
    PlaceInstance,
    PlaceOpeningHours,
    PlaceOpeningHoursPeriod,
    PlaceOpeningHoursPoint,
    PlacePhoto,
    PlacePrediction,
    PlaceReview,
    SearchByTextRequest,
    SearchNearbyRequest,
  };
}
