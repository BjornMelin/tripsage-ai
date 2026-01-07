/**
 * @fileoverview Domain-specific errors for Google API client wrappers.
 */

/**
 * Error codes that can be surfaced to API consumers for Places Photo requests.
 */
export type GooglePlacesPhotoErrorCode =
  | "invalid_photo_name"
  | "missing_photo_dimensions"
  | "invalid_photo_dimensions"
  | "redirect_host_not_allowed"
  | "redirect_limit_exceeded";

/**
 * Error thrown when Places Photo request validation fails (or redirect rules are violated).
 */
export class GooglePlacesPhotoError extends Error {
  constructor(
    message: string,
    public code: GooglePlacesPhotoErrorCode,
    public status: number
  ) {
    super(message);
    this.name = "GooglePlacesPhotoError";
  }
}
