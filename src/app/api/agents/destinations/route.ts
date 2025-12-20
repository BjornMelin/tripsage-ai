import "server-only";

import { createDestinationAgent } from "@ai/agents";
import { agentSchemas } from "@schemas/agents";
import { createAgentRoute } from "@/lib/api/factory";

export const maxDuration = 60;

export const POST = createAgentRoute({
  agentFactory: createDestinationAgent,
  agentType: "destinationResearchAgent",
  rateLimit: "agents:destinations",
  schema: agentSchemas.destinationResearchRequestSchema,
  telemetry: "agent.destinationResearch",
});
