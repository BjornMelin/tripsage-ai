/**
 * @fileoverview Shared types for currency store slices.
 */

export type StoreLogger = {
  error: (message: string, details?: Record<string, unknown>) => void;
  info: (message: string, details?: Record<string, unknown>) => void;
  warn: (message: string, details?: Record<string, unknown>) => void;
};
