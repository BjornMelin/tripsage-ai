/**
 * @fileoverview Default Open Graph image for social previews.
 */

import { ImageResponse } from "next/og";

/** Alt text for the Open Graph image. */
export const alt = "TripSage AI";

/** Dimensions for the Open Graph image (1200×630 standard). */
export const size = { height: 630, width: 1200 };

/** MIME type for the generated image. */
export const contentType = "image/png";

/**
 * Generates the default Open Graph image for social previews.
 *
 * @returns The rendered Open Graph ImageResponse.
 */
export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        alignItems: "center",
        background:
          "linear-gradient(135deg, rgba(79,70,229,1) 0%, rgba(17,24,39,1) 55%, rgba(0,0,0,1) 100%)",
        color: "white",
        display: "flex",
        height: "100%",
        justifyContent: "center",
        width: "100%",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 18,
          maxWidth: 980,
          padding: 64,
        }}
      >
        <div style={{ fontSize: 72, fontWeight: 800, letterSpacing: -2 }}>
          TripSage AI
        </div>
        <div style={{ fontSize: 34, opacity: 0.92 }}>
          Intelligent travel planning with personalized recommendations, budgets, and
          itineraries.
        </div>
        <div style={{ fontSize: 22, opacity: 0.8 }}>tripsage.ai</div>
      </div>
    </div>,
    size
  );
}
