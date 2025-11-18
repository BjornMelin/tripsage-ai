/**
 * @fileoverview Dashboard metrics API route handler.
 */

"use server";

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import type { TypedServerSupabase } from "@/lib/supabase/server";

/**
 * Returns dashboard metrics based on trip statistics.
 *
 * @param supabase - Supabase client
 * @param _req - Next.js request object
 * @returns Response with dashboard metrics
 */
async function getDashboardMetrics(
  supabase: TypedServerSupabase,
  _req: NextRequest
): Promise<NextResponse> {
  // TODO: Implement proper API usage logging and metrics collection.
  // Currently returns basic trip counts as placeholder dashboard metrics.
  const { data: trips, error } = await supabase
    .from("trips")
    .select("id, status, created_at");

  if (error) {
    return NextResponse.json(
      { error: "Failed to load dashboard metrics" },
      { status: 500 }
    );
  }

  const tripData = trips ?? [];
  const totalTrips = tripData.length;
  const completedTrips = tripData.filter((trip) => trip.status === "completed").length;
  const activeTrips = tripData.filter(
    (trip) => trip.status === "planning" || trip.status === "booked"
  ).length;

  return NextResponse.json({
    activeTrips,
    avgLatencyMs: 0,
    completedTrips,
    errorRate: 0,
    totalRequests: totalTrips,
    totalTrips,
  });
}

/**
 * GET /api/dashboard
 *
 * Returns dashboard metrics based on trip statistics.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "dashboard:metrics",
  telemetry: "dashboard.metrics",
})(async (req, { supabase }) => getDashboardMetrics(supabase, req));
