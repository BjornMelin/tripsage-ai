#!/usr/bin/env tsx
/**
 * @fileoverview Generate JSON Schema files from Zod schemas for API documentation.
 * Uses Zod v4.2.0 native .toJSONSchema() for OpenAPI 3.1 compatibility.
 *
 * Usage: pnpm tsx scripts/generate-api-schemas.ts
 * Output: docs/api/schemas/*.json
 */

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";

// Import schemas to generate JSON Schema for
// Add more schema imports as needed for API documentation
import {
  baseSearchParamsSchema,
  flightSearchParamsSchema,
} from "../src/domain/schemas/search";
import { tripCreateSchema, tripUpdateSchema } from "../src/domain/schemas/trips";
import { toJsonSchemaRegistry } from "../src/lib/schema/json-schema";

const OUTPUT_DIR = join(process.cwd(), "docs/api/schemas");

/**
 * Schemas to export as JSON Schema.
 * Add schemas here as they need documentation.
 */
const API_SCHEMAS: Record<string, z.ZodType> = {
  baseSearchParams: baseSearchParamsSchema,
  flightSearchParams: flightSearchParamsSchema,
  tripCreate: tripCreateSchema,
  tripUpdate: tripUpdateSchema,
};

function ensureDir(dir: string): void {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

function main(): void {
  console.log("Generating JSON Schema files...\n");

  ensureDir(OUTPUT_DIR);

  // Generate registry (all schemas in one file)
  const registry = toJsonSchemaRegistry(API_SCHEMAS);
  const registryPath = join(OUTPUT_DIR, "schemas.json");
  writeFileSync(registryPath, JSON.stringify(registry, null, 2));
  console.log(`  Created: ${registryPath}`);

  // Generate individual schema files
  for (const [name, schema] of Object.entries(API_SCHEMAS)) {
    const jsonSchema = z.toJSONSchema(schema, { target: "openapi-3.1" });
    const filePath = join(OUTPUT_DIR, `${name}.json`);
    writeFileSync(filePath, JSON.stringify(jsonSchema, null, 2));
    console.log(`  Created: ${filePath}`);
  }

  console.log(`\nGenerated ${Object.keys(API_SCHEMAS).length + 1} schema files.`);
}

main();
