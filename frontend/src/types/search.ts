/**
 * Types for Search functionality
 */

// Base search parameters interface
export interface BaseSearchParams {
  destination: string;
  startDate: string;
  endDate: string;
  adults: number;
  children: number;
  infants: number;
}

// Flight specific search parameters
export interface FlightSearchParams {
  origin?: string;
  destination?: string;
  departureDate?: string;
  returnDate?: string;
  cabinClass?: "economy" | "premium_economy" | "business" | "first";
  directOnly?: boolean;
  maxStops?: number;
  preferredAirlines?: string[];
  excludedAirlines?: string[];
  adults?: number;
  children?: number;
  infants?: number;
}

// Accommodation specific search parameters
export interface AccommodationSearchParams {
  destination?: string;
  checkIn?: string;
  checkOut?: string;
  rooms?: number;
  amenities?: string[];
  propertyType?: "hotel" | "apartment" | "villa" | "hostel" | "resort";
  priceRange?: {
    min?: number;
    max?: number;
  };
  minRating?: number;
  adults?: number;
  children?: number;
  infants?: number;
}

// Activity specific search parameters
export interface ActivitySearchParams {
  destination?: string;
  date?: string;
  category?: string;
  duration?: {
    min?: number;
    max?: number;
  };
  difficulty?: "easy" | "moderate" | "challenging" | "extreme";
  indoor?: boolean;
  adults?: number;
  children?: number;
  infants?: number;
}

// Destination specific search parameters
export interface DestinationSearchParams {
  query: string;
  types?: ("locality" | "country" | "administrative_area" | "establishment")[];
  language?: string;
  region?: string;
  components?: {
    country?: string[];
  };
  limit?: number;
}

// Union type for all search parameters
export type SearchParams =
  | FlightSearchParams
  | AccommodationSearchParams
  | ActivitySearchParams
  | DestinationSearchParams;

// Search type
export type SearchType = "flight" | "accommodation" | "activity" | "destination";

// Flight search result
export interface Flight {
  id: string;
  airline: string;
  flightNumber: string;
  origin: string;
  destination: string;
  departureTime: string;
  arrivalTime: string;
  duration: number;
  stops: number;
  price: number;
  cabinClass: string;
  seatsAvailable: number;
  layovers?: Array<{
    airport: string;
    duration: number;
  }>;
}

// Accommodation search result
export interface Accommodation {
  id: string;
  name: string;
  type: string;
  location: string;
  checkIn: string;
  checkOut: string;
  pricePerNight: number;
  totalPrice: number;
  rating: number;
  amenities: string[];
  images: string[];
  coordinates?: {
    lat: number;
    lng: number;
  };
}

// Activity search result
export interface Activity {
  id: string;
  name: string;
  type: string;
  location: string;
  date: string;
  duration: number;
  price: number;
  rating: number;
  description: string;
  images: string[];
  coordinates?: {
    lat: number;
    lng: number;
  };
}

// Destination search result
export interface Destination {
  id: string;
  name: string;
  description: string;
  formattedAddress: string;
  types: string[];
  coordinates: {
    lat: number;
    lng: number;
  };
  photos?: string[];
  placeId?: string;
  country?: string;
  region?: string;
  rating?: number;
  popularityScore?: number;
  climate?: {
    season: string;
    averageTemp: number;
    rainfall: number;
  };
  attractions?: string[];
  bestTimeToVisit?: string[];
}

// Union type for all search results
export type SearchResult = Flight | Accommodation | Activity | Destination;

// Search results grouped by type
export interface SearchResults {
  flights?: Flight[];
  accommodations?: Accommodation[];
  activities?: Activity[];
  destinations?: Destination[];
}

// Saved search
export interface SavedSearch {
  id: string;
  type: SearchType;
  name: string;
  params: SearchParams;
  createdAt: string;
  lastUsed?: string;
}

// Filter value type
export type FilterValue = string | number | boolean | string[] | number[];

// Metadata value type
export type MetadataValue = string | number | boolean | Record<string, unknown>;

// Search response from API
export interface SearchResponse {
  results: SearchResults;
  totalResults: number;
  filters?: Record<string, FilterValue>;
  metadata?: Record<string, MetadataValue>;
}

// Filter option
export interface FilterOption {
  id: string;
  label: string;
  value: FilterValue;
  type: "checkbox" | "radio" | "range" | "select";
  count?: number;
  options?: Array<{
    label: string;
    value: FilterValue;
    count?: number;
  }>;
}

// Sort option
export interface SortOption {
  id: string;
  label: string;
  value: string;
  direction: "asc" | "desc";
}
