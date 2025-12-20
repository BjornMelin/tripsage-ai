import "server-only";

import { createAccommodationAgent } from "@ai/agents";
import { agentSchemas } from "@schemas/agents";
import { createAgentRoute } from "@/lib/api/factory";

export const maxDuration = 60;

export const POST = createAgentRoute({
  agentFactory: createAccommodationAgent,
  agentType: "accommodationAgent",
  rateLimit: "agents:accommodations",
  schema: agentSchemas.accommodationSearchRequestSchema,
  telemetry: "agent.accommodationSearch",
});
