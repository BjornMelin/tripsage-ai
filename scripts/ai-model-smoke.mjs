#!/usr/bin/env node
/**
 * Tiny non-user-data AI Gateway smoke test for TripSage model-profile choices.
 */

import { performance } from "node:perf_hooks";
import { createGateway, generateText, isStepCount, Output, tool } from "ai";
import { z } from "zod";

const DEFAULT_MODELS = ["openai/gpt-5.4-mini", "openai/gpt-5.4-nano", "openai/gpt-5.5"];
const DEFAULT_GATEWAY_HOST = "ai-gateway.vercel.sh";

const intentSchema = z.strictObject({
  city: z.literal("Denver"),
  intent: z.literal("flight_search"),
  travelers: z.number().int().min(1).max(4),
});

function parseArgs(argv) {
  const options = {
    json: false,
    models: DEFAULT_MODELS,
    required: false,
  };

  for (const arg of argv) {
    if (arg === "--json") {
      options.json = true;
    } else if (arg === "--required") {
      options.required = true;
    } else if (arg.startsWith("--models=")) {
      const models = arg
        .slice("--models=".length)
        .split(",")
        .map((model) => model.trim())
        .filter(Boolean);
      if (models.length === 0) {
        throw new Error("--models requires at least one model id");
      }
      options.models = models;
    }
  }

  return options;
}

function summarizeUsage(...usages) {
  const totals = { inputTokens: 0, outputTokens: 0, totalTokens: 0 };
  for (const usage of usages) {
    if (!usage) continue;
    totals.inputTokens += Number(usage.inputTokens ?? usage.promptTokens ?? 0);
    totals.outputTokens += Number(usage.outputTokens ?? usage.completionTokens ?? 0);
    totals.totalTokens += Number(usage.totalTokens ?? 0);
  }
  return totals;
}

function readToolInput(call) {
  return call?.input ?? call?.args ?? call?.arguments;
}

function allowedGatewayHosts() {
  const hosts = new Set([DEFAULT_GATEWAY_HOST]);
  for (const host of (process.env.AI_GATEWAY_ALLOWED_HOSTS ?? "").split(",")) {
    const normalized = host.trim().toLowerCase();
    if (normalized) hosts.add(normalized);
  }
  return hosts;
}

function isPrivateGatewayHost(hostname) {
  const host = hostname.toLowerCase();
  if (host === "localhost" || host.endsWith(".local")) return true;

  const ipv4Match = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/u.exec(host);
  if (ipv4Match) {
    const octets = ipv4Match.slice(1).map((octet) => Number(octet));
    if (octets.some((octet) => !Number.isInteger(octet) || octet < 0 || octet > 255)) {
      return true;
    }
    const [a, b] = octets;
    return (
      a === 0 ||
      a === 10 ||
      a === 127 ||
      (a === 169 && b === 254) ||
      (a === 172 && b >= 16 && b <= 31) ||
      (a === 192 && b === 168)
    );
  }

  const ipv6 = host.replace(/^\[|\]$/gu, "").toLowerCase();
  if (ipv6 === "::1" || /^(0{1,4}:){7}0*1$/iu.test(ipv6)) return true;
  if (ipv6.startsWith("fe80")) return true;
  const firstHextetMatch = /^([0-9a-f]{1,4}):/iu.exec(ipv6);
  if (!firstHextetMatch) return false;
  const firstHextet = Number.parseInt(firstHextetMatch[1], 16);
  return firstHextet >= 0xfc00 && firstHextet <= 0xfdff;
}

function validateGatewayBaseUrl(rawBaseUrl) {
  if (!rawBaseUrl?.trim()) return undefined;

  let parsed;
  try {
    parsed = new URL(rawBaseUrl);
  } catch {
    throw new Error("invalid_gateway_url");
  }

  if (parsed.protocol !== "https:") throw new Error("gateway_url_non_https");
  if (parsed.username || parsed.password) throw new Error("gateway_url_credentials");
  if (isPrivateGatewayHost(parsed.hostname))
    throw new Error("gateway_url_private_host");
  if (!allowedGatewayHosts().has(parsed.hostname.toLowerCase())) {
    throw new Error("gateway_url_host_not_allowed");
  }

  return parsed.toString();
}

async function runModelSmoke(gateway, modelId) {
  const started = performance.now();
  const model = gateway(modelId);
  const errors = [];
  let schemaUsage;
  let toolUsage;
  let schemaOk = false;
  let toolOk = false;

  try {
    const schemaResult = await generateText({
      maxOutputTokens: 96,
      model,
      output: Output.object({ schema: intentSchema }),
      prompt:
        'Return the travel intent as JSON for: "Find flights to Denver for 2 travelers."',
      providerOptions: {
        gateway: { tags: ["tripsage:model-smoke", "schema"] },
      },
      temperature: 0,
    });
    schemaUsage = schemaResult.usage;
    schemaOk = intentSchema.safeParse(schemaResult.output).success;
    if (!schemaOk) errors.push("schema_output_invalid");
  } catch (error) {
    errors.push(
      `schema_error:${error instanceof Error ? error.message : String(error)}`
    );
  }

  try {
    const toolResult = await generateText({
      maxOutputTokens: 128,
      model,
      prompt:
        "Use the selectTripIntent tool with intent flight_search, city Denver, and 2 travelers.",
      providerOptions: {
        gateway: { tags: ["tripsage:model-smoke", "tool"] },
      },
      stopWhen: isStepCount(2),
      temperature: 0,
      toolChoice: { toolName: "selectTripIntent", type: "tool" },
      tools: {
        selectTripIntent: tool({
          description: "Select a tiny validated travel intent payload.",
          execute: async (input) => ({ accepted: true, input }),
          inputSchema: intentSchema,
        }),
      },
    });
    toolUsage = toolResult.usage;
    const toolCalls = [
      ...(toolResult.toolCalls ?? []),
      ...(toolResult.steps ?? []).flatMap((step) => step.toolCalls ?? []),
    ];
    toolOk = toolCalls.some(
      (call) => intentSchema.safeParse(readToolInput(call)).success
    );
    if (!toolOk) errors.push("tool_args_invalid_or_missing");
  } catch (error) {
    errors.push(`tool_error:${error instanceof Error ? error.message : String(error)}`);
  }

  const elapsedMs = Math.round(performance.now() - started);
  const usage = summarizeUsage(schemaUsage, toolUsage);
  return {
    elapsedMs,
    errors,
    modelId,
    ok: schemaOk && toolOk,
    schemaOk,
    toolOk,
    usage,
  };
}

let options;
try {
  options = parseArgs(process.argv.slice(2));
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
const apiKey = process.env.AI_GATEWAY_API_KEY;

if (!apiKey) {
  const skipped = {
    ok: !options.required,
    reason: "AI_GATEWAY_API_KEY is not set",
    skipped: true,
  };
  console.log(JSON.stringify(skipped, null, 2));
  process.exit(options.required ? 1 : 0);
}

let gatewayBaseUrl;
try {
  gatewayBaseUrl = validateGatewayBaseUrl(process.env.AI_GATEWAY_URL);
} catch (error) {
  console.log(
    JSON.stringify(
      {
        ok: false,
        reason: error instanceof Error ? error.message : String(error),
      },
      null,
      2
    )
  );
  process.exit(1);
}

const gatewayOptions = { apiKey };
if (gatewayBaseUrl) gatewayOptions.baseURL = gatewayBaseUrl;
const gateway = createGateway(gatewayOptions);

const results = [];
for (const modelId of options.models) {
  results.push(await runModelSmoke(gateway, modelId));
}

const failed = results.filter((result) => !result.ok);
const summary = {
  failed: failed.length,
  models: results,
  ok: failed.length === 0,
};

if (options.json) {
  console.log(JSON.stringify(summary, null, 2));
} else {
  for (const result of results) {
    const status = result.ok ? "pass" : "fail";
    const usage = result.usage.totalTokens
      ? `${result.usage.totalTokens} tokens`
      : "usage unavailable";
    console.log(
      `${status} ${result.modelId} ${result.elapsedMs}ms ${usage} schema=${result.schemaOk} tool=${result.toolOk}`
    );
    for (const error of result.errors) console.log(`  ${error}`);
  }
}

process.exit(summary.ok ? 0 : 1);
