"use client";

import {
  useApiDeleteMutation,
  useApiMutation,
  useApiQuery,
} from "@/hooks/use-api-query";
import { useApiKeyStore } from "@/stores/api-key-store";
import type {
  AddKeyRequest,
  AddKeyResponse,
  AllKeysResponse,
  DeleteKeyResponse,
  ValidateKeyResponse,
} from "@/types/api-keys";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

/**
 * Hook for fetching all user API keys
 */
export function useApiKeys() {
  const { setKeys, setSupportedServices } = useApiKeyStore();

  const query = useApiQuery<AllKeysResponse>("/api/user/keys", {});

  useEffect(() => {
    if (query.data) {
      setKeys(query.data.keys);
      setSupportedServices(query.data.supported_services);
    }
  }, [query.data, setKeys, setSupportedServices]);

  return query;
}

/**
 * Hook for adding a new API key
 */
export function useAddApiKey() {
  const { updateKey } = useApiKeyStore();
  const queryClient = useQueryClient();

  const mutation = useApiMutation<AddKeyResponse, AddKeyRequest>("/api/user/keys");

  useEffect(() => {
    if (mutation.data) {
      updateKey(mutation.data.service, {
        is_valid: mutation.data.is_valid,
        has_key: true,
        service: mutation.data.service,
        last_validated: new Date().toISOString(),
      });
      // Invalidate the API keys query to refetch the updated list
      queryClient.invalidateQueries({ queryKey: ["/api/user/keys"] });
    }
  }, [mutation.data, updateKey, queryClient]);

  return mutation;
}

/**
 * Hook for validating an API key without saving it
 */
export function useValidateApiKey() {
  return useApiMutation<ValidateKeyResponse, AddKeyRequest>("/api/user/keys/validate");
}

/**
 * Hook for deleting an API key
 */
export function useDeleteApiKey() {
  const { removeKey } = useApiKeyStore();
  const queryClient = useQueryClient();

  const mutation = useApiDeleteMutation<DeleteKeyResponse, string>("/api/user/keys");

  useEffect(() => {
    if (mutation.data?.success) {
      removeKey(mutation.data.service);
      // Invalidate the API keys query to refetch the updated list
      queryClient.invalidateQueries({ queryKey: ["/api/user/keys"] });
    }
  }, [mutation.data, removeKey, queryClient]);

  return mutation;
}
