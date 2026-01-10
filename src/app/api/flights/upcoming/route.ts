/**
 * @fileoverview GET /api/flights/upcoming route handler.
 */

import "server-only";

import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { nowIso } from "@/lib/security/random";
import type { Json } from "@/lib/supabase/database.types";

type UpcomingFlightStatus = "upcoming" | "boarding" | "delayed" | "cancelled";

type UpcomingFlight = {
  id: string;
  tripId?: string;
  tripName?: string;
  airline: string;
  airlineName: string;
  flightNumber: string;
  origin: string;
  destination: string;
  departureTime: string;
  arrivalTime: string;
  duration: number;
  stops: number;
  price: number;
  currency: string;
  cabinClass: string;
  seatsAvailable?: number;
  status: UpcomingFlightStatus;
  terminal?: string;
  gate?: string;
};

type FlightRow = {
  airline: string | null;
  currency: string;
  departure_date: string;
  destination: string;
  flight_class: string;
  flight_number: string | null;
  id: number;
  metadata: Json | null;
  origin: string;
  price: number;
  return_date: string | null;
  trip_id: number;
};

const DEFAULT_LIMIT = 3;
const MAX_LIMIT = 20;

function parseLimit(raw: string | null): number {
  const parsed = raw ? Number.parseInt(raw, 10) : Number.NaN;
  if (!Number.isFinite(parsed) || parsed <= 0) return DEFAULT_LIMIT;
  return Math.min(MAX_LIMIT, parsed);
}

function asRecord(value: Json | null): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function normalizeStatus(value: unknown): UpcomingFlightStatus {
  if (typeof value !== "string") return "upcoming";
  switch (value) {
    case "boarding":
    case "delayed":
    case "cancelled":
    case "upcoming":
      return value;
    default:
      return "upcoming";
  }
}

function toUpcomingFlight(row: FlightRow): UpcomingFlight {
  const metadata = asRecord(row.metadata);
  const airline = row.airline?.trim() ?? "Unknown";
  const airlineName =
    typeof metadata?.airlineName === "string" && metadata.airlineName.trim().length > 0
      ? metadata.airlineName.trim()
      : airline;
  const flightNumber =
    row.flight_number?.trim().length && row.flight_number.trim().length > 0
      ? row.flight_number.trim()
      : "TBD";
  const arrivalTime =
    typeof metadata?.arrivalTime === "string" && metadata.arrivalTime.trim().length > 0
      ? metadata.arrivalTime
      : (row.return_date ?? row.departure_date);
  const duration =
    typeof metadata?.duration === "number" && Number.isFinite(metadata.duration)
      ? Math.max(0, Math.round(metadata.duration))
      : 0;
  const stops =
    typeof metadata?.stops === "number" && Number.isFinite(metadata.stops)
      ? Math.max(0, Math.round(metadata.stops))
      : 0;
  const status = normalizeStatus(metadata?.status);

  return {
    airline,
    airlineName,
    arrivalTime,
    cabinClass: row.flight_class,
    currency: row.currency,
    departureTime: row.departure_date,
    destination: row.destination,
    duration,
    flightNumber,
    gate: typeof metadata?.gate === "string" ? metadata.gate : undefined,
    id: String(row.id),
    origin: row.origin,
    price: row.price,
    seatsAvailable:
      typeof metadata?.seatsAvailable === "number" &&
      Number.isFinite(metadata.seatsAvailable)
        ? Math.max(0, Math.round(metadata.seatsAvailable))
        : undefined,
    status,
    stops,
    terminal: typeof metadata?.terminal === "string" ? metadata.terminal : undefined,
    tripId: row.trip_id ? String(row.trip_id) : undefined,
    tripName:
      typeof metadata?.tripName === "string" && metadata.tripName.trim().length > 0
        ? metadata.tripName
        : undefined,
  };
}

export const GET = withApiGuards({
  auth: true,
  rateLimit: "flights:upcoming",
  telemetry: "flights.upcoming",
})(async (req, { supabase, user }) => {
  const auth = requireUserId(user);
  if (!auth.ok) return auth.error;

  const limit = parseLimit(req.nextUrl.searchParams.get("limit"));

  const { data, error } = await supabase
    .from("flights")
    .select(
      "airline,currency,departure_date,destination,flight_class,flight_number,id,metadata,origin,price,return_date,trip_id"
    )
    .eq("user_id", auth.data)
    .gte("departure_date", nowIso())
    .order("departure_date", { ascending: true })
    .limit(limit)
    .returns<FlightRow[]>();

  if (error) {
    return errorResponse({
      err: error,
      error: "upcoming_flights_failed",
      reason: "Failed to load upcoming flights",
      status: 500,
    });
  }

  return Response.json((data ?? []).map(toUpcomingFlight));
});
