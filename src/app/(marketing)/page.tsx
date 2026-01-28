/**
 * @fileoverview TripSage AI marketing homepage route.
 */

import type { Metadata } from "next";
import { MarketingHome } from "@/components/marketing/marketing-home";

/** Metadata for the TripSage AI marketing homepage. */
export const metadata: Metadata = {
  description:
    "TripSage AI helps you plan smarter trips with personalized recommendations, budget guardrails, and an itinerary you can actually follow.",
  title: "TripSage AI - Intelligent Travel Planning",
};

/**
 * Marketing homepage route.
 *
 * @returns The marketing homepage layout.
 */
export default function Home() {
  return <MarketingHome />;
}
