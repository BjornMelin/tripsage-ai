/**
 * Normalizes form state into a string accepted by date inputs.
 *
 * @param value - Raw value from form state.
 * @returns A date input string, or an empty string for non-string values.
 */
export const dateInputValue = (value: unknown): string =>
  typeof value === "string" ? value : "";
