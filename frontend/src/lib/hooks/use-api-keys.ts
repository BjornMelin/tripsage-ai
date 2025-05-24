"use client";

import {
  useApiQuery,
  useApiMutation,
  useApiDeleteMutation,
} from "@/lib/hooks/use-api-query";
import { useApiKeyStore } from "@/stores/api-key-store";
import type {
  AddKeyRequest,
  AddKeyResponse,
  AllKeysResponse,
  DeleteKeyResponse,
  ValidateKeyResponse,
} from "@/types/api-keys";

/**
 * Hook for fetching all user API keys
 */
export function useApiKeys() {
  const { setKeys, setSupportedServices } = useApiKeyStore();

  return useApiQuery<AllKeysResponse>(
    "/api/user/keys",
    {},
    {
      onSuccess: (data) => {
        setKeys(data.keys);
        setSupportedServices(data.supported_services);
      },
    }
  );
}

/**
 * Hook for adding a new API key
 */
export function useAddApiKey() {
  const { updateKey } = useApiKeyStore();

  return useApiMutation<AddKeyResponse, AddKeyRequest>("/api/user/keys", {
    onSuccess: (data) => {
      updateKey(data.service, {
        is_valid: data.is_valid,
        has_key: true,
        service: data.service,
        last_validated: new Date().toISOString(),
      });
    },
  });
}

/**
 * Hook for validating an API key without saving it
 */
export function useValidateApiKey() {
  return useApiMutation<ValidateKeyResponse, AddKeyRequest>(
    "/api/user/keys/validate"
  );
}

/**
 * Hook for deleting an API key
 */
export function useDeleteApiKey() {
  const { removeKey } = useApiKeyStore();

  return useApiDeleteMutation<DeleteKeyResponse, string>("/api/user/keys", {
    onSuccess: (data) => {
      if (data.success) {
        removeKey(data.service);
      }
    },
  });
}
