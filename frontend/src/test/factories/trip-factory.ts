/**
 * @fileoverview Factory for creating Trip and related test data.
 */

let tripIdCounter = 1;
let flightIdCounter = 1;
let hotelIdCounter = 1;

export interface TripOverrides {
  id?: string;
  user_id?: string;
  destination?: string;
  start_date?: string;
  end_date?: string;
  budget?: number;
  status?: "planning" | "booked" | "completed" | "cancelled";
  created_at?: string;
  updated_at?: string;
}

export interface FlightOverrides {
  id?: string;
  trip_id?: string;
  airline?: string;
  flight_number?: string;
  departure_airport?: string;
  arrival_airport?: string;
  departure_time?: string;
  arrival_time?: string;
  price?: number;
  currency?: string;
  booking_reference?: string;
}

export interface HotelOverrides {
  id?: string;
  trip_id?: string;
  name?: string;
  address?: string;
  check_in_date?: string;
  check_out_date?: string;
  price_per_night?: number;
  currency?: string;
  booking_reference?: string;
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
    overrides.start_date ??
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
  const endDate =
    overrides.end_date ?? new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString();

  return {
    budget: overrides.budget ?? 2000,
    created_at: overrides.created_at ?? new Date().toISOString(),
    destination: overrides.destination ?? "New York",
    end_date: endDate,
    id,
    start_date: startDate,
    status: overrides.status ?? "planning",
    updated_at: overrides.updated_at ?? new Date().toISOString(),
    user_id: overrides.user_id ?? "user-1",
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
    overrides.departure_time ??
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
  const arrivalTime =
    overrides.arrival_time ??
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000 + 3 * 60 * 60 * 1000).toISOString();

  return {
    airline: overrides.airline ?? "Test Airlines",
    arrival_airport: overrides.arrival_airport ?? "LAX",
    arrival_time: arrivalTime,
    booking_reference: overrides.booking_reference ?? `BR${id}`,
    currency: overrides.currency ?? "USD",
    departure_airport: overrides.departure_airport ?? "JFK",
    departure_time: departureTime,
    flight_number: overrides.flight_number ?? "TA123",
    id,
    price: overrides.price ?? 500,
    trip_id: overrides.trip_id ?? "trip-1",
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
    overrides.check_in_date ??
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
  const checkOut =
    overrides.check_out_date ??
    new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString();

  return {
    address: overrides.address ?? "123 Test Street, Test City",
    booking_reference: overrides.booking_reference ?? `HR${id}`,
    check_in_date: checkIn,
    check_out_date: checkOut,
    currency: overrides.currency ?? "USD",
    id,
    name: overrides.name ?? "Test Hotel",
    price_per_night: overrides.price_per_night ?? 150,
    rating: overrides.rating ?? 4.5,
    trip_id: overrides.trip_id ?? "trip-1",
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
