import "server-only";

import { createBudgetAgent } from "@ai/agents";
import { agentSchemas } from "@schemas/agents";
import { createAgentRoute } from "@/lib/api/factory";

export const maxDuration = 60;

export const POST = createAgentRoute({
  agentFactory: createBudgetAgent,
  agentType: "budgetAgent",
  rateLimit: "agents:budget",
  schema: agentSchemas.budgetPlanRequestSchema,
  telemetry: "agent.budgetPlanning",
});
