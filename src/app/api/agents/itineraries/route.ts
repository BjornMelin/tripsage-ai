import "server-only";

import { createItineraryAgent } from "@ai/agents";
import { agentSchemas } from "@schemas/agents";
import { createAgentRoute } from "@/lib/api/factory";

export const maxDuration = 60;

export const POST = createAgentRoute({
  agentFactory: createItineraryAgent,
  agentType: "itineraryAgent",
  rateLimit: "agents:itineraries",
  schema: agentSchemas.itineraryPlanRequestSchema,
  telemetry: "agent.itineraryPlanning",
});
