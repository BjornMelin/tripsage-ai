/**
 * @fileoverview Accommodation tools – prefers MCP (Airbnb). For booking, requires approval.
 */

import { tool } from "ai";
import { z } from "zod";
import { requireApproval } from "./approvals";

export const searchAccommodations = tool({
  description: "Search accommodations (Airbnb MCP proxy or custom endpoint).",
  execute: async ({ location, checkin, checkout, guests, priceMin, priceMax }) => {
    const base = process.env.ACCOM_SEARCH_URL || process.env.AIRBNB_MCP_URL;
    const token = process.env.ACCOM_SEARCH_TOKEN || process.env.AIRBNB_MCP_API_KEY;
    if (!base) throw new Error("accom_search_not_configured");
    const url = new URL(base);
    url.searchParams.set("location", location);
    url.searchParams.set("checkin", checkin);
    url.searchParams.set("checkout", checkout);
    url.searchParams.set("guests", String(guests));
    if (priceMin !== undefined) url.searchParams.set("priceMin", String(priceMin));
    if (priceMax !== undefined) url.searchParams.set("priceMax", String(priceMax));
    const res = await fetch(url, {
      headers: token ? { authorization: `Bearer ${token}` } : undefined,
    });
    if (!res.ok) throw new Error(`accom_search_failed:${res.status}`);
    return await res.json();
  },
  inputSchema: z.object({
    checkin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    checkout: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    guests: z.number().int().min(1).max(16).default(1),
    location: z.string().min(2),
    priceMax: z.number().optional(),
    priceMin: z.number().optional(),
  }),
});

export const bookAccommodation = tool({
  description: "Book an accommodation (requires user approval).",
  execute: async ({ listingId, checkin, checkout, guests, sessionId }) => {
    // Approval gate
    await requireApproval("bookAccommodation", { sessionId });

    // In a full implementation, call the MCP "book" tool or provider API here.
    // For safety, return a structured booking intent with echo of inputs.
    return {
      checkin,
      checkout,
      guests,
      listingId,
      message: "Booking request created. Provider confirmation pending.",
      reference: `bk_${Math.random().toString(36).slice(2, 10)}`,
      status: "pending_confirmation",
    } as const;
  },
  inputSchema: z.object({
    checkin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    checkout: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    guests: z.number().int().min(1).max(16).default(1),
    listingId: z.string().min(1),
    sessionId: z.string().min(6),
  }),
});
