import "server-only";

import { createFlightAgent } from "@ai/agents";
import { flightSearchRequestSchema } from "@schemas/flights";
import { createAgentRoute } from "@/lib/api/factory";

export const maxDuration = 60;

export const POST = createAgentRoute({
  agentFactory: createFlightAgent,
  agentType: "flightAgent",
  rateLimit: "agents:flight",
  schema: flightSearchRequestSchema,
  telemetry: "agent.flightSearch",
});
