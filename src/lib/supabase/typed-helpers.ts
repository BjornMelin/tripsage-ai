/**
 * @fileoverview Typed helper utilities for Supabase CRUD operations with Zod validation. These helpers centralize runtime validation using Zod schemas while preserving compile-time shapes using the generated `Database` types.
 */

import { getSupabaseSchema, type SupabaseSchemaName } from "@schemas/supabase";
import type { SupabaseClient } from "@supabase/supabase-js";
import { z } from "zod";
import { recordErrorOnSpan, withTelemetrySpan } from "@/lib/telemetry/span";
import type { Database } from "./database.types";

export type TypedClient = SupabaseClient<Database>;

type SchemaName = Extract<SupabaseSchemaName, keyof Database>;
type TableName<S extends SchemaName> = Extract<keyof Database[S]["Tables"], string>;
type TableRow<S extends SchemaName, T extends TableName<S>> =
  Database[S]["Tables"][T] extends Record<"Row", infer R> ? R : never;
type TableInsert<S extends SchemaName, T extends TableName<S>> =
  Database[S]["Tables"][T] extends Record<"Insert", infer I> ? I : never;
type TableUpdate<S extends SchemaName, T extends TableName<S>> =
  Database[S]["Tables"][T] extends Record<"Update", infer U> ? U : never;
/**
 * Query builder type alias for Supabase chaining with minimal shape.
 * Keep this loose enough for test doubles while avoiding `any`.
 */
export type TableFilterBuilder = {
  eq: (column: string, value: unknown) => TableFilterBuilder;
  in: (column: string, values: readonly unknown[]) => TableFilterBuilder;
  is: (column: string, value: boolean | null) => TableFilterBuilder;
  gt: (column: string, value: unknown) => TableFilterBuilder;
  gte: (column: string, value: unknown) => TableFilterBuilder;
  lt: (column: string, value: unknown) => TableFilterBuilder;
  lte: (column: string, value: unknown) => TableFilterBuilder;
  neq: (column: string, value: unknown) => TableFilterBuilder;
  like: (column: string, pattern: string) => TableFilterBuilder;
  ilike: (column: string, pattern: string) => TableFilterBuilder;
  contains: (column: string, value: unknown) => TableFilterBuilder;
  overlaps: (column: string, value: readonly unknown[]) => TableFilterBuilder;
  order: (
    column: string,
    options?: {
      ascending?: boolean;
      foreignTable?: string;
      nullsFirst?: boolean;
      referencedTable?: string;
    }
  ) => TableFilterBuilder;
  select: (
    columns?: string,
    options?: { count?: CountPreference }
  ) => TableFilterBuilder;
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
  select: (
    columns?: string,
    options?: { count?: CountPreference }
  ) => TableFilterBuilder;
  insert: (values: unknown) => TableFilterBuilder;
  update: (values: unknown, options?: unknown) => TableFilterBuilder;
  upsert: (values: unknown, options?: unknown) => TableFilterBuilder;
  delete: (options?: { count?: CountPreference }) => TableFilterBuilder;
};

type TableOperation = keyof TableQueryBuilder;

type SupabaseTableSchema = {
  insert?: z.ZodTypeAny;
  row?: z.ZodTypeAny;
  update?: z.ZodTypeAny;
};

type CountPreference = "exact" | "planned" | "estimated";

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

const getTableBuilder = (
  client: TypedClient,
  schema: SchemaName,
  table: string,
  operation: TableOperation
): TableQueryBuilder | Error => {
  const schemaClient = getFromClient(client, schema);
  if (!schemaClient) {
    return new Error("from_unavailable");
  }

  const base = schemaClient.from(table);
  if (typeof base[operation] !== "function") {
    return new Error(`${operation}_unavailable`);
  }
  return base;
};

const resolveValidationSchema = (
  schema: SchemaName,
  table: string,
  shouldValidate: boolean
): SupabaseTableSchema | Error | undefined => {
  const tableSchema = getSupabaseSchema(table as never, { schema }) as
    | SupabaseTableSchema
    | undefined;
  if (shouldValidate && !tableSchema) {
    return new Error(`unsupported_table_for_validation:${schema}.${table}`);
  }
  return tableSchema;
};

const failWithError = <T extends object>(
  span: Parameters<typeof recordErrorOnSpan>[0],
  error: unknown,
  fallback: T
): T & { error: unknown } => {
  if (error instanceof Error) {
    recordErrorOnSpan(span, error);
  }
  return { ...fallback, error };
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
 * Use `options.select` to limit returned columns; validation defaults to
 * `false` when selecting partial columns.
 * Explicit validation with partial selects returns an error.
 * When `options.select` is provided, callers must set `validate: false`; the
 * returned data only contains the requested columns and is intentionally not
 * validated against the full row schema.
 *
 * Note: This function accepts only single objects, not arrays.
 * For batch inserts, use `insertMany` instead.
 *
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param values - Insert payload (validated via Zod schema).
 * @param options - Optional schema selection, select columns, and validation toggle.
 * @returns Selected row (validated) and error (if any).
 */
export function insertSingle<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  values: TableInsert<S, T>,
  options?: { schema?: S; select?: string; validate?: boolean }
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
      const selectColumns = options?.select ?? "*";
      if (options?.validate === true && selectColumns !== "*") {
        const error = new Error("partial_select_validation_unavailable");
        recordErrorOnSpan(span, error);
        return { data: null, error };
      }
      const shouldValidate = options?.validate ?? selectColumns === "*";
      const schema = resolveValidationSchema(
        schemaName,
        table as string,
        shouldValidate
      );
      if (schema instanceof Error) {
        return failWithError(span, schema, { data: null });
      }
      // Validate input if schema exists
      if (Array.isArray(values)) {
        const error = new Error("insert_single_requires_object");
        recordErrorOnSpan(span, error);
        return { data: null, error };
      }
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

      const base = getTableBuilder(client, schemaName, table, "insert");
      if (base instanceof Error) return { data: null, error: base };
      const insertQb = base.insert(values as unknown);
      // Some tests stub a very lightweight query builder without select/single methods.
      // Gracefully handle those by treating the insert as fire-and-forget.
      if (insertQb && typeof insertQb.select === "function") {
        const selected =
          selectColumns === "*" ? insertQb.select() : insertQb.select(selectColumns);
        const { data, error } = await selected.single();
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
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param updates - Partial update payload (validated via Zod schema).
 * @param where - Closure to apply filters to the builder.
 * @param options - Optional schema, select columns, and validation toggle.
 * @returns Selected row (validated) and error (if any).
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
      const schema = resolveValidationSchema(
        schemaName,
        table as string,
        shouldValidate
      );
      if (schema instanceof Error) {
        return failWithError(span, schema, { data: null });
      }
      // Validate input if schema exists
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

      const base = getTableBuilder(client, schemaName, table, "update");
      if (base instanceof Error) return { data: null, error: base };
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
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param updates - Partial update payload (validated via Zod schema).
 * @param where - Closure to apply filters to the builder.
 * @param options - Optional schema, validation toggle, and count preference.
 * @returns Count of updated rows and error (if any).
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
      const schema = resolveValidationSchema(
        schemaName,
        table as string,
        shouldValidate
      );
      if (schema instanceof Error) {
        return failWithError(span, schema, { count: 0 });
      }
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

      const base = getTableBuilder(client, schemaName, table, "update");
      if (base instanceof Error) return { count: 0, error: base };
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
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param where - Closure to apply filters to the builder.
 * @param options - Optional schema, select columns, and validation toggle.
 * @returns Selected row (validated) and error (if any).
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
      const selectColumns = options?.select ?? "*";
      const shouldValidate = options?.validate ?? selectColumns === "*";
      const schema = resolveValidationSchema(
        schemaName,
        table as string,
        shouldValidate
      );
      if (schema instanceof Error) {
        return failWithError(span, schema, { data: null });
      }

      const base = getTableBuilder(client, schemaName, table, "select");
      if (base instanceof Error) return { data: null, error: base };
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

type DeleteOptions<S extends SchemaName> = {
  schema?: S;
  count?: CountPreference | null;
  limit?: number;
  returning?: "representation";
  select?: string;
};

const multiRowDeleteError = (count: number): Error | null =>
  count > 1 ? new Error("delete_single_matched_multiple_rows") : null;

const deleteRows = async <
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: DeleteOptions<S>
): Promise<{ count: number; error: unknown | null }> =>
  withTelemetrySpan(
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
      const base = getTableBuilder(client, schemaName, table, "delete");
      if (base instanceof Error) return { count: 0, error: base };

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

      const filtered = where(returningBuilder);
      const qb =
        options?.limit === undefined ? filtered : filtered.limit(options.limit);
      const { count, error } = await qb;
      span.setAttribute("db.supabase.row_count", count ?? 0);
      return { count: count ?? 0, error: error ?? null };
    }
  );

const countDeleteCandidates = async <
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: DeleteOptions<S>
): Promise<{ count: number; error: unknown | null }> =>
  withTelemetrySpan(
    "supabase.delete.preflight",
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
      const base = getTableBuilder(client, schemaName, table, "select");
      if (base instanceof Error) return { count: 0, error: base };

      const selectColumns = options?.select ?? "id";
      const qb = where(base.select(selectColumns, { count: "exact" }).limit(2));
      const { count, data, error } = await qb;
      if (error) return { count: 0, error };

      const rowCount =
        count ??
        (Array.isArray(data)
          ? data.length
          : data === null || data === undefined
            ? 0
            : 1);
      span.setAttribute("db.supabase.row_count", rowCount);
      return { count: rowCount, error: null };
    }
  );

/**
 * Deletes at most one row from the specified table matching the given criteria.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, etc.) prior to deletion. This helper requests a count and returns an
 * error if the filter matches more than one row. Use `deleteMany` for bulk
 * deletes or no-count cleanup operations.
 *
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param where - Closure to apply filters to the builder.
 * @param options - Optional schema, count preference, returning mode, and select columns.
 * @returns Count of deleted rows and error (if any).
 */
export async function deleteSingle<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: DeleteOptions<S>
): Promise<{ count: number; error: unknown | null }> {
  if (options?.count === null) {
    return { count: 0, error: new Error("delete_single_requires_count") };
  }

  const candidateResult = await countDeleteCandidates(client, table, where, options);
  if (candidateResult.error) return candidateResult;
  if (candidateResult.count === 0) return candidateResult;
  const preflightError = multiRowDeleteError(candidateResult.count);
  if (preflightError) {
    return {
      count: candidateResult.count,
      error: preflightError,
    };
  }

  const deleteResult = await deleteRows(client, table, where, {
    ...options,
    count: options?.count ?? "exact",
    limit: 1,
  });
  if (deleteResult.error) return deleteResult;

  const deleteCountError = multiRowDeleteError(deleteResult.count);
  return deleteCountError ? { ...deleteResult, error: deleteCountError } : deleteResult;
}

/**
 * Deletes rows from the specified table matching the given criteria.
 * Naming aligns with bulk operations (e.g., updateMany). This helper does not
 * enforce single-row effects and is the only supported path for no-count
 * cleanup deletes.
 *
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param where - Closure to apply filters to the builder.
 * @param options - Optional schema and count preference.
 * @returns Count of deleted rows and error (if any).
 */
export function deleteMany<
  S extends SchemaName = "public",
  T extends TableName<S> = TableName<S>,
>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder) => TableFilterBuilder,
  options?: DeleteOptions<S>
): Promise<{ count: number; error: unknown | null }> {
  return deleteRows(client, table, where, options);
}

/**
 * Fetches a single row from the specified table, returning null if not found.
 * Uses `.maybeSingle()` instead of `.single()` to avoid PGRST116 errors.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to selecting the row.
 * Validates output using Zod schemas when available.
 *
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param where - Closure to apply filters to the builder.
 * @param options - Optional schema, select columns, and validation toggle.
 * @returns Selected row (validated) or null, and error (if any).
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
      const selectColumns = options?.select ?? "*";
      const shouldValidate = options?.validate ?? selectColumns === "*";
      const schema = resolveValidationSchema(
        schemaName,
        table as string,
        shouldValidate
      );
      if (schema instanceof Error) {
        return failWithError(span, schema, { data: null });
      }

      const base = getTableBuilder(client, schemaName, table, "select");
      if (base instanceof Error) return { data: null, error: base };
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
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param values - Upsert payload (validated via Zod schema).
 * @param onConflict - Column name(s) to determine conflict (e.g., "user_id").
 * @param options - Optional schema and validation toggle.
 * @returns Selected row (validated) and error (if any).
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
      const schema = resolveValidationSchema(
        schemaName,
        table as string,
        shouldValidate
      );
      if (schema instanceof Error) {
        return failWithError(span, schema, { data: null });
      }
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

      const base = getTableBuilder(client, schemaName, table, "upsert");
      if (base instanceof Error) return { data: null, error: base };
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
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param values - Array of upsert payloads (validated via Zod schema).
 * @param onConflict - Column name(s) to determine conflict (e.g., "user_id").
 * @param options - Optional schema and validation toggle.
 * @returns Array of upserted rows (validated) and error (if any).
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

      const schema = resolveValidationSchema(
        schemaName,
        table as string,
        shouldValidate
      );
      if (schema instanceof Error) {
        return failWithError(span, schema, { data: [] });
      }
      if (schema?.insert && shouldValidate) {
        try {
          z.array(schema.insert).parse(values);
        } catch (validationError) {
          if (validationError instanceof Error) {
            recordErrorOnSpan(span, validationError);
          }
          return { data: [], error: validationError };
        }
      }

      const base = getTableBuilder(client, schemaName, table, "upsert");
      if (base instanceof Error) return { data: [], error: base };
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
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param where - Closure to apply filters to the builder.
 * @param options - Optional pagination, ordering, and count settings.
 * @returns Array of rows (validated), count if requested, and error (if any).
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
      const selectColumns = options?.select ?? "*";
      const shouldValidate = options?.validate ?? selectColumns === "*";
      const schema = resolveValidationSchema(
        schemaName,
        table as string,
        shouldValidate
      );
      if (schema instanceof Error) {
        return failWithError(span, schema, { count: null, data: [] });
      }

      // Build the initial query with optional count
      const selectOptions = options?.count ? { count: options.count } : undefined;
      const base = getTableBuilder(client, schemaName, table, "select");
      if (base instanceof Error) return { count: null, data: [], error: base };
      let qb = base.select(selectColumns, selectOptions);

      // Apply where clause
      qb = where(qb);

      // Apply ordering if specified
      if (options?.orderBy && typeof qb.order === "function") {
        qb = qb.order(options.orderBy, { ascending: options.ascending ?? true });
      }

      // Pagination: when options.offset is set without options.limit, end is undefined so
      // we intentionally skip qb.range and fall back to qb.offset(start) (and qb.limit if
      // present) to support the offset-only path.
      // Apply pagination using range
      if (options?.limit !== undefined || options?.offset !== undefined) {
        const start = options?.offset ?? 0;
        const end =
          options?.limit === undefined ? undefined : start + options.limit - 1;
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
 * @typeParam S - Supabase schema name for the target table.
 * @typeParam T - Table name within the selected schema.
 * @param client - Typed Supabase client.
 * @param table - Target table name.
 * @param values - Array of insert payloads (validated via Zod schema).
 * @param options - Optional schema and validation toggle.
 * @returns Array of inserted rows (validated) and error (if any).
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

      const schema = resolveValidationSchema(
        schemaName,
        table as string,
        shouldValidate
      );
      if (schema instanceof Error) {
        return failWithError(span, schema, { data: [] });
      }
      // Validate input if schema exists
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

      const base = getTableBuilder(client, schemaName, table, "insert");
      if (base instanceof Error) return { data: [], error: base };
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
