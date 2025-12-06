/**
 * @fileoverview Shared AI prompt sanitization utilities.
 *
 * Provides functions to sanitize user inputs before interpolation into AI prompts,
 * preventing prompt injection attacks. Can be used across all AI-generating routes.
 *
 * @see https://owasp.org/www-project-top-ten/ (A03:2021 - Injection)
 */

/**
 * Common prompt injection patterns to detect.
 * These patterns are commonly used to hijack LLM behavior.
 */
export const FILTERED_MARKER = "[FILTERED]";

export const INJECTION_PATTERNS: ReadonlyArray<{
  pattern: RegExp;
  replacement: string;
}> = [
  // Directive commands that try to override system prompts
  {
    pattern: /(?:^|\b)(IMPORTANT|URGENT|SYSTEM|ADMIN|ROOT)\s*:/gi,
    replacement: `${FILTERED_MARKER}:`,
  },
  // Attempts to invoke tools or functions
  {
    pattern: /\b(invoke|call|execute|run)\s+(tool|function|command)/gi,
    replacement: FILTERED_MARKER,
  },
  // Attempts to ignore previous instructions
  {
    pattern: /ignore\s+(previous|above|all)\s+(instructions?|prompts?)/gi,
    replacement: FILTERED_MARKER,
  },
  // JSON injection attempts
  { pattern: /```json[\s\S]*?```/gi, replacement: "[CODE_BLOCK]" },
  // Role-playing attempts
  {
    pattern:
      /\b(?:pretend|act|behave|roleplay|please\s+(?:act|pretend))\s+(?:to\s+be|you\s+are|as|like)?\s*(?:a|an|the)?\s+[A-Za-z][\w\s.,-]*/gi,
    replacement: `${FILTERED_MARKER} `,
  },
];

/**
 * Sanitize a string for safe use in AI prompts.
 *
 * Removes control characters, collapses whitespace, and limits length.
 * Does NOT detect injection patterns - use `hasInjectionRisk()` for that.
 *
 * @param input - The string to sanitize.
 * @param maxLength - Maximum allowed length (default: 200).
 * @returns Sanitized string safe for prompt interpolation.
 *
 * @example
 * ```ts
 * const safeName = sanitizeForPrompt(userInput.name, 100);
 * const prompt = `Analyze hotel: "${safeName}"`;
 * ```
 */
export function sanitizeForPrompt(input: string, maxLength = 200): string {
  if (typeof input !== "string") {
    return "";
  }

  // biome-ignore lint/suspicious/noControlCharactersInRegex: intentional - removing control chars for security
  const controlCharPattern = /[\x00-\x1F\x7F]/g;

  return input
    .normalize("NFKC")
    .replace(controlCharPattern, " ")
    .replace(/[\n\r\t]/g, " ") // Replace newlines/tabs with spaces
    .replace(/["\\`]/g, "") // Remove quotes that could break formatting (keep apostrophes)
    .replace(/\s+/g, " ") // Collapse multiple spaces
    .trim()
    .slice(0, maxLength); // Limit length
}

/**
 * Sanitize a string with injection pattern detection.
 *
 * Applies basic sanitization and replaces known injection patterns
 * with safe placeholders. Use for high-risk inputs like user messages.
 *
 * @param input - The string to sanitize.
 * @param maxLength - Maximum allowed length (default: 1000).
 * @returns Sanitized string with injection patterns neutralized.
 *
 * @example
 * ```ts
 * const safeMessage = sanitizeWithInjectionDetection(userMessage, 5000);
 * ```
 */
export function sanitizeWithInjectionDetection(
  input: string,
  maxLength = 1000
): string {
  if (typeof input !== "string") {
    return "";
  }

  // biome-ignore lint/suspicious/noControlCharactersInRegex: intentional - removing control chars for security
  const controlCharPattern = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g;
  let sanitized = input
    .normalize("NFKC")
    .replace(controlCharPattern, "") // Remove control characters
    .replace(/\s+/g, " ") // Collapse whitespace
    .trim();

  // Apply injection pattern filtering with fresh regex instances
  for (const { pattern, replacement } of INJECTION_PATTERNS) {
    const freshPattern = new RegExp(pattern.source, pattern.flags);
    sanitized = sanitized.replace(freshPattern, replacement);
  }

  return sanitized.slice(0, maxLength);
}

/**
 * Check if a string contains potential injection patterns.
 *
 * Returns true if any known injection patterns are detected.
 * Use for logging/monitoring without blocking.
 *
 * @param input - The string to check.
 * @returns True if injection patterns detected.
 *
 * @example
 * ```ts
 * if (hasInjectionRisk(userMessage)) {
 *   logger.warn("Potential injection attempt detected");
 * }
 * ```
 */
export function hasInjectionRisk(input: string): boolean {
  if (typeof input !== "string") {
    return false;
  }

  // Create fresh regex instances to avoid global flag state issues
  return INJECTION_PATTERNS.some(({ pattern }) => {
    const freshPattern = new RegExp(pattern.source, pattern.flags);
    return freshPattern.test(input);
  });
}

export function isFilteredValue(value: string | undefined | null): boolean {
  return typeof value === "string" && value.includes(FILTERED_MARKER);
}

/**
 * Sanitize an array of strings for prompt use.
 *
 * Limits array size, sanitizes each element, and filters empty results.
 *
 * @param items - Array of strings to sanitize.
 * @param maxItems - Maximum number of items (default: 10).
 * @param maxItemLength - Maximum length per item (default: 50).
 * @param detectInjection - Whether to run injection-aware sanitization.
 * @returns Sanitized array.
 *
 * @example
 * ```ts
 * const safeAmenities = sanitizeArray(hotel.amenities, 10, 30);
 * ```
 */
export function sanitizeArray(
  items: string[],
  maxItems = 10,
  maxItemLength = 50,
  detectInjection = false
): string[] {
  if (!Array.isArray(items)) {
    return [];
  }

  return items
    .slice(0, maxItems)
    .map((item) =>
      detectInjection
        ? sanitizeWithInjectionDetection(item, maxItemLength)
        : sanitizeForPrompt(item, maxItemLength)
    )
    .filter((item) => item.length > 0);
}

/**
 * Sanitize a record/object for prompt use.
 *
 * Applies sanitization to all string values in an object.
 *
 * @param record - Object with string values to sanitize.
 * @param maxValueLength - Maximum length per value (default: 200).
 * @param detectInjection - Whether to run injection-aware sanitization.
 * @returns New object with sanitized values.
 *
 * @example
 * ```ts
 * const safePrefs = sanitizeRecord(userPreferences, 100);
 * ```
 */
export function sanitizeRecord(
  record: Record<string, string | undefined>,
  maxValueLength = 200,
  detectInjection = false
): Record<string, string> {
  const result: Record<string, string> = {};

  for (const [key, value] of Object.entries(record)) {
    if (typeof value === "string" && value.trim()) {
      result[key] = detectInjection
        ? sanitizeWithInjectionDetection(value, maxValueLength)
        : sanitizeForPrompt(value, maxValueLength);
    }
  }

  return result;
}

/**
 * Sanitize both keys and values of a record for prompt use.
 * Skips entries with empty sanitized keys. Colliding sanitized keys keep the first value.
 *
 * @param record - Object with string keys/values to sanitize.
 * @param maxKeyLength - Maximum length for each key (default: 50).
 * @param maxValueLength - Maximum length for each value (default: 200).
 */
export function sanitizeRecordKeysAndValues(
  record: Record<string, string | undefined>,
  maxKeyLength = 50,
  maxValueLength = 200
): Record<string, string> {
  const result: Record<string, string> = {};

  for (const [rawKey, rawValue] of Object.entries(record)) {
    const key = sanitizeForPrompt(rawKey, maxKeyLength);
    if (!key) continue;
    if (Object.hasOwn(result, key)) continue;
    if (typeof rawValue === "string" && rawValue.trim()) {
      result[key] = sanitizeForPrompt(rawValue, maxValueLength);
    }
  }

  return result;
}
