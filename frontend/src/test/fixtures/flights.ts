import type { UpcomingFlight } from "@/hooks/use-trips";

export const UPCOMING_FLIGHT_A: UpcomingFlight = {
  airline: "NH",
  airlineName: "ANA",
  arrivalTime: "2025-01-15T14:20:00Z",
  cabinClass: "economy",
  currency: "USD",
  departureTime: "2025-01-15T10:00:00Z",
  destination: "HND",
  duration: 420,
  flightNumber: "NH203",
  id: "f1",
  origin: "NRT",
  price: 999,
  status: "upcoming",
  stops: 0,
};

export const UPCOMING_FLIGHT_B: UpcomingFlight = {
  airline: "UA",
  airlineName: "United",
  arrivalTime: "2025-01-10T16:30:00Z",
  cabinClass: "business",
  currency: "USD",
  departureTime: "2025-01-10T12:00:00Z",
  destination: "SFO",
  duration: 720,
  flightNumber: "UA837",
  id: "f2",
  origin: "NRT",
  price: 1200,
  status: "upcoming",
  stops: 0,
};
