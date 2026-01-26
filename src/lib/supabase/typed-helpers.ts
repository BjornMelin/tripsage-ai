/**
 * @fileoverview Typed helper utilities for Supabase CRUD operations with Zod validation. These helpers centralize runtime validation using Zod schemas while preserving compile-time shapes using the generated `Database` types.
 */

import { getSupabaseSchema, type SupabaseSchemaName } from "@schemas/supabase";
import type { SupabaseClient } from "@supabase/supabase-js";
import { recordErrorOnSpan, withTelemetrySpan } from "@/lib/telemetry/span";
import type { Database } from "./database.types";

export type TypedClient = SupabaseClient<Database>;

type SchemaName = Extract<SupabaseSchemaName, keyof Database>;
type TableName<S extends SchemaName> = Extract<keyof Database[S]["Tables"], string>;
type TableRow<
  S extends SchemaName,
  T extends TableName<S>,
> = Database[S]["Tables"][T] extends Record<"Row", infer R> ? R : never;
type TableInsert<
  S extends SchemaName,
  T extends TableName<S>,
> = Database[S]["Tables"][T] extends Record<"Insert", infer I> ? I : never;
type TableUpdate<
  S extends SchemaName,
  T extends TableName<S>,
> = Database[S]["Tables"][T] extends Record<"Update", infer U> ? U : never;
/**
 * Query builder type alias using `any` intentionally.
 * Supabase's query builder is any-based internally; precise generics cause
 * excessive complexity and type instability. Biome rule suppressed below.
 */
// biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing is any-based
export type TableFilterBuilder = any;

type SupabaseTableSchema = {
  insert?: { parse: (value: unknown) => unknown };
  row?: { parse: (value: unknown) => unknown };
  update?: { parse: (value: unknown) => unknown };
};

const SUPPORTED_TABLES = {
  auth: ["sessions"],
  memories: ["sessions", "turns"],
  public: [
    "accommodations",
    "agent_config",
    "agent_config_versions",
    "api_metrics",
    "auth_backup_codes",
    "chat_messages",
    "chat_sessions",
    "chat_tool_calls",
    "file_attachments",
    "flights",
    "itinerary_items",
    "mfa_enrollments",
    "rag_documents",
    "saved_places",
    "trip_collaborators",
    "trips",
    "user_settings",
  ],
} as const;

type SupportedSchema = keyof typeof SUPPORTED_TABLES;

const isSupportedTable = (schema: SchemaName, table: string): boolean => {
  const tables = SUPPORTED_TABLES[schema as SupportedSchema];
  return Array.isArray(tables) && tables.includes(table as never);
};

const resolveSchema = (schema?: SchemaName): SchemaName => schema ?? "public";

const getSchemaClient = (
  client: TypedClient,
  schema: SchemaName
): TableFilterBuilder => {
  if (schema === "public") return client;
  const schemaFn = (client as { schema?: (name: SchemaName) => TableFilterBuilder })
    .schema;
  return typeof schemaFn === "function" ? schemaFn(schema) : client;
};

const getFromClient = (
  client: TypedClient,
  schema: SchemaName
): TableFilterBuilder | null => {
  const schemaClient = getSchemaClient(client, schema) as TableFilterBuilder;
  return schemaClient && typeof (schemaClient as { from?: unknown }).from === "function"
    ? schemaClient
    : null;
};

const getValidationSchema = (
  schema: SchemaName,
  table: string
): SupabaseTableSchema | undefined => {
  if (!isSupportedTable(schema, table)) return undefined;
  return getSupabaseSchema(table as never, { schema }) as
    | SupabaseTableSchema
    | undefined;
};

/**
 * Inserts a row into the specified table and returns the single selected row.
 * Uses `.select().single()` to fetch the inserted record in one roundtrip.
 * Validates input and output using Zod schemas when available.
 *
 * Note: When inserting multiple rows, `.single()` will error. For batches,
 * add a dedicated `insertMany` helper without `.single()` if needed.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param values Insert payload (validated via Zod schema)
 * @returns Selected row (validated) and error (if any)
 */
export function insertSingle<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  values: TableInsert<S, T> | TableInsert<S, T>[],
  options?: { schema?: S; validate?: boolean }
): Promise<{ data: TableRow<S, T> | null; error: unknown }> {
  return withTelemetrySpan(
    "supabase.insert",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "insert",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      const shouldValidate = options?.validate ?? true;
      // Validate input if schema exists
      const schema = getValidationSchema(schemaName, table as string);
      if (schema?.insert && shouldValidate && !Array.isArray(values)) {
        try {
          schema.insert.parse(values);
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { data: null, error: validationError };
        }
      }

      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      if (!anyClient || typeof anyClient.from !== "function") {
        return { data: null, error: new Error("from_unavailable") };
      }
      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const insertQb = (anyClient as any)
        .from(table as string)
        .insert(values as unknown);
      // Some tests stub a very lightweight query builder without select/single methods.
      // Gracefully handle those by treating the insert as fire-and-forget.
      if (insertQb && typeof insertQb.select === "function") {
        const { data, error } = await insertQb.select().single();
        if (error) return { data: null, error };
        // Validate output if schema exists
        const rowSchema = schema?.row;
        if (rowSchema && data && shouldValidate) {
          try {
            const validated = rowSchema.parse(data);
            return { data: validated as TableRow<S, T>, error: null };
          } catch (validationError) {
            if (validationError instanceof Error) {
              recordErrorOnSpan(span, validationError);
            }
            return { data: null, error: validationError };
          }
        }
        return { data: (data ?? null) as TableRow<S, T> | null, error: null };
      }

      if (insertQb && typeof insertQb.then === "function") {
        const { error } = await insertQb;
        return { data: null, error: error ?? null };
      }

      return { data: null, error: null };
    }
  );
}

/**
 * Updates rows in the specified table and returns a single selected row.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to selecting the row. Callers must supply filters
 * that narrow the result to one row; this helper does not enforce uniqueness
 * and will update all matching rows before selecting `.single()`.
 * Validates input and output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param updates Partial update payload (validated via Zod schema)
 * @param where Closure to apply filters to the builder
 * @returns Selected row (validated) and error (if any)
 */
export function updateSingle<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  updates: Partial<TableUpdate<S, T>>,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: { schema?: S; validate?: boolean }
): Promise<{ data: TableRow<S, T> | null; error: unknown }> {
  return withTelemetrySpan(
    "supabase.update",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "update",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      const shouldValidate = options?.validate ?? true;
      // Validate input if schema exists
      const schema = getValidationSchema(schemaName, table as string);
      if (schema?.update && shouldValidate) {
        try {
          schema.update.parse(updates);
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { data: null, error: validationError };
        }
      }

      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      const filtered = where(
        // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
        (anyClient as any)
          .from(table as string)
          .update(updates as unknown) as TableFilterBuilder
      );
      const resolved = await Promise.resolve(filtered);
      if (resolved && typeof (resolved as { select?: unknown }).select === "function") {
        const { data, error } = await (resolved as TableFilterBuilder)
          .select()
          .single();
        if (error) return { data: null, error };
        if (!data) return { data: null, error: null };
        // Validate output if schema exists
        const rowSchema = schema?.row;
        if (rowSchema && shouldValidate) {
          try {
            const validated = rowSchema.parse(data);
            return { data: validated as TableRow<S, T>, error: null };
          } catch (validationError) {
            if (validationError instanceof Error) {
              recordErrorOnSpan(span, validationError);
            }
            return { data: null, error: validationError };
          }
        }
        return { data: (data ?? null) as TableRow<S, T> | null, error: null };
      }
      if (resolved && typeof resolved === "object" && "error" in resolved) {
        return {
          data: null,
          error: (resolved as { error?: unknown }).error ?? null,
        };
      }
      return { data: null, error: null };
    }
  );
}

/**
 * Updates rows in the specified table and returns the number of rows affected.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to executing the update. This helper does not
 * enforce uniqueness and is suitable for bulk updates.
 * Validates input using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param updates Partial update payload (validated via Zod schema)
 * @param where Closure to apply filters to the builder
 * @returns Count of updated rows and error (if any)
 */
export function updateMany<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  updates: Partial<TableUpdate<S, T>>,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: { schema?: S; validate?: boolean }
): Promise<{ count: number; error: unknown | null }> {
  return withTelemetrySpan(
    "supabase.update",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "update",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      const shouldValidate = options?.validate ?? true;
      const schema = getValidationSchema(schemaName, table as string);
      if (schema?.update && shouldValidate) {
        try {
          schema.update.parse(updates);
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { count: 0, error: validationError };
        }
      }

      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { count: 0, error: new Error("from_unavailable") };
      }
      const qb = where(
        // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
        (anyClient as any)
          .from(table as string)
          .update(updates as unknown, { count: "exact" }) as TableFilterBuilder
      );
      const { count, error } = await qb;
      span.setAttribute("db.supabase.row_count", count ?? 0);
      return { count: count ?? 0, error: error ?? null };
    }
  );
}

/**
 * Fetches a single row from the specified table.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to selecting the row. The caller is responsible for
 * scoping the filter to a unique row; this helper does not add additional
 * constraints and will surface Supabase errors if multiple rows match.
 * Validates output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param where Closure to apply filters to the builder
 * @returns Selected row (validated) and error (if any)
 */
export function getSingle<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: { schema?: S; select?: string; validate?: boolean }
): Promise<{ data: TableRow<S, T> | null; error: unknown }> {
  return withTelemetrySpan(
    "supabase.select",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "select",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      const schema = getValidationSchema(schemaName, table as string);
      const selectColumns = options?.select ?? "*";
      const shouldValidate = options?.validate ?? selectColumns === "*";

      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      const qb = where(
        // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
        (anyClient as any)
          .from(table as string)
          .select(selectColumns) as TableFilterBuilder
      );
      const limited = typeof qb.limit === "function" ? qb.limit(1) : null;
      const result =
        typeof qb.single === "function"
          ? await qb.single()
          : limited && typeof limited.single === "function"
            ? await limited.single()
            : { data: null, error: new Error("single_unavailable") };
      const { data, error } = result;
      if (error) return { data: null, error };
      if (!data) return { data: null, error: null };
      // Validate output if schema exists
      const rowSchema = schema?.row;
      if (rowSchema && shouldValidate) {
        try {
          const validated = rowSchema.parse(data);
          return { data: validated as TableRow<S, T>, error: null };
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { data: null, error: validationError };
        }
      }
      return { data: (data ?? null) as TableRow<S, T> | null, error: null };
    }
  );
}

/**
 * Deletes rows from the specified table matching the given criteria.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to deletion. Naming follows getSingle/updateSingle;
 * callers must provide filters that target the intended row(s). This helper
 * does not enforce single-row deletion and will delete all rows matching the
 * supplied filter.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param where Closure to apply filters to the builder
 * @returns Error (if any)
 */
export function deleteSingle<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: { schema?: S }
): Promise<{ count: number; error: unknown | null }> {
  return withTelemetrySpan(
    "supabase.delete",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "delete",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { count: 0, error: new Error("from_unavailable") };
      }
      const qb = where(
        // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
        (anyClient as any)
          .from(table as string)
          .delete({ count: "exact" }) as TableFilterBuilder
      );
      const { count, error } = await qb;
      span.setAttribute("db.supabase.row_count", count ?? 0);
      return { count: count ?? 0, error: error ?? null };
    }
  );
}

/**
 * Fetches a single row from the specified table, returning null if not found.
 * Uses `.maybeSingle()` instead of `.single()` to avoid PGRST116 errors.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to selecting the row.
 * Validates output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param where Closure to apply filters to the builder
 * @returns Selected row (validated) or null, and error (if any)
 */
export function getMaybeSingle<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: { schema?: S; select?: string; validate?: boolean }
): Promise<{ data: TableRow<S, T> | null; error: unknown }> {
  return withTelemetrySpan(
    "supabase.select",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "select",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      const schema = getValidationSchema(schemaName, table as string);
      const selectColumns = options?.select ?? "*";
      const shouldValidate = options?.validate ?? selectColumns === "*";

      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      const qb = where(
        // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
        (anyClient as any)
          .from(table as string)
          .select(selectColumns) as TableFilterBuilder
      );
      const limited = typeof qb.limit === "function" ? qb.limit(1) : null;
      const result =
        typeof qb.maybeSingle === "function"
          ? await qb.maybeSingle()
          : limited && typeof limited.maybeSingle === "function"
            ? await limited.maybeSingle()
            : limited && typeof limited.single === "function"
              ? await limited.single()
              : typeof qb.single === "function"
                ? await qb.single()
                : { data: null, error: new Error("maybeSingle_unavailable") };
      const { data, error } = result;
      if (error) return { data: null, error };
      if (!data) return { data: null, error: null };
      // Validate output if schema exists
      const rowSchema = schema?.row;
      if (rowSchema && shouldValidate) {
        try {
          const validated = rowSchema.parse(data);
          return { data: validated as TableRow<S, T>, error: null };
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { data: null, error: validationError };
        }
      }
      return { data: data as TableRow<S, T>, error: null };
    }
  );
}

/**
 * Upserts a row into the specified table and returns the single selected row.
 * Uses `.upsert()` with onConflict to perform insert-or-update operations.
 * Validates input and output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param values Upsert payload (validated via Zod schema)
 * @param onConflict Column name(s) to determine conflict (e.g., "user_id")
 * @returns Selected row (validated) and error (if any)
 */
export function upsertSingle<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  values: TableInsert<S, T>,
  onConflict: string,
  options?: { schema?: S; validate?: boolean }
): Promise<{ data: TableRow<S, T> | null; error: unknown }> {
  return withTelemetrySpan(
    "supabase.upsert",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "upsert",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      const shouldValidate = options?.validate ?? true;
      const schema = getValidationSchema(schemaName, table as string);
      if (schema?.insert && shouldValidate) {
        try {
          schema.insert.parse(values);
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { data: null, error: validationError };
        }
      }

      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const upsertQb = (anyClient as any)
        .from(table as string)
        .upsert(values as unknown, {
          ignoreDuplicates: false,
          onConflict,
        });

      // Chain select/single to return the upserted row
      if (upsertQb && typeof upsertQb.select === "function") {
        const { data, error } = await upsertQb.select().single();
        if (error) return { data: null, error };
        // Validate output if schema exists
        const rowSchema = schema?.row;
        if (rowSchema && data && shouldValidate) {
          try {
            const validated = rowSchema.parse(data);
            return { data: validated as TableRow<S, T>, error: null };
          } catch (validationError) {
            if (validationError instanceof Error) {
              recordErrorOnSpan(span, validationError);
            }
            return { data: null, error: validationError };
          }
        }
        return { data: (data ?? null) as TableRow<S, T> | null, error: null };
      }
      return { data: null, error: null };
    }
  );
}

/**
 * Upserts multiple rows into the specified table and returns all selected rows.
 * Uses `.upsert()` with onConflict to perform insert-or-update operations in batch.
 * Validates input and output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param values Array of upsert payloads (validated via Zod schema)
 * @param onConflict Column name(s) to determine conflict (e.g., "user_id")
 * @returns Array of upserted rows (validated) and error (if any)
 */
export function upsertMany<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  values: TableInsert<S, T>[],
  onConflict: string,
  options?: { schema?: S; validate?: boolean }
): Promise<{ data: TableRow<S, T>[]; error: unknown }> {
  return withTelemetrySpan(
    "supabase.upsert",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.batch_size": values.length,
        "db.supabase.operation": "upsert",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      const shouldValidate = options?.validate ?? true;
      if (values.length === 0) {
        return { data: [], error: null };
      }

      const schema = getValidationSchema(schemaName, table as string);
      if (schema?.insert && shouldValidate) {
        try {
          for (const value of values) {
            schema.insert.parse(value);
          }
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { data: [], error: validationError };
        }
      }

      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { data: [], error: new Error("from_unavailable") };
      }
      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const upsertQb = (anyClient as any)
        .from(table as string)
        .upsert(values as unknown, {
          ignoreDuplicates: false,
          onConflict,
        });

      if (upsertQb && typeof upsertQb.select === "function") {
        const { data, error } = await upsertQb.select();
        if (error) return { data: [], error };

        const rows = (data ?? []) as TableRow<S, T>[];
        span.setAttribute("db.supabase.row_count", rows.length);

        const rowSchema = schema?.row;
        if (rowSchema && shouldValidate && rows.length > 0) {
          try {
            const validated = rows.map((row) => rowSchema.parse(row)) as TableRow<
              S,
              T
            >[];
            return { data: validated, error: null };
          } catch (validationError) {
            if (validationError instanceof Error) {
              recordErrorOnSpan(span, validationError);
            }
            return { data: [], error: validationError };
          }
        }
        return { data: rows, error: null };
      }
      return { data: [], error: null };
    }
  );
}

/**
 * Options for the `getMany` helper.
 */
export interface GetManyOptions {
  /** Maximum number of rows to return. */
  limit?: number;
  /** Number of rows to skip (for pagination). */
  offset?: number;
  /** Column to order by. */
  orderBy?: string;
  /** If true, order ascending; otherwise descending. Default: true. */
  ascending?: boolean;
  /** Whether to include a count of total matching rows. */
  count?: "exact" | "planned" | "estimated";
  /** Optional schema to query (defaults to public). */
  schema?: SchemaName;
  /** Optional column list for select (defaults to "*"). */
  select?: string;
  /** Whether to validate results against row schema (defaults true for "*" selects). */
  validate?: boolean;
}

/**
 * Fetches multiple rows from the specified table with optional pagination and ordering.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to selecting rows.
 * Validates output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param where Closure to apply filters to the builder
 * @param options Optional pagination, ordering, and count settings
 * @returns Array of rows (validated), count if requested, and error (if any)
 */
export function getMany<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: GetManyOptions & { schema?: S }
): Promise<{ data: TableRow<S, T>[]; count: number | null; error: unknown }> {
  return withTelemetrySpan(
    "supabase.select",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "select",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      const schema = getValidationSchema(schemaName, table as string);
      const selectColumns = options?.select ?? "*";
      const shouldValidate = options?.validate ?? selectColumns === "*";

      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { count: null, data: [], error: new Error("from_unavailable") };
      }

      // Build the initial query with optional count
      const selectOptions = options?.count ? { count: options.count } : undefined;
      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      let qb = (anyClient as any)
        .from(table as string)
        .select(selectColumns, selectOptions);

      // Apply where clause
      qb = where(qb);

      // Apply ordering if specified
      if (options?.orderBy && typeof qb.order === "function") {
        qb = qb.order(options.orderBy, { ascending: options.ascending ?? true });
      }

      // Apply pagination using range
      if (options?.limit !== undefined || options?.offset !== undefined) {
        const start = options?.offset ?? 0;
        const end =
          options?.limit !== undefined ? start + options.limit - 1 : undefined;
        if (end !== undefined && typeof qb.range === "function") {
          qb = qb.range(start, end);
        } else {
          if (options?.offset !== undefined && typeof qb.offset === "function") {
            qb = qb.offset(start);
          }
          if (options?.limit !== undefined && typeof qb.limit === "function") {
            qb = qb.limit(options.limit);
          }
        }
      }

      const { data, count, error } = await qb;

      if (error) {
        return { count: null, data: [], error };
      }

      const rows = (data ?? []) as TableRow<S, T>[];
      span.setAttribute("db.supabase.row_count", rows.length);

      // Validate output if schema exists
      const rowSchema = schema?.row;
      if (rowSchema && shouldValidate && rows.length > 0) {
        try {
          const validated = rows.map((row) => rowSchema.parse(row)) as TableRow<S, T>[];
          return { count: count ?? null, data: validated, error: null };
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { count: null, data: [], error: validationError };
        }
      }

      return { count: count ?? null, data: rows, error: null };
    }
  );
}

/**
 * Inserts multiple rows into the specified table and returns all inserted records.
 * Unlike `insertSingle`, this handles batch inserts without `.single()`.
 * Validates input and output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param values Array of insert payloads (validated via Zod schema)
 * @returns Array of inserted rows (validated) and error (if any)
 */
export function insertMany<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  values: TableInsert<S, T>[],
  options?: { schema?: S; validate?: boolean }
): Promise<{ data: TableRow<S, T>[]; error: unknown }> {
  return withTelemetrySpan(
    "supabase.insert",
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.batch_size": values.length,
        "db.supabase.operation": "insert",
        "db.supabase.table": table,
        "db.system": "postgres",
      },
    },
    async (span) => {
      const schemaName = resolveSchema(options?.schema);
      const shouldValidate = options?.validate ?? true;
      if (values.length === 0) {
        return { data: [], error: null };
      }

      // Validate input if schema exists
      const schema = getValidationSchema(schemaName, table as string);
      if (schema?.insert && shouldValidate) {
        try {
          for (const value of values) {
            schema.insert.parse(value);
          }
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { data: [], error: validationError };
        }
      }

      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const anyClient = getFromClient(client, schemaName) as any;
      if (!anyClient) {
        return { data: [], error: new Error("from_unavailable") };
      }
      // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
      const insertQb = (anyClient as any)
        .from(table as string)
        .insert(values as unknown);

      // Chain select to return the inserted rows
      if (insertQb && typeof insertQb.select === "function") {
        const { data, error } = await insertQb.select();
        if (error) return { data: [], error };

        const rows = (data ?? []) as TableRow<S, T>[];
        span.setAttribute("db.supabase.row_count", rows.length);

        // Validate output if schema exists
        const rowSchema = schema?.row;
        if (rowSchema && shouldValidate && rows.length > 0) {
          try {
            const validated = rows.map((row) => rowSchema.parse(row)) as TableRow<
              S,
              T
            >[];
            return { data: validated, error: null };
          } catch (validationError) {
            if (validationError instanceof Error) {
              recordErrorOnSpan(span, validationError);
            }
            return { data: [], error: validationError };
          }
        }
        return { data: rows, error: null };
      }
      return { data: [], error: null };
    }
  );
}
