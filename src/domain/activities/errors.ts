/**
 * @fileoverview Domain-level errors for activities service.
 */

/**
 * Error thrown when an activity cannot be found.
 */
export class NotFoundError extends Error {
  readonly code = "NOT_FOUND" as const;

  constructor(message: string) {
    super(message);
    this.name = "NotFoundError";
    Object.setPrototypeOf(this, NotFoundError.prototype);
  }
}

/**
 * Type guard to check if an error is a NotFoundError.
 *
 * @param error - Error to check.
 * @returns True if error is a NotFoundError.
 */
export function isNotFoundError(error: unknown): error is NotFoundError {
  return (
    error instanceof NotFoundError ||
    (error instanceof Error &&
      "code" in error &&
      (error as { code: unknown }).code === "NOT_FOUND")
  );
}
