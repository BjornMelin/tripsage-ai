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
 * Query builder type alias for Supabase chaining with minimal shape.
 * Keep this loose enough for test doubles while avoiding `any`.
 */
export type TableFilterBuilder = {
  eq: (...args: unknown[]) => TableFilterBuilder;
  in: (...args: unknown[]) => TableFilterBuilder;
  is: (...args: unknown[]) => TableFilterBuilder;
  gt: (...args: unknown[]) => TableFilterBuilder;
  gte: (...args: unknown[]) => TableFilterBuilder;
  lt: (...args: unknown[]) => TableFilterBuilder;
  lte: (...args: unknown[]) => TableFilterBuilder;
  neq: (...args: unknown[]) => TableFilterBuilder;
  like: (...args: unknown[]) => TableFilterBuilder;
  ilike: (...args: unknown[]) => TableFilterBuilder;
  contains: (...args: unknown[]) => TableFilterBuilder;
  overlaps: (...args: unknown[]) => TableFilterBuilder;
  order: (...args: unknown[]) => TableFilterBuilder;
  select: (...args: unknown[]) => TableFilterBuilder;
  limit: (count: number) => TableFilterBuilder;
  offset?: (count: number) => TableFilterBuilder;
  range?: (from: number, to: number) => TableFilterBuilder;
  single: () => PromiseLike<{ data: unknown; error: unknown }>;
  maybeSingle: () => PromiseLike<{ data: unknown; error: unknown }>;
  count?: number | null;
  error?: unknown;
  data?: unknown;
  then?: unknown;
};

type TableQueryBuilder = {
  select: (...args: unknown[]) => TableFilterBuilder;
  insert: (values: unknown) => TableFilterBuilder;
  update: (values: unknown, options?: unknown) => TableFilterBuilder;
  upsert: (values: unknown, options?: unknown) => TableFilterBuilder;
  delete: (options?: unknown) => TableFilterBuilder;
};

type SupabaseTableSchema = {
  insert?: { parse: (value: unknown) => unknown };
  row?: { parse: (value: unknown) => unknown };
  update?: { parse: (value: unknown) => unknown };
};

type CountPreference = "exact" | "planned" | "estimated";

/**
 * Registry of tables supported by runtime Zod validation.
 * authoritative source: src/domain/schemas/supabase.ts
 * To add a new table:
 * 1. Ensure schema exists in src/domain/schemas/supabase.ts
 * 2. Add table name to the appropriate schema array below
 */
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

const getFromClient = (
  client: TypedClient,
  schema: SchemaName
): { from: (table: string) => TableQueryBuilder } | null => {
  const schemaClient =
    schema === "public" || typeof client.schema !== "function"
      ? client
      : client.schema(schema);
  if (!schemaClient || typeof schemaClient.from !== "function") {
    return null;
  }
  const schemaClientAny = schemaClient as { from: (table: string) => unknown };
  return {
    from: (table: string) => schemaClientAny.from(table as string) as TableQueryBuilder,
  };
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

const resolveMaybeSingle = async (
  qb: TableFilterBuilder
): Promise<{ data: unknown; error: unknown }> => {
  if (qb && typeof qb.maybeSingle === "function") {
    return await qb.maybeSingle();
  }

  if (qb && typeof qb.limit === "function") {
    const limited = qb.limit(1);
    if (limited && typeof limited.maybeSingle === "function") {
      return await limited.maybeSingle();
    }
    if (limited && typeof limited.single === "function") {
      return await limited.single();
    }
  }

  if (qb && typeof qb.single === "function") {
    return await qb.single();
  }

  return { data: null, error: new Error("maybeSingle_unavailable") };
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

      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      const base = schemaClient.from(table as string);
      if (typeof base.insert !== "function") {
        return { data: null, error: new Error("insert_unavailable") };
      }
      const insertQb = base.insert(values as unknown);
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
        return { data: data as TableRow<S, T>, error: null };
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
 * Use `options.select` to limit returned columns; validation defaults to
 * `false` when selecting partial columns.
 * Explicit validation with partial selects returns an error.
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
  options?: { schema?: S; select?: string; validate?: boolean }
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
      const selectColumns = options?.select ?? "*";
      if (options?.validate === true && selectColumns !== "*") {
        const error = new Error("partial_select_validation_unavailable");
        recordErrorOnSpan(span, error);
        return { data: null, error };
      }
      const shouldValidate = options?.validate ?? selectColumns === "*";
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

      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      const base = schemaClient.from(table as string);
      if (typeof base.update !== "function") {
        return { data: null, error: new Error("update_unavailable") };
      }
      const filtered = where(base.update(updates as unknown));
      if (filtered && typeof filtered.select === "function") {
        const { data, error } = await filtered.select(selectColumns).single();
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
      if (filtered && typeof filtered === "object" && "error" in filtered) {
        return {
          data: null,
          error: (filtered as { error?: unknown }).error ?? null,
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
 * Use `options.count` to control PostgREST count behavior; set to `null`
 * to skip counting entirely.
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
  options?: { schema?: S; validate?: boolean; count?: CountPreference | null }
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

      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { count: 0, error: new Error("from_unavailable") };
      }
      const base = schemaClient.from(table as string);
      if (typeof base.update !== "function") {
        return { count: 0, error: new Error("update_unavailable") };
      }
      const countPreference = options?.count;
      const updateBuilder =
        countPreference === null
          ? base.update(updates as unknown)
          : base.update(updates as unknown, { count: countPreference ?? "exact" });
      const qb = where(updateBuilder);
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

      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      const base = schemaClient.from(table as string);
      if (typeof base.select !== "function") {
        return { data: null, error: new Error("select_unavailable") };
      }
      const qb = where(base.select(selectColumns));
      if (qb && typeof qb === "object" && "error" in qb) {
        return { data: null, error: (qb as { error?: unknown }).error ?? null };
      }
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
      return { data: data as TableRow<S, T>, error: null };
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
 * Use `options.count` to request a PostgREST count preference; set to `null`
 * to skip counting entirely.
 * Use `options.returning: "representation"` (with `options.select`) to request
 * deleted rows when the caller needs return data or reliable count headers.
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
  options?: {
    schema?: S;
    count?: CountPreference | null;
    returning?: "representation";
    select?: string;
  }
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
      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { count: 0, error: new Error("from_unavailable") };
      }
      const base = schemaClient.from(table as string);

      if (typeof base.delete !== "function") {
        return { count: 0, error: new Error("delete_unavailable") };
      }

      const countPreference = options?.count;
      const deleteBuilder =
        countPreference === null
          ? base.delete()
          : base.delete({ count: countPreference ?? "exact" });

      const selectColumns = options?.select ?? "*";
      const returningBuilder =
        options?.returning === "representation" &&
        deleteBuilder &&
        typeof deleteBuilder.select === "function"
          ? deleteBuilder.select(selectColumns)
          : deleteBuilder;

      const qb = where(returningBuilder);
      const { count, error } = await qb;
      span.setAttribute("db.supabase.row_count", count ?? 0);
      return { count: count ?? 0, error: error ?? null };
    }
  );
}

/**
 * Deletes rows from the specified table matching the given criteria.
 * Naming aligns with bulk operations (e.g., updateMany) and does not enforce
 * single-row deletes.
 * NOTE: deleteMany is an intentional alias for deleteSingle, and deleteSingle
 * deletes all matching rows. This keeps naming consistent with updateMany and
 * insertMany while sharing the same implementation.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param where Closure to apply filters to the builder
 * @returns Count of deleted rows and error (if any)
 */
export function deleteMany<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: { schema?: S; count?: CountPreference | null }
): Promise<{ count: number; error: unknown | null }> {
  return deleteSingle(client, table, where, options);
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

      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      const base = schemaClient.from(table as string);
      if (typeof base.select !== "function") {
        return { data: null, error: new Error("select_unavailable") };
      }
      const qb = where(base.select(selectColumns));
      if (qb && typeof qb === "object" && "error" in qb) {
        return { data: null, error: (qb as { error?: unknown }).error ?? null };
      }
      const result = await resolveMaybeSingle(qb);
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

      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { data: null, error: new Error("from_unavailable") };
      }
      const base = schemaClient.from(table as string);
      if (typeof base.upsert !== "function") {
        return { data: null, error: new Error("upsert_unavailable") };
      }
      const upsertQb = base.upsert(values as unknown, {
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

      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { data: [], error: new Error("from_unavailable") };
      }
      const base = schemaClient.from(table as string);
      if (typeof base.upsert !== "function") {
        return { data: [], error: new Error("upsert_unavailable") };
      }
      const upsertQb = base.upsert(values as unknown, {
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
  count?: CountPreference;
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

      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { count: null, data: [], error: new Error("from_unavailable") };
      }

      // Build the initial query with optional count
      const selectOptions = options?.count ? { count: options.count } : undefined;
      const base = schemaClient.from(table as string);
      if (typeof base.select !== "function") {
        return { count: null, data: [], error: new Error("select_unavailable") };
      }
      let qb = base.select(selectColumns, selectOptions);

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

      const schemaClient = getFromClient(client, schemaName);
      if (!schemaClient) {
        return { data: [], error: new Error("from_unavailable") };
      }
      const base = schemaClient.from(table as string);
      if (typeof base.insert !== "function") {
        return { data: [], error: new Error("insert_unavailable") };
      }
      const insertQb = base.insert(values as unknown);

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
