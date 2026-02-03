/**
 * @fileoverview Web app manifest metadata route.
 */

import type { MetadataRoute } from "next";

/**
 * Web app manifest metadata route.
 * @returns The web app manifest metadata.
 */
export default function manifest(): MetadataRoute.Manifest {
  const name = process.env.NEXT_PUBLIC_APP_NAME?.trim() || "TripSage AI";

  return {
    // biome-ignore lint/complexity/useLiteralKeys: Manifest fields are snake_case per spec.
    ["background_color"]: "#0b0b0f",
    description: "Plan smarter trips with AI-powered recommendations and itineraries.",
    display: "standalone",
    icons: [
      {
        sizes: "any",
        src: "/favicon.ico",
        type: "image/x-icon",
      },
    ],
    name,
    // biome-ignore lint/complexity/useLiteralKeys: Manifest fields are snake_case per spec.
    ["short_name"]: name,
    // biome-ignore lint/complexity/useLiteralKeys: Manifest fields are snake_case per spec.
    ["start_url"]: "/",
    // biome-ignore lint/complexity/useLiteralKeys: Manifest fields are snake_case per spec.
    ["theme_color"]: "#0b0b0f",
  };
}
