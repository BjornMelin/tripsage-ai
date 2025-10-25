/**
 * @fileoverview Types for API key management.
 */

export interface ApiKey {
  id?: string;
  service: string;
  has_key: boolean;
  is_valid: boolean;
  last_validated?: string;
  last_used?: string;
}

export interface AllKeysResponse {
  keys: Record<string, ApiKey>;
  supported_services: string[];
}

export interface AddKeyRequest {
  service: string;
  api_key: string;
  save: boolean;
}

export interface AddKeyResponse {
  service: string;
  is_valid: boolean;
  message: string;
}

export interface ValidateKeyResponse {
  service: string;
  is_valid: boolean;
  message: string;
  details?: Record<string, unknown>;
}

export interface DeleteKeyResponse {
  service: string;
  success: boolean;
  message: string;
}
