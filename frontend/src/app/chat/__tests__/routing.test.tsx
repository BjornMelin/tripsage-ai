/** @vitest-environment node */

import {
  accommodationSearchResultSchema,
  flightSearchResultSchema,
} from "@schemas/agents";
import type { UIMessage } from "ai";
import { DefaultChatTransport } from "ai";
import { describe, expect, it } from "vitest";

describe("Chat routing logic", () => {
  it("routes to flight agent when metadata contains flightSearch", () => {
    const userId = "user-123";
    const transport = new DefaultChatTransport({
      api: "/api/chat/stream",
      body: () => (userId ? { user_id: userId } : {}),
      credentials: "include",
      prepareSendMessagesRequest: ({ messages, id }) => {
        const last = messages[messages.length - 1];
        // biome-ignore lint/suspicious/noExplicitAny: Metadata shape is dynamic
        const md = (last && (last as any).metadata) || {};
        if (md.agent === "flightSearch" && md.request) {
          return {
            api: "/api/agents/flights",
            body: md.request,
            credentials: "include",
          };
        }
        if (md.agent === "accommodationSearch" && md.request) {
          return {
            api: "/api/agents/accommodations",
            body: md.request,
            credentials: "include",
          };
        }
        return {
          api: "/api/chat/stream",
          body: { id, messages, ...(userId ? { user_id: userId } : {}) },
          credentials: "include",
        };
      },
    });

    const messages: UIMessage[] = [
      {
        id: "1",
        metadata: {
          agent: "flightSearch",
          request: {
            cabinClass: "economy",
            departureDate: "2025-12-15",
            destination: "JFK",
            origin: "SFO",
            passengers: 1,
            returnDate: "2025-12-19",
          },
        },
        parts: [
          {
            text: "Search flights",
            type: "text",
          },
        ],
        role: "user",
      },
    ];

    // Access internal method via type assertion for testing
    // biome-ignore lint/suspicious/noExplicitAny: Testing internal transport API
    const request = (transport as any).prepareSendMessagesRequest?.({
      id: "1",
      messages,
    });
    expect(request).toBeDefined();
    expect(request.api).toBe("/api/agents/flights");
    expect(request.body.origin).toBe("SFO");
    expect(request.body.destination).toBe("JFK");
  });

  it("routes to accommodation agent when metadata contains accommodationSearch", () => {
    const userId = "user-123";
    const transport = new DefaultChatTransport({
      api: "/api/chat/stream",
      body: () => (userId ? { user_id: userId } : {}),
      credentials: "include",
      prepareSendMessagesRequest: ({ messages, id }) => {
        const last = messages[messages.length - 1];
        // biome-ignore lint/suspicious/noExplicitAny: Metadata shape is dynamic
        const md = (last && (last as any).metadata) || {};
        if (md.agent === "flightSearch" && md.request) {
          return {
            api: "/api/agents/flights",
            body: md.request,
            credentials: "include",
          };
        }
        if (md.agent === "accommodationSearch" && md.request) {
          return {
            api: "/api/agents/accommodations",
            body: md.request,
            credentials: "include",
          };
        }
        return {
          api: "/api/chat/stream",
          body: { id, messages, ...(userId ? { user_id: userId } : {}) },
          credentials: "include",
        };
      },
    });

    const messages: UIMessage[] = [
      {
        id: "1",
        metadata: {
          agent: "accommodationSearch",
          request: {
            checkIn: "2025-12-15",
            checkOut: "2025-12-19",
            destination: "New York City",
            guests: 2,
          },
        },
        parts: [
          {
            text: "Find stays",
            type: "text",
          },
        ],
        role: "user",
      },
    ];

    // Access internal method via type assertion for testing
    // biome-ignore lint/suspicious/noExplicitAny: Testing internal transport API
    const request = (transport as any).prepareSendMessagesRequest?.({
      id: "1",
      messages,
    });
    expect(request).toBeDefined();
    expect(request.api).toBe("/api/agents/accommodations");
    expect(request.body.destination).toBe("New York City");
    expect(request.body.guests).toBe(2);
  });

  it("routes to general chat when no agent metadata", () => {
    const userId = "user-123";
    const transport = new DefaultChatTransport({
      api: "/api/chat/stream",
      body: () => (userId ? { user_id: userId } : {}),
      credentials: "include",
      prepareSendMessagesRequest: ({ messages, id }) => {
        const last = messages[messages.length - 1];
        // biome-ignore lint/suspicious/noExplicitAny: Metadata shape is dynamic
        const md = (last && (last as any).metadata) || {};
        if (md.agent === "flightSearch" && md.request) {
          return {
            api: "/api/agents/flights",
            body: md.request,
            credentials: "include",
          };
        }
        if (md.agent === "accommodationSearch" && md.request) {
          return {
            api: "/api/agents/accommodations",
            body: md.request,
            credentials: "include",
          };
        }
        return {
          api: "/api/chat/stream",
          body: { id, messages, ...(userId ? { user_id: userId } : {}) },
          credentials: "include",
        };
      },
    });

    const messages: UIMessage[] = [
      {
        id: "1",
        parts: [
          {
            text: "Hello",
            type: "text",
          },
        ],
        role: "user",
      },
    ];

    // Access internal method via type assertion for testing
    // biome-ignore lint/suspicious/noExplicitAny: Testing internal transport API
    const request = (transport as any).prepareSendMessagesRequest?.({
      id: "1",
      messages,
    });
    expect(request).toBeDefined();
    expect(request.api).toBe("/api/chat/stream");
    expect(request.body.messages).toBeDefined();
  });
});

describe("JSON parsing for structured results", () => {
  it("parses flight.v2 JSON from text", () => {
    const jsonText = JSON.stringify({
      currency: "USD",
      fromCache: false,
      itineraries: [
        {
          id: "flight-1",
          price: 450,
          segments: [
            {
              arrival: "2025-12-15T18:30:00Z",
              carrier: "AA",
              departure: "2025-12-15T10:00:00Z",
              destination: "JFK",
              origin: "SFO",
            },
          ],
        },
      ],
      offers: [],
      provider: "duffel",
      schemaVersion: "flight.v2",
    });

    const parsed = JSON.parse(jsonText);
    const result = flightSearchResultSchema.safeParse(parsed);
    if (!result.success) {
      throw new Error(result.error.toString());
    }
    expect(result.data.schemaVersion).toBe("flight.v2");
    expect(result.data.itineraries).toHaveLength(1);
  });

  it("parses stay.v1 JSON from text", () => {
    const jsonText = JSON.stringify({
      schemaVersion: "stay.v1",
      sources: [],
      stays: [
        {
          address: "123 Main St",
          currency: "USD",
          name: "Grand Hotel",
          nightlyRate: 150,
          rating: 4.5,
        },
      ],
    });

    const parsed = JSON.parse(jsonText);
    const result = accommodationSearchResultSchema.safeParse(parsed);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.schemaVersion).toBe("stay.v1");
      expect(result.data.stays).toHaveLength(1);
    }
  });

  it("extracts JSON from markdown code blocks", () => {
    const markdownText = `Here are the flight results:

\`\`\`json
{
  "schemaVersion": "flight.v2",
  "currency": "USD",
  "provider": "duffel",
  "fromCache": false,
  "offers": [],
  "itineraries": []
}
\`\`\``;

    const jsonMatch = markdownText.match(
      /```(?:json)?\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*\})/
    );
    const jsonStr = jsonMatch?.[1] ?? jsonMatch?.[2] ?? markdownText;
    const parsed = JSON.parse(jsonStr);
    expect(parsed.schemaVersion).toBe("flight.v2");
  });

  it("handles invalid JSON gracefully", () => {
    const invalidText = "This is not JSON";
    let parsedJson: unknown = null;
    try {
      parsedJson = JSON.parse(invalidText);
    } catch {
      // Expected to fail
    }
    expect(parsedJson).toBeNull();
  });
});
