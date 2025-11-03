"use client";

import {
  type UseMutationOptions,
  type UseQueryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { z } from "zod";
import { type AppError, handleApiError } from "@/lib/api/error-types";
import { useAuthenticatedApi } from "./use-authenticated-api";

// Zod schemas for validation
const API_QUERY_PARAMS_SCHEMA = z
  .record(z.string(), z.union([z.string(), z.number(), z.boolean()]))
  .optional();

const ENDPOINT_SCHEMA = z.string().min(1, "Endpoint cannot be empty");

const _HttpMethodSchema = z.enum(["GET", "POST", "PUT", "PATCH", "DELETE"]);

// type definitions with proper generics
type ApiQueryOptions<Data, Error = AppError> = Omit<
  UseQueryOptions<Data, Error, Data, readonly unknown[]>,
  "queryKey" | "queryFn"
> & {
  queryKey?: readonly unknown[];
};

type ApiMutationOptions<Data, Variables, Error = AppError> = Omit<
  UseMutationOptions<Data, Error, Variables, unknown>,
  "mutationFn"
> & {
  invalidateQueries?: readonly unknown[][];
  optimisticUpdate?: {
    queryKey: readonly unknown[];
    updater: (old: unknown, variables: Variables) => unknown;
  };
};

export interface MutationContext<Variables = unknown> {
  previousData?: unknown;
  optimisticData?: unknown;
  variables?: Variables;
  onMutateResult?: unknown;
}

// Hook for GET requests with enhanced error handling and TypeScript
export function useApiQuery<Data = unknown, Error = AppError>(
  endpoint: string,
  params?: Record<string, unknown>,
  options?: ApiQueryOptions<Data, Error>
) {
  // Validate inputs with Zod
  const validatedEndpoint = ENDPOINT_SCHEMA.parse(endpoint);
  const validatedParams = API_QUERY_PARAMS_SCHEMA.parse(params);

  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  // Use provided queryKey or generate default
  const queryKey = options?.queryKey || [
    validatedEndpoint,
    ...(validatedParams ? [validatedParams] : []),
  ];

  return useQuery<Data, Error, Data, readonly unknown[]>({
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<Data>(validatedEndpoint, {
          params: validatedParams,
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey,
    throwOnError: false, // Let components handle errors
    ...options,
  });
}

// Hook for POST requests with optimistic updates and proper error handling
export function useApiMutation<Data = unknown, Variables = unknown, Error = AppError>(
  endpoint: string,
  options?: ApiMutationOptions<Data, Variables, Error>
) {
  const queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<Data, Error, Variables, MutationContext<Variables>>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<Data>(endpoint, {
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onError: (error, variables, context) => {
      // Rollback optimistic updates
      if (context?.previousData && options?.optimisticUpdate) {
        queryClient.setQueryData(
          options.optimisticUpdate.queryKey,
          context.previousData
        );
      }

      // Call user-defined onError
      options?.onError?.(error, variables, context?.onMutateResult, {
        client: queryClient,
        meta: undefined,
      });
    },
    onMutate: async (variables) => {
      const context: MutationContext<Variables> = { variables };

      // Handle optimistic updates
      if (options?.optimisticUpdate) {
        const { queryKey, updater } = options.optimisticUpdate;

        // Cancel outgoing refetches
        await queryClient.cancelQueries({ queryKey });

        // Snapshot previous value
        context.previousData = queryClient.getQueryData(queryKey);

        // Optimistically update cache
        const optimisticData = updater(context.previousData, variables);
        queryClient.setQueryData(queryKey, optimisticData);
        context.optimisticData = optimisticData;
      }

      // Call user-defined onMutate
      if (options?.onMutate) {
        const userContext = await options.onMutate(variables, {
          client: queryClient,
          meta: undefined,
        });
        context.onMutateResult = userContext;
        Object.assign(context, userContext as object);
      }

      return context;
    },
    onSettled: (data, error, variables, context) => {
      // Refetch optimistic update query on settle
      if (options?.optimisticUpdate) {
        queryClient.invalidateQueries({ queryKey: options.optimisticUpdate.queryKey });
      }

      // Call user-defined onSettled
      options?.onSettled?.(data, error, variables, context?.onMutateResult, {
        client: queryClient,
        meta: undefined,
      });
    },
    onSuccess: (data, variables, context) => {
      // Invalidate specified queries
      if (options?.invalidateQueries) {
        options.invalidateQueries.forEach((queryKey) => {
          queryClient.invalidateQueries({ queryKey });
        });
      }

      // Call user-defined onSuccess
      options?.onSuccess?.(data, variables, context?.onMutateResult, {
        client: queryClient,
        meta: undefined,
      });
    },
    throwOnError: false, // Let components handle errors
    // Exclude our custom options from the base mutation options
    ...Object.fromEntries(
      Object.entries(options || {}).filter(
        ([key]) => !["invalidateQueries", "optimisticUpdate"].includes(key)
      )
    ),
  });
}

// Hook for PUT requests
export function useApiPutMutation<
  Data = unknown,
  Variables = unknown,
  Error = AppError,
>(endpoint: string, options?: ApiMutationOptions<Data, Variables, Error>) {
  return useApiMutationWithMethod("PUT", endpoint, options);
}

// Hook for PATCH requests
export function useApiPatchMutation<
  Data = unknown,
  Variables = unknown,
  Error = AppError,
>(endpoint: string, options?: ApiMutationOptions<Data, Variables, Error>) {
  return useApiMutationWithMethod("PATCH", endpoint, options);
}

// Hook for DELETE requests
export function useApiDeleteMutation<
  Data = unknown,
  Variables = unknown,
  Error = AppError,
>(endpoint: string, options?: ApiMutationOptions<Data, Variables, Error>) {
  const queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<Data, Error, Variables, MutationContext<Variables>>({
    mutationFn: async (variables) => {
      try {
        // Handle both string variables (ID) and object variables
        const deleteEndpoint =
          typeof variables === "string" || typeof variables === "number"
            ? `${endpoint}/${variables}`
            : endpoint;

        return await makeAuthenticatedRequest<Data>(deleteEndpoint, {
          method: "DELETE",
          ...(typeof variables === "object" &&
            variables !== null && {
              body: JSON.stringify(variables),
              headers: { "Content-Type": "application/json" },
            }),
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onError: (error, variables, context) => {
      if (context?.previousData && options?.optimisticUpdate) {
        queryClient.setQueryData(
          options.optimisticUpdate.queryKey,
          context.previousData
        );
      }
      options?.onError?.(error, variables, context?.onMutateResult, {
        client: queryClient,
        meta: undefined,
      });
    },
    onMutate: async (variables) => {
      const context: MutationContext<Variables> = { variables };

      // Handle optimistic updates
      if (options?.optimisticUpdate) {
        const { queryKey, updater } = options.optimisticUpdate;

        await queryClient.cancelQueries({ queryKey });
        context.previousData = queryClient.getQueryData(queryKey);

        const optimisticData = updater(context.previousData, variables);
        queryClient.setQueryData(queryKey, optimisticData);
        context.optimisticData = optimisticData;
      }

      if (options?.onMutate) {
        const userContext = await options.onMutate(variables, {
          client: queryClient,
          meta: undefined,
        });
        context.onMutateResult = userContext;
        Object.assign(context, userContext as object);
      }

      return context;
    },
    onSettled: (data, error, variables, context) => {
      if (options?.optimisticUpdate) {
        queryClient.invalidateQueries({ queryKey: options.optimisticUpdate.queryKey });
      }
      options?.onSettled?.(data, error, variables, context?.onMutateResult, {
        client: queryClient,
        meta: undefined,
      });
    },
    onSuccess: (data, variables, context) => {
      if (options?.invalidateQueries) {
        options.invalidateQueries.forEach((queryKey) => {
          queryClient.invalidateQueries({ queryKey });
        });
      }
      options?.onSuccess?.(data, variables, context?.onMutateResult, {
        client: queryClient,
        meta: undefined,
      });
    },
    throwOnError: false,
    ...Object.fromEntries(
      Object.entries(options || {}).filter(
        ([key]) => !["invalidateQueries", "optimisticUpdate"].includes(key)
      )
    ),
  });
}

// Helper function for PUT/PATCH mutations
function useApiMutationWithMethod<
  Data = unknown,
  Variables = unknown,
  Error = AppError,
>(
  method: "PUT" | "PATCH",
  endpoint: string,
  options?: ApiMutationOptions<Data, Variables, Error>
) {
  const queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<Data, Error, Variables, MutationContext<Variables>>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<Data>(endpoint, {
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
          method,
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onError: (error, variables, context) => {
      if (context?.previousData && options?.optimisticUpdate) {
        queryClient.setQueryData(
          options.optimisticUpdate.queryKey,
          context.previousData
        );
      }
      options?.onError?.(error, variables, context?.onMutateResult, {
        client: queryClient,
        meta: undefined,
      });
    },
    onMutate: async (variables) => {
      const context: MutationContext<Variables> = { variables };

      if (options?.optimisticUpdate) {
        const { queryKey, updater } = options.optimisticUpdate;

        await queryClient.cancelQueries({ queryKey });
        context.previousData = queryClient.getQueryData(queryKey);

        const optimisticData = updater(context.previousData, variables);
        queryClient.setQueryData(queryKey, optimisticData);
        context.optimisticData = optimisticData;
      }

      if (options?.onMutate) {
        const userContext = await options.onMutate(variables, {
          client: queryClient,
          meta: undefined,
        });
        context.onMutateResult = userContext;
        Object.assign(context, userContext as object);
      }

      return context;
    },
    onSettled: (data, error, variables, context) => {
      if (options?.optimisticUpdate) {
        queryClient.invalidateQueries({ queryKey: options.optimisticUpdate.queryKey });
      }
      options?.onSettled?.(data, error, variables, context?.onMutateResult, {
        client: queryClient,
        meta: undefined,
      });
    },
    onSuccess: (data, variables, context) => {
      if (options?.invalidateQueries) {
        options.invalidateQueries.forEach((queryKey) => {
          queryClient.invalidateQueries({ queryKey });
        });
      }
      options?.onSuccess?.(data, variables, context?.onMutateResult, {
        client: queryClient,
        meta: undefined,
      });
    },
    throwOnError: false,
    ...Object.fromEntries(
      Object.entries(options || {}).filter(
        ([key]) => !["invalidateQueries", "optimisticUpdate"].includes(key)
      )
    ),
  });
}
