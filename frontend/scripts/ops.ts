#!/usr/bin/env tsx

/**
 * @fileoverview Consolidated ops CLI for infra, AI config, and test analysis.
 *
 * Subcommands (run from frontend/):
 *   pnpm ops infra check supabase   -- Supabase auth health (+ storage with service role key)
 *   pnpm ops infra check upstash    -- Upstash Redis ping + QStash token probe
 *   pnpm ops ai check config        -- AI Gateway/BYOK credential presence + gateway reachability
 *   pnpm ops check all              -- Run all infra/AI checks with summary
 *   pnpm ops test analyze failures  -- Analyze test failures from Vitest JSON report
 *   pnpm ops test analyze all       -- Full test analysis (failures + performance summary)
 *
 * BYOK providers checked: OpenAI, OpenRouter, Anthropic, xAI
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";
import { createClient } from "@supabase/supabase-js";
import { Redis } from "@upstash/redis";
import { z } from "zod";

type Command = () => Promise<void>;

const supabaseEnvSchema = z.object({
	supabaseAnonKey: z.string().min(1),
	supabaseServiceRoleKey: z.string().optional(),
	supabaseUrl: z.string().url(),
});

const upstashEnvSchema = z.object({
	redisToken: z.string().min(1),
	redisUrl: z.string().url(),
});

const qstashEnvSchema = z.object({
	qstashToken: z.string().min(1),
});

const aiEnvSchema = z.object({
	aiGatewayApiKey: z.string().min(1).optional(),
	aiGatewayUrl: z.string().url().optional(),
	anthropicApiKey: z.string().min(1).optional(),
	openaiApiKey: z.string().min(1).optional(),
	openrouterApiKey: z.string().min(1).optional(),
	xaiApiKey: z.string().min(1).optional(),
});

// ===== VITEST REPORT SCHEMAS =====

const vitestAssertionResultSchema = z.object({
	ancestorTitles: z.array(z.string()).optional(),
	duration: z.number().optional(),
	failureMessages: z.array(z.string()).optional(),
	fullName: z.string().optional(),
	status: z.enum(["passed", "failed", "skipped", "todo", "pending"]),
	title: z.string().optional(),
});

const vitestTestResultSchema = z.object({
	assertionResults: z.array(vitestAssertionResultSchema),
	endTime: z.number().optional(),
	name: z.string(),
	startTime: z.number().optional(),
	status: z.enum(["passed", "failed", "skipped", "todo", "pending"]).optional(),
});

const vitestReportSchema = z.object({
	numFailedTests: z.number(),
	numPassedTests: z.number(),
	numTotalTests: z.number(),
	startTime: z.number().optional(),
	testResults: z.array(vitestTestResultSchema),
});

type VitestReport = z.infer<typeof vitestReportSchema>;

// ===== FAILURE CATEGORIES =====

type FailureCategory =
	| "routeContext"
	| "browserEnv"
	| "schema"
	| "asyncFlaky"
	| "mockIssues"
	| "behaviorDrift"
	| "other";

interface CategorizedFailure {
	category: FailureCategory;
	error: string;
	file: string;
	test: string;
}

interface FailureAnalysis {
	byCategory: Record<FailureCategory, CategorizedFailure[]>;
	summary: {
		failed: number;
		passed: number;
		total: number;
	};
}

const DEFAULT_REPORT_PATH = ".vitest-reports/vitest-report.json";

// ===== FAILURE ANALYSIS CONSTANTS =====

/** Maximum length for error message in category summary. */
const ERROR_TRUNCATE_LENGTH = 300;

/** Maximum length for error display preview in list. */
const ERROR_DISPLAY_LENGTH = 100;

/** Threshold for showing individual failures vs "more" indicator. */
const FAILURES_SHOW_THRESHOLD = 10;

/** Number of failures to show when count exceeds threshold. */
const FAILURES_SHOW_COUNT = 5;

function formatError(error: unknown): string {
	if (error instanceof Error) return error.message;
	return String(error);
}

function printUsage(): void {
	console.log("Usage:");
	console.log("");
	console.log("  Infrastructure checks:");
	console.log(
		"    pnpm ops infra check supabase   -- Supabase auth health + storage",
	);
	console.log(
		"    pnpm ops infra check upstash    -- Redis ping + QStash probe",
	);
	console.log(
		"    pnpm ops ai check config        -- AI Gateway/BYOK credentials",
	);
	console.log("    pnpm ops check all              -- Run all infra/AI checks");
	console.log("");
	console.log("  Test analysis:");
	console.log(
		"    pnpm ops test analyze failures  -- Analyze failures from Vitest JSON",
	);
	console.log(
		"    pnpm ops test analyze all       -- Full analysis (failures + stats)",
	);
}

async function checkSupabase(): Promise<void> {
	const env = supabaseEnvSchema.parse({
		supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
		supabaseServiceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY,
		supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
	});

	const healthRes = await fetch(`${env.supabaseUrl}/auth/v1/health`, {
		headers: {
			apikey: env.supabaseAnonKey,
		},
		method: "GET",
	});

	if (!healthRes.ok) {
		throw new Error(
			`Supabase auth health failed (${healthRes.status} ${healthRes.statusText})`,
		);
	}

	if (env.supabaseServiceRoleKey) {
		const client = createClient(env.supabaseUrl, env.supabaseServiceRoleKey, {
			auth: {
				autoRefreshToken: false,
				persistSession: false,
			},
		});

		const { error } = await client.storage.listBuckets();
		if (error) {
			throw new Error(`Supabase storage list failed: ${error.message}`);
		}
	}

	console.log("Supabase check: OK");
}

async function checkUpstash(): Promise<void> {
	const redisEnv = upstashEnvSchema.parse({
		redisToken: process.env.UPSTASH_REDIS_REST_TOKEN,
		redisUrl: process.env.UPSTASH_REDIS_REST_URL,
	});

	const redis = new Redis({
		token: redisEnv.redisToken,
		url: redisEnv.redisUrl,
	});

	const ping = await redis.ping();
	if (ping !== "PONG") {
		throw new Error(`Upstash Redis ping failed (got ${ping})`);
	}

	const qstashEnv = qstashEnvSchema.safeParse({
		qstashToken: process.env.QSTASH_TOKEN,
	});

	if (qstashEnv.success) {
		const topicsRes = await fetch("https://qstash.upstash.io/v2/topics", {
			headers: {
				/* biome-ignore lint/style/useNamingConvention: HTTP header key */
				Authorization: `Bearer ${qstashEnv.data.qstashToken}`,
			},
			method: "GET",
		});

		if (!topicsRes.ok) {
			throw new Error(
				`QStash topics endpoint failed (${topicsRes.status} ${topicsRes.statusText})`,
			);
		}
	}

	console.log("Upstash check: OK");
}

async function checkAiConfig(): Promise<void> {
	const env = aiEnvSchema.parse({
		aiGatewayApiKey: process.env.AI_GATEWAY_API_KEY,
		aiGatewayUrl: process.env.AI_GATEWAY_URL,
		anthropicApiKey: process.env.ANTHROPIC_API_KEY,
		openaiApiKey: process.env.OPENAI_API_KEY,
		openrouterApiKey: process.env.OPENROUTER_API_KEY,
		xaiApiKey: process.env.XAI_API_KEY,
	});

	const hasProviderKey =
		env.openaiApiKey ||
		env.openrouterApiKey ||
		env.anthropicApiKey ||
		env.xaiApiKey;

	if (!env.aiGatewayApiKey && !hasProviderKey) {
		throw new Error("No AI credentials found (gateway or provider keys)");
	}

	// Show which credentials are configured
	const configured: string[] = [];
	if (env.aiGatewayApiKey) configured.push("AI Gateway");
	if (env.openaiApiKey) configured.push("OpenAI");
	if (env.openrouterApiKey) configured.push("OpenRouter");
	if (env.anthropicApiKey) configured.push("Anthropic");
	if (env.xaiApiKey) configured.push("xAI");
	console.log(`  Configured: ${configured.join(", ")}`);

	if (env.aiGatewayApiKey && env.aiGatewayUrl) {
		const res = await fetch(env.aiGatewayUrl, {
			headers: {
				/* biome-ignore lint/style/useNamingConvention: HTTP header key */
				Authorization: `Bearer ${env.aiGatewayApiKey}`,
			},
			method: "HEAD",
		});

		if (!res.ok) {
			throw new Error(
				`AI Gateway unreachable (${res.status} ${res.statusText}); check AI_GATEWAY_URL/API_KEY`,
			);
		}
	}

	console.log("AI config check: OK");
}

async function checkAll(): Promise<void> {
	const checks = [
		{ fn: checkSupabase, name: "Supabase" },
		{ fn: checkUpstash, name: "Upstash" },
		{ fn: checkAiConfig, name: "AI Config" },
	];

	const results: Array<{ name: string; ok: boolean; error?: string }> = [];

	for (const { name, fn } of checks) {
		console.log(`\n[${name}]`);
		try {
			await fn();
			results.push({ name, ok: true });
		} catch (error) {
			results.push({ error: formatError(error), name, ok: false });
			console.error(`  Error: ${formatError(error)}`);
		}
	}

	console.log(`\n${"=".repeat(40)}`);
	console.log("Summary:");
	for (const r of results) {
		console.log(`  ${r.ok ? "✅" : "❌"} ${r.name}`);
	}
	console.log("=".repeat(40));

	const failed = results.filter((r) => !r.ok);
	if (failed.length > 0) {
		throw new Error(`${failed.length} check(s) failed`);
	}
}

// ===== TEST ANALYSIS FUNCTIONS =====

/**
 * Categorize a test failure based on error message patterns.
 * Uses heuristics to identify common failure types in TripSage tests.
 */
function categorizeFailure(errorMessage: string): FailureCategory {
	const lower = errorMessage.toLowerCase();

	// Route context issues (Next.js headers/cookies)
	if (
		lower.includes("cookies") ||
		lower.includes("request scope") ||
		lower.includes("headers") ||
		lower.includes("next/headers") ||
		lower.includes("asynclocalstorage")
	) {
		return "routeContext";
	}

	// Browser environment issues
	if (
		lower.includes("window is not defined") ||
		lower.includes("document is not defined") ||
		lower.includes("sessionstorage") ||
		lower.includes("localstorage") ||
		lower.includes("navigator is not defined") ||
		lower.includes("matchmedia")
	) {
		return "browserEnv";
	}

	// Schema/Zod validation issues - only when Zod-specific
	if (
		lower.includes("zod") ||
		lower.includes("zoderror") ||
		lower.includes("safeparse") ||
		lower.includes("invalid_type") ||
		lower.includes("validation failed")
	) {
		return "schema";
	}
	// Generic "schema" keyword only classifies as Zod if paired with other Zod indicators
	if (
		lower.includes("schema") &&
		(lower.includes("zod") || lower.includes("validation"))
	) {
		return "schema";
	}

	// Async/timeout/flaky issues
	if (
		lower.includes("timeout") ||
		lower.includes("exceeded") ||
		lower.includes("etimedout") ||
		lower.includes("hanging") ||
		lower.includes("did not resolve") ||
		lower.includes("async callback")
	) {
		return "asyncFlaky";
	}

	// Mock-related issues
	if (
		lower.includes("vi.mock") ||
		lower.includes("vi.fn") ||
		lower.includes("mock not called") ||
		lower.includes("mockimplementation") ||
		lower.includes("not been called") ||
		lower.includes("spy") ||
		lower.includes("tohavebeencalled")
	) {
		return "mockIssues";
	}

	// Assertion/behavior drift - only classify with explicit matcher/assertion indicators
	// to avoid false positives from generic words like "expected" in error messages
	if (
		lower.includes("expect(") ||
		lower.includes("assert(") ||
		lower.includes("toequal") ||
		lower.includes("tobethrows") ||
		lower.includes("tomatch") ||
		lower.includes("tocontain") ||
		lower.includes("tohavebeencalled") ||
		(lower.includes("expected") && lower.includes("but received"))
	) {
		return "behaviorDrift";
	}

	return "other";
}

/**
 * Load and validate the Vitest JSON report file.
 */
function loadVitestReport(reportPath: string): VitestReport {
	const fullPath = resolve(reportPath);

	if (!existsSync(fullPath)) {
		throw new Error(
			`Vitest JSON report not found at ${fullPath}.\n` +
				`Run: pnpm vitest run --reporter=json --outputFile=${reportPath}`,
		);
	}

	const content = readFileSync(fullPath, "utf-8");
	let parsed: unknown;
	try {
		parsed = JSON.parse(content);
	} catch (error) {
		throw new Error(
			`Failed to parse JSON in ${fullPath}: ${error instanceof Error ? error.message : String(error)}`,
		);
	}
	return vitestReportSchema.parse(parsed);
}

/**
 * Extract and categorize all failures from a Vitest report.
 */
function extractFailures(report: VitestReport): FailureAnalysis {
	const byCategory: Record<FailureCategory, CategorizedFailure[]> = {
		asyncFlaky: [],
		behaviorDrift: [],
		browserEnv: [],
		mockIssues: [],
		other: [],
		routeContext: [],
		schema: [],
	};

	for (const testResult of report.testResults) {
		for (const assertion of testResult.assertionResults) {
			if (assertion.status === "failed" && assertion.failureMessages) {
				const errorText = assertion.failureMessages.join("\n");
				const category = categorizeFailure(errorText);
				const testName =
					assertion.fullName ||
					assertion.title ||
					assertion.ancestorTitles?.join(" > ") ||
					"Unknown test";

				byCategory[category].push({
					category,
					error: errorText.slice(0, ERROR_TRUNCATE_LENGTH),
					file: testResult.name,
					test: testName,
				});
			}
		}
	}

	return {
		byCategory,
		summary: {
			failed: report.numFailedTests,
			passed: report.numPassedTests,
			total: report.numTotalTests,
		},
	};
}

/**
 * Format failure analysis for console output.
 */
function formatFailureAnalysis(analysis: FailureAnalysis): string {
	const lines: string[] = [];
	const categoryLabels: Record<FailureCategory, string> = {
		asyncFlaky: "Async/Flaky Issues (timeouts/hanging)",
		behaviorDrift: "Behavior Drift (assertion mismatches)",
		browserEnv: "Browser Environment (window/storage)",
		mockIssues: "Mock Issues (vi.mock/vi.fn)",
		other: "Other Issues",
		routeContext: "Route Context (cookies/headers)",
		schema: "Schema/Validation (Zod)",
	};

	lines.push("=".repeat(60));
	lines.push("Test Failure Analysis");
	lines.push("=".repeat(60));
	lines.push("");

	lines.push("Summary:");
	lines.push(`  Total: ${analysis.summary.total}`);
	lines.push(`  Passed: ${analysis.summary.passed}`);
	lines.push(`  Failed: ${analysis.summary.failed}`);
	lines.push("");

	// Derive category order from categoryLabels to maintain single source of truth
	const categories = Object.keys(categoryLabels) as FailureCategory[];

	let totalCategorized = 0;
	for (const cat of categories) {
		const failures = analysis.byCategory[cat];
		totalCategorized += failures.length;

		lines.push(`${categoryLabels[cat]}: ${failures.length}`);

		if (failures.length > 0 && failures.length <= FAILURES_SHOW_THRESHOLD) {
			for (const f of failures) {
				lines.push(`  - ${f.test}`);
				lines.push(`    File: ${f.file}`);
				lines.push(
					`    ${f.error.split("\n")[0].slice(0, ERROR_DISPLAY_LENGTH)}`,
				);
			}
		} else if (failures.length > FAILURES_SHOW_THRESHOLD) {
			for (const f of failures.slice(0, FAILURES_SHOW_COUNT)) {
				lines.push(`  - ${f.test}`);
			}
			lines.push(`  ... and ${failures.length - FAILURES_SHOW_COUNT} more`);
		}
		lines.push("");
	}

	lines.push("-".repeat(60));
	lines.push(`Total failures categorized: ${totalCategorized}`);

	if (analysis.summary.failed === 0) {
		lines.push("");
		lines.push("All tests passed!");
	}

	return lines.join("\n");
}

/**
 * Extract the value following a flag from CLI args.
 * Handles both `--flag value` and `--flag=value` formats.
 * Returns null if flag not found, no value provided, or value starts with "--".
 */
function getArgValue(args: string[], flag: string): string | null {
	// Check for --flag=value format
	for (const arg of args) {
		if (arg.startsWith(`${flag}=`)) {
			return arg.substring(flag.length + 1);
		}
	}

	// Check for --flag value format
	const index = args.indexOf(flag);
	if (
		index >= 0 &&
		index + 1 < args.length &&
		!args[index + 1].startsWith("-")
	) {
		return args[index + 1];
	}
	return null;
}

// biome-ignore lint/suspicious/useAwait: Matches Command type signature
async function analyzeTestFailures(): Promise<void> {
	const args = process.argv.slice(2);

	const reportPath = getArgValue(args, "--input") ?? DEFAULT_REPORT_PATH;
	const outputPath = getArgValue(args, "--output");

	const report = loadVitestReport(reportPath);
	const analysis = extractFailures(report);

	console.log(formatFailureAnalysis(analysis));

	if (outputPath) {
		writeFileSync(resolve(outputPath), JSON.stringify(analysis, null, 2));
		console.log(`\nAnalysis written to: ${outputPath}`);
	}

	if (analysis.summary.failed > 0) {
		throw new Error(`${analysis.summary.failed} test(s) failed`);
	}
}

// biome-ignore lint/suspicious/useAwait: Matches Command type signature
async function analyzeTestAll(): Promise<void> {
	const args = process.argv.slice(2);
	const reportPath = getArgValue(args, "--input") ?? DEFAULT_REPORT_PATH;

	// Parse slow-threshold option (default: 500ms)
	const slowThresholdArg = getArgValue(args, "--slow-threshold");
	const slowThreshold = slowThresholdArg
		? Math.max(1, Number.parseInt(slowThresholdArg, 10) || 500)
		: 500;

	const report = loadVitestReport(reportPath);
	const analysis = extractFailures(report);

	// Failure analysis
	console.log(formatFailureAnalysis(analysis));

	// Performance summary (simplified version)
	console.log("");
	console.log("=".repeat(60));
	console.log("Performance Summary");
	console.log("=".repeat(60));

	const fileDurations: Array<{ duration: number; name: string }> = [];

	for (const result of report.testResults) {
		const duration =
			result.endTime && result.startTime
				? result.endTime - result.startTime
				: result.assertionResults.reduce(
						(sum, a) => sum + (a.duration ?? 0),
						0,
					);

		fileDurations.push({ duration, name: result.name });
	}

	fileDurations.sort((a, b) => b.duration - a.duration);

	const slowFiles = fileDurations.filter((f) => f.duration > slowThreshold);
	if (slowFiles.length > 0) {
		console.log("");
		console.log(`Slow files (>${slowThreshold}ms): ${slowFiles.length}`);
		for (const f of slowFiles.slice(0, 10)) {
			console.log(`  - ${f.name}: ${f.duration.toFixed(0)}ms`);
		}
		if (slowFiles.length > 10) {
			console.log(`  ... and ${slowFiles.length - 10} more`);
		}
	} else {
		console.log("");
		console.log(`No slow files detected (all <${slowThreshold}ms)`);
	}

	if (analysis.summary.failed > 0) {
		throw new Error(`${analysis.summary.failed} test(s) failed`);
	}
}

const commandMap: Record<string, Command> = {
	"ai:check:config": checkAiConfig,
	"check:all": checkAll,
	"infra:check:supabase": checkSupabase,
	"infra:check:upstash": checkUpstash,
	"test:analyze:all": analyzeTestAll,
	"test:analyze:failures": analyzeTestFailures,
};

async function main(): Promise<void> {
	const [, , ...args] = process.argv;
	const key = args.join(":");

	try {
		const command = commandMap[key];
		if (!command) {
			printUsage();
			throw new Error(`Unknown command "${key || "(none)"}"`);
		}

		await command();
	} catch (error) {
		console.error(`Error: ${formatError(error)}`);
		process.exit(1);
	}
}

main().catch((error) => {
	console.error(`Error: ${formatError(error)}`);
	process.exit(1);
});
