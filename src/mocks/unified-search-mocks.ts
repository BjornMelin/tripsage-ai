/**
 * @fileoverview Demo mock results for unified search.
 *
 * These mocks are intentionally not imported at module scope by UI components.
 * Load them dynamically behind `process.env.NODE_ENV === "development"` guards.
 */

import type { FlightResult, HotelResult } from "@schemas/search";

export const MOCK_FLIGHT_RESULTS = [
  {
    aircraft: "Boeing 787",
    airline: "Delta Airlines",
    amenities: ["wifi", "meals", "entertainment"],
    arrival: { date: "2025-06-15", time: "10:45 PM" },
    departure: { date: "2025-06-15", time: "10:30 AM" },
    destination: { city: "London", code: "LHR", terminal: "3" },
    duration: 420,
    emissions: { compared: "low" as const, kg: 850 },
    flexibility: { changeable: true, cost: 50, refundable: false },
    flightNumber: "DL 128",
    id: "flight-1",
    origin: { city: "New York", code: "JFK", terminal: "4" },
    prediction: {
      confidence: 89,
      priceAlert: "buy_now" as const,
      reason: "Prices trending up for this route",
    },
    price: {
      base: 599,
      currency: "USD",
      dealScore: 9,
      priceChange: "down" as const,
      total: 699,
    },
    promotions: {
      description: "Flash Deal - 24hrs only",
      savings: 150,
      type: "flash_deal" as const,
    },
    stops: { cities: [], count: 0 },
  },
  {
    aircraft: "Airbus A350",
    airline: "United Airlines",
    amenities: ["wifi", "entertainment"],
    arrival: { date: "2025-06-16", time: "1:35 AM" },
    departure: { date: "2025-06-15", time: "1:15 PM" },
    destination: { city: "London", code: "LHR", terminal: "2" },
    duration: 440,
    emissions: { compared: "average" as const, kg: 920 },
    flexibility: { changeable: true, cost: 0, refundable: true },
    flightNumber: "UA 901",
    id: "flight-2",
    origin: { city: "New York", code: "JFK", terminal: "7" },
    prediction: {
      confidence: 72,
      priceAlert: "neutral" as const,
      reason: "Stable pricing expected",
    },
    price: {
      base: 649,
      currency: "USD",
      dealScore: 7,
      priceChange: "stable" as const,
      total: 749,
    },
    stops: { cities: [], count: 0 },
  },
] satisfies readonly FlightResult[];

export const MOCK_HOTEL_RESULTS = [
  {
    ai: {
      personalizedTags: ["luxury", "city-center", "business"],
      reason: "Perfect for luxury seekers with prime location",
      recommendation: 9,
    },
    allInclusive: {
      available: false,
      inclusions: [],
      tier: "basic" as const,
    },
    amenities: {
      essential: ["wifi", "breakfast", "gym", "spa"],
      premium: ["concierge", "butler"],
      unique: ["central-park-view"],
    },
    availability: {
      flexible: true,
      roomsLeft: 3,
      urgency: "high" as const,
    },
    brand: "Ritz-Carlton",
    category: "hotel" as const,
    guestExperience: {
      highlights: ["Exceptional service with Central Park views"],
      recentMentions: ["Outstanding breakfast", "Perfect location"],
      vibe: "luxury" as const,
    },
    id: "hotel-1",
    images: {
      count: 24,
      gallery: [],
      main: "/hotel-1.jpg",
    },
    location: {
      address: "50 Central Park South",
      city: "New York",
      district: "Midtown",
      landmarks: ["Central Park", "Times Square"],
      walkScore: 95,
    },
    name: "The Ritz-Carlton New York",
    pricing: {
      basePrice: 450,
      currency: "USD",
      deals: {
        description: "Early Bird - Book 30 days ahead",
        originalPrice: 525,
        savings: 75,
        type: "early_bird" as const,
      },
      priceHistory: "falling" as const,
      pricePerNight: 450,
      taxes: 85,
      taxesEstimated: false,
      totalPrice: 1350,
    },
    reviewCount: 2847,
    starRating: 5,
    sustainability: {
      certified: true,
      practices: ["solar-power", "recycling", "local-sourcing"],
      score: 8,
    },
    userRating: 4.8,
  },
  {
    ai: {
      personalizedTags: ["budget", "city-center", "modern"],
      reason: "Great value in prime location for business travelers",
      recommendation: 7,
    },
    allInclusive: {
      available: false,
      inclusions: [],
      tier: "basic" as const,
    },
    amenities: {
      essential: ["wifi", "gym"],
      premium: [],
      unique: ["pod-design", "rooftop-bar"],
    },
    availability: {
      flexible: true,
      roomsLeft: 12,
      urgency: "low" as const,
    },
    brand: "Pod Hotels",
    category: "hotel" as const,
    guestExperience: {
      highlights: ["Modern pod-style rooms in heart of Times Square"],
      recentMentions: ["Great location", "Clean and efficient"],
      vibe: "business" as const,
    },
    id: "hotel-2",
    images: {
      count: 18,
      gallery: [],
      main: "/hotel-2.jpg",
    },
    location: {
      address: "400 W 42nd St",
      city: "New York",
      district: "Times Square",
      landmarks: ["Times Square", "Broadway"],
      walkScore: 100,
    },
    name: "Pod Hotels Times Square",
    pricing: {
      basePrice: 189,
      currency: "USD",
      priceHistory: "rising" as const,
      pricePerNight: 189,
      taxes: 35,
      taxesEstimated: false,
      totalPrice: 567,
    },
    reviewCount: 1893,
    starRating: 3,
    sustainability: {
      certified: false,
      practices: ["energy-efficient"],
      score: 6,
    },
    userRating: 4.2,
  },
] satisfies readonly HotelResult[];
