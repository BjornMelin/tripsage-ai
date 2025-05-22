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
export interface FlightSearchParams extends BaseSearchParams {
  origin: string;
  cabinClass: 'economy' | 'premium_economy' | 'business' | 'first';
  directOnly: boolean;
  maxStops?: number;
  preferredAirlines?: string[];
  departureTime?: 'morning' | 'afternoon' | 'evening' | 'night';
  returnTime?: 'morning' | 'afternoon' | 'evening' | 'night';
}

// Accommodation specific search parameters
export interface AccommodationSearchParams extends BaseSearchParams {
  rooms: number;
  amenities?: string[];
  propertyType?: string[];
  priceRange?: {
    min: number;
    max: number;
  };
  rating?: number;
  distance?: number;
}

// Activity specific search parameters
export interface ActivitySearchParams extends BaseSearchParams {
  categories?: string[];
  duration?: number;
  priceRange?: {
    min: number;
    max: number;
  };
  rating?: number;
}

// Union type for all search parameters
export type SearchParams = 
  | FlightSearchParams 
  | AccommodationSearchParams 
  | ActivitySearchParams;

// Search type
export type SearchType = 'flight' | 'accommodation' | 'activity';

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

// Union type for all search results
export type SearchResult = Flight | Accommodation | Activity;

// Search results grouped by type
export interface SearchResults {
  flights?: Flight[];
  accommodations?: Accommodation[];
  activities?: Activity[];
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
  type: 'checkbox' | 'radio' | 'range' | 'select';
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
  direction: 'asc' | 'desc';
}