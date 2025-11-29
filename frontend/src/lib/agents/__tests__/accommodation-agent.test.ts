/** @vitest-environment node */

import { toolRegistry } from "@ai/tools";
import type { AccommodationSearchRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { runAccommodationAgent } from "@/lib/agents/accommodation-agent";
import { createMockModel } from "@/test/ai-sdk/mock-model";
import { deepCloneValue } from "@/test-utils/deep-clone";

const streamTextImpl = (options: unknown) =>
  ({
    ...(options as Record<string, unknown>),
    textStream: (function* () {
      yield { textDelta: "ok", type: "text-delta" } as const;
    })(),
    toUIMessageStreamResponse: vi.fn(),
  }) as unknown;

const streamTextMock = vi.hoisted(() =>
  vi.fn<(options: unknown) => unknown>((options: unknown) => streamTextImpl(options))
);
const createAiToolMock = vi.hoisted(() =>
  vi.fn().mockImplementation(({ execute, name }) => ({
    description: name,
    execute,
    inputSchema: {},
    name,
  }))
);

vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai");
  return {
    ...actual,
    streamText: streamTextMock,
  };
});

vi.mock("@ai/lib/tool-factory", () => ({
  createAiTool: createAiToolMock,
}));

const baseConfig: AgentConfig = {
  agentType: "accommodationAgent",
  createdAt: "2025-01-01T00:00:00.000Z",
  id: "v1_accom01",
  model: "gpt-4o",
  parameters: {
    description: null,
    maxTokens: 2048,
    model: "gpt-4o",
    temperature: 0.25,
    timeoutSeconds: 30,
    topKTools: 4,
    topP: 0.85,
  },
  scope: "agentSpecific",
  updatedAt: "2025-01-01T00:00:00.000Z",
};

const baseInput: AccommodationSearchRequest = {
  checkIn: "2025-06-01",
  checkOut: "2025-06-05",
  destination: "Lisbon",
  guests: 2,
};

const cloneToolRegistry = (registry: typeof toolRegistry) =>
  deepCloneValue(registry) as typeof toolRegistry;

const originalRegistry = cloneToolRegistry(toolRegistry);

describe("runAccommodationAgent", () => {
  beforeEach(() => {
    Object.keys(toolRegistry).forEach((key) => {
      delete (toolRegistry as Record<string, unknown>)[key];
    });
    Object.assign(toolRegistry, cloneToolRegistry(originalRegistry));
    streamTextMock.mockReset();
    streamTextMock.mockImplementation(streamTextImpl);
    createAiToolMock.mockClear();
  });

  it("throws when searchAccommodations tool is missing", () => {
    (toolRegistry as Record<string, unknown>).searchAccommodations = undefined as never;

    expect(() =>
      runAccommodationAgent(
        { identifier: "user-3", model: createMockModel(), modelId: "mock" },
        baseConfig,
        baseInput
      )
    ).toThrow(/Tool searchAccommodations not registered/);
  });

  it("wraps accommodation tools and delegates execution", async () => {
    const searchExecute = vi.fn().mockResolvedValue({ results: [] });
    const detailsExecute = vi.fn().mockResolvedValue({ listing: {} });
    const availabilityExecute = vi.fn().mockResolvedValue({ bookingToken: "tok" });
    const bookingExecute = vi.fn().mockResolvedValue({ status: "ok" });

    Object.assign(toolRegistry, {
      searchAccommodations: { description: "search", execute: searchExecute },
      getAccommodationDetails: { description: "details", execute: detailsExecute },
      checkAvailability: { description: "availability", execute: availabilityExecute },
      bookAccommodation: { description: "book", execute: bookingExecute },
    });

    runAccommodationAgent(
      { identifier: "user-3", model: createMockModel(), modelId: "mock" },
      baseConfig,
      baseInput
    );

    const call = streamTextMock.mock.calls[0]?.[0] as {
      tools: Record<
        string,
        { execute: (params: unknown, callOpts?: unknown) => unknown }
      >;
    };
    expect(call).toBeDefined();
    const tools = call.tools;

    const searchInput = { destination: "Lisbon" };
    const detailsInput = { listingId: "id1" };
    const availabilityInput = { priceCheckToken: "pct", propertyId: "p1", rateId: "r1", roomId: "room1", checkIn: "2025-06-01", checkOut: "2025-06-05", guests: 2 };
    const bookingInput = { bookingToken: "b1" };

    await tools.searchAccommodations.execute(searchInput, { toolCallId: "tc1" });
    await tools.getAccommodationDetails.execute(detailsInput, { toolCallId: "tc2" });
    await tools.checkAvailability.execute(availabilityInput, { toolCallId: "tc3" });
    await tools.bookAccommodation.execute(bookingInput, { toolCallId: "tc4" });

    expect(searchExecute).toHaveBeenCalledWith(
      searchInput,
      expect.objectContaining({ toolCallId: "tc1" })
    );
    expect(detailsExecute).toHaveBeenCalledWith(
      detailsInput,
      expect.objectContaining({ toolCallId: "tc2" })
    );
    expect(availabilityExecute).toHaveBeenCalledWith(
      availabilityInput,
      expect.objectContaining({ toolCallId: "tc3" })
    );
    expect(bookingExecute).toHaveBeenCalledWith(
      bookingInput,
      expect.objectContaining({ toolCallId: "tc4" })
    );
    expect(createAiToolMock).toHaveBeenCalledTimes(4);
    expect(streamTextMock).toHaveBeenCalledTimes(1);
  });
});
