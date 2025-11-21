/**
 * @fileoverview System prompt builders for agent workflows.
 *
 * Constructs system instructions for destination research, itinerary planning,
 * flight search, accommodation search, budget planning, and router classification
 * agents. Prompts include context from user requests and optional metadata.
 */

import type {
  BudgetPlanRequest,
  DestinationResearchRequest,
  ItineraryPlanRequest,
} from "@schemas/agents";
import type { FlightSearchRequest } from "@schemas/flights";

/**
 * Base context shared across prompt builders.
 *
 * Optional metadata that can be included in any agent prompt for
 * personalization and context.
 */
type BasePromptContext = {
  userName?: string;
  locale?: string;
  travelStyle?: string;
  safetySummary?: string;
};

/**
 * Input type for destination research prompt builder.
 *
 * Combines base context, destination research request parameters, and
 * optional provider summary for external findings.
 */
export type DestinationPromptInput = BasePromptContext &
  DestinationResearchRequest & {
    providerSummary?: string;
  };

/**
 * Build system prompt for destination research agent.
 *
 * Constructs instructions for researching a destination, including travel
 * style, dates, interests, safety context, and external provider findings.
 *
 * @param input - Destination research request with optional context and provider summary.
 * @returns System prompt string for the destination research agent.
 */
export function buildDestinationPrompt(input: DestinationPromptInput): string {
  const style = input.travelStyle ?? "balanced";
  const locale = input.locale ?? "en-US";
  const intro = `You are TripSage's destination researcher. Respond in ${locale} with concise, helpful travel insights.`;
  const safetyFragment = input.safetySummary
    ? `Incorporate safety context: ${input.safetySummary}.`
    : "";
  const providerFragment = input.providerSummary
    ? `Supplement recommendations with these external findings: ${input.providerSummary}`
    : "";

  return [
    intro,
    `Focus destination: ${input.destination}. Travel style: ${style}.`,
    input.travelDates ? `Travel dates: ${input.travelDates}.` : "",
    input.specificInterests?.length
      ? `Specific interests: ${input.specificInterests.join(", ")}.`
      : "",
    providerFragment,
    safetyFragment,
    "Provide overview, top attractions, activities, cultural notes, and practical tips with brief bullet lists.",
  ]
    .filter(Boolean)
    .join("\n");
}

/**
 * Input type for itinerary planning prompt builder.
 *
 * Combines base context with itinerary planning request parameters.
 */
export type ItineraryPromptInput = BasePromptContext & ItineraryPlanRequest;

/**
 * Build system prompt for itinerary planning agent.
 *
 * Constructs instructions for generating a multi-day itinerary, including
 * destination, duration, dates, interests, party size, and budget guidance.
 *
 * @param input - Itinerary planning request with optional context.
 * @returns System prompt string for the itinerary planning agent.
 */
export function buildItineraryPrompt(input: ItineraryPromptInput): string {
  const locale = input.locale ?? "en-US";
  return [
    `You are TripSage's itinerary planner. Respond in ${locale}.`,
    `Destination: ${input.destination}.`,
    input.durationDays
      ? `Trip length: ${input.durationDays} days.`
      : "Determine a sensible number of days based on provided dates or interests.",
    input.travelDates ? `Travel dates: ${input.travelDates}.` : "",
    input.interests?.length
      ? `Key interests to highlight: ${input.interests.join(", ")}.`
      : "",
    input.partySize ? `Party size: ${input.partySize}.` : "",
    input.budgetPerDay ? `Budget guidance: ${input.budgetPerDay} per day.` : "",
    "Return a JSON-friendly summary with day-by-day plans, logistics, and highlights.",
  ]
    .filter(Boolean)
    .join("\n");
}

/**
 * Input type for flight search prompt builder.
 *
 * Combines base context with flight search request parameters.
 */
export type FlightPromptInput = BasePromptContext & FlightSearchRequest;

/**
 * Build system prompt for flight search agent.
 *
 * Constructs instructions for searching flights, including route, departure
 * date, optional return date, passenger count, and cabin class.
 *
 * @param input - Flight search request with optional context.
 * @returns System prompt string for the flight search agent.
 */
export function buildFlightPrompt(input: FlightPromptInput): string {
  const cabin = input.cabinClass ?? "economy";
  return [
    "You are an airline shopping assistant. Produce concise flight options with pricing and carriers.",
    `Route: ${input.origin} → ${input.destination}.`,
    `Departure: ${input.departureDate}.`,
    input.returnDate ? `Return: ${input.returnDate}.` : "",
    `Passengers: ${input.passengers}. Cabin: ${cabin}.`,
  ]
    .filter(Boolean)
    .join(" ");
}

/**
 * Input type for accommodation search prompt builder.
 *
 * Defines parameters for searching accommodations including destination,
 * check-in/out dates, guest count, and optional preferences.
 */
export type AccommodationPromptInput = {
  destination: string;
  checkIn: string;
  checkOut: string;
  guests?: number;
  preferences?: string[];
};

/**
 * Build system prompt for accommodation search agent.
 *
 * Constructs instructions for finding accommodations, including destination,
 * dates, guest count, and optional preferences.
 *
 * @param input - Accommodation search parameters.
 * @returns System prompt string for the accommodation search agent.
 */
export function buildAccommodationPrompt(input: AccommodationPromptInput): string {
  return [
    "You are a lodging specialist.",
    `Destination: ${input.destination}.`,
    `Dates: ${input.checkIn} to ${input.checkOut}.`,
    input.guests ? `Guests: ${input.guests}.` : "",
    input.preferences?.length ? `Preferences: ${input.preferences.join(", ")}.` : "",
    "Return a small set of options with nightly rate, location context, and why they fit the traveler profile.",
  ]
    .filter(Boolean)
    .join(" ");
}

/**
 * Input type for budget planning prompt builder.
 *
 * Combines base context with budget planning request parameters.
 */
export type BudgetPromptInput = BasePromptContext & BudgetPlanRequest;

/**
 * Build system prompt for budget planning agent.
 *
 * Constructs instructions for generating a travel budget, including destination,
 * duration, travel style, optional budget cap, and allocation categories.
 *
 * @param input - Budget planning request with optional context.
 * @returns System prompt string for the budget planning agent.
 */
export function buildBudgetPrompt(input: BudgetPromptInput): string {
  return [
    "You are a travel budget analyst.",
    `Destination: ${input.destination}. Duration: ${input.durationDays} days.`,
    input.travelStyle ? `Style: ${input.travelStyle}.` : "",
    input.budgetCap
      ? `Overall budget cap: ${input.budgetCap}.`
      : "Estimate reasonable ranges if no cap provided.",
    "Allocate funds for flights, lodging, food, transportation, and experiences.",
  ]
    .filter(Boolean)
    .join(" ");
}

/**
 * Build system prompt for router classification agent.
 *
 * Constructs instructions for classifying user messages into agent workflows.
 * Returns a prompt that instructs the model to return JSON with agent workflow,
 * confidence score, and reasoning.
 *
 * @returns System prompt string for the router classification agent.
 */
export function buildRouterPrompt(): string {
  return [
    "You are TripSage's router. Inspect the latest user message and classify it into an agent workflow.",
    "Return JSON with { agent, confidence, reasoning } where agent is one of the predefined workflows.",
  ].join(" ");
}
