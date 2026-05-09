/**
 * @fileoverview Date input value normalization shared by search forms.
 */

export const dateInputValue = (value: unknown): string =>
  typeof value === "string" ? value : "";
