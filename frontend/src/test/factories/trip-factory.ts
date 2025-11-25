/**
 * @fileoverview Factory for creating Trip and related test data.
 */

let tripIdCounter = 1;
let flightIdCounter = 1;
let hotelIdCounter = 1;

export interface TripOverrides {
  id?: string;
  userId?: string;
  destination?: string;
  startDate?: string;
  endDate?: string;
  budget?: number;
  currency?: string;
  status?: "planning" | "booked" | "completed" | "cancelled";
  createdAt?: string;
  updatedAt?: string;
  title?: string;
  travelers?: number;
  tripType?: "leisure" | "business" | "family" | "solo" | "other";
}

export interface FlightOverrides {
  id?: string;
  tripId?: string;
  airline?: string;
  flightNumber?: string;
  departureAirport?: string;
  arrivalAirport?: string;
  departureTime?: string;
  arrivalTime?: string;
  price?: number;
  currency?: string;
  bookingReference?: string;
}

export interface HotelOverrides {
  id?: string;
  tripId?: string;
  name?: string;
  address?: string;
  checkInDate?: string;
  checkOutDate?: string;
  pricePerNight?: number;
  currency?: string;
  bookingReference?: string;
  rating?: number;
}

/**
 * Creates a mock Trip with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete Trip object
 */
export const createTrip = (
  overrides: TripOverrides = {}
): TripOverrides & { id: string } => {
  const id = overrides.id ?? `trip-${tripIdCounter++}`;
  const startDate =
    overrides.startDate ?? new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
  const endDate =
    overrides.endDate ?? new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString();

  return {
    budget: overrides.budget ?? 2000,
    createdAt: overrides.createdAt ?? new Date().toISOString(),
    currency: overrides.currency ?? "USD",
    destination: overrides.destination ?? "New York",
    endDate,
    id,
    startDate,
    status: overrides.status ?? "planning",
    title: overrides.title ?? "Test Trip",
    travelers: overrides.travelers ?? 1,
    tripType: overrides.tripType ?? "leisure",
    updatedAt: overrides.updatedAt ?? new Date().toISOString(),
    userId: overrides.userId ?? "user-1",
  };
};

/**
 * Creates a mock Flight with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete Flight object
 */
export const createFlight = (
  overrides: FlightOverrides = {}
): FlightOverrides & { id: string } => {
  const id = overrides.id ?? `flight-${flightIdCounter++}`;
  const departureTime =
    overrides.departureTime ??
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
  const arrivalTime =
    overrides.arrivalTime ??
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000 + 3 * 60 * 60 * 1000).toISOString();

  return {
    airline: overrides.airline ?? "Test Airlines",
    arrivalAirport: overrides.arrivalAirport ?? "LAX",
    arrivalTime,
    bookingReference: overrides.bookingReference ?? `BR${id}`,
    currency: overrides.currency ?? "USD",
    departureAirport: overrides.departureAirport ?? "JFK",
    departureTime,
    flightNumber: overrides.flightNumber ?? "TA123",
    id,
    price: overrides.price ?? 500,
    tripId: overrides.tripId ?? "trip-1",
  };
};

/**
 * Creates a mock Hotel booking with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete Hotel object
 */
export const createHotel = (
  overrides: HotelOverrides = {}
): HotelOverrides & { id: string } => {
  const id = overrides.id ?? `hotel-${hotelIdCounter++}`;
  const checkIn =
    overrides.checkInDate ??
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
  const checkOut =
    overrides.checkOutDate ??
    new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString();

  return {
    address: overrides.address ?? "123 Test Street, Test City",
    bookingReference: overrides.bookingReference ?? `HR${id}`,
    checkInDate: checkIn,
    checkOutDate: checkOut,
    currency: overrides.currency ?? "USD",
    id,
    name: overrides.name ?? "Test Hotel",
    pricePerNight: overrides.pricePerNight ?? 150,
    rating: overrides.rating ?? 4.5,
    tripId: overrides.tripId ?? "trip-1",
  };
};

/**
 * Creates multiple trips at once.
 *
 * @param count - Number of trips to create
 * @param overridesFn - Optional function to customize each trip (receives index)
 * @returns Array of Trip objects
 */
export const createTrips = (
  count: number,
  overridesFn?: (index: number) => TripOverrides
): Array<TripOverrides & { id: string }> => {
  return Array.from({ length: count }, (_, i) =>
    createTrip(overridesFn ? overridesFn(i) : {})
  );
};

/**
 * Resets all trip-related ID counters for deterministic test data.
 */
export const resetTripFactory = (): void => {
  tripIdCounter = 1;
  flightIdCounter = 1;
  hotelIdCounter = 1;
};
