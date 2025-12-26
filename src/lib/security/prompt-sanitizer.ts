/**
 * @fileoverview Shared AI prompt sanitization utilities.
 *
 * SECURITY: This module defends against prompt injection attacks including:
 * - Unicode homoglyphs (Cyrillic "А" looks like Latin "A")
 * - Zero-width characters (invisible characters that break regex)
 * - Common injection patterns (SYSTEM:, ignore instructions, etc.)
 */

/**
 * Common prompt injection patterns to detect.
 * These patterns are commonly used to hijack LLM behavior.
 */
export const FILTERED_MARKER = "[FILTERED]";

/**
 * Zero-width and invisible characters that can be used to bypass injection filters.
 * These must be stripped before applying regex patterns.
 *
 * Uses alternation instead of character class to avoid combining character issues.
 */
const ZERO_WIDTH_CHARS =
  /\u200B|\u200C|\u200D|\u2060|\u2061|\u2062|\u2063|\u2064|\uFEFF|\u00AD|\u180E|\u034F/g;

/**
 * Common Unicode homoglyphs that look like ASCII letters.
 * Maps confusable characters to their ASCII equivalents.
 *
 * Note: This covers the most common attack vectors (Cyrillic, Greek).
 * NFKC normalization handles many others (fullwidth, superscript, etc.)
 *
 * Uses Map to avoid Biome naming convention lint errors while allowing
 * non-ASCII character keys for security purposes.
 */
const HOMOGLYPH_MAP = new Map<string, string>([
  // Greek lookalikes
  ["Α", "A"],
  ["Β", "B"],
  ["Ε", "E"],
  ["Ζ", "Z"],
  ["Η", "H"],
  ["Ι", "I"],
  ["Κ", "K"],
  ["Μ", "M"],
  ["Ν", "N"],
  ["Ο", "O"],
  ["Ρ", "P"],
  ["Τ", "T"],
  ["Υ", "Y"],
  ["Χ", "X"],
  ["ο", "o"],
  ["Ѕ", "S"],
  ["І", "I"],
  ["Ј", "J"],
  // Cyrillic lookalikes (most common in attacks)
  ["А", "A"],
  ["В", "B"],
  ["Е", "E"],
  ["К", "K"],
  ["М", "M"],
  ["Н", "H"],
  ["О", "O"],
  ["Р", "P"],
  ["С", "C"],
  ["Т", "T"],
  ["Х", "X"],
  ["а", "a"],
  ["е", "e"],
  ["о", "o"],
  ["р", "p"],
  ["с", "c"],
  ["у", "y"],
  ["х", "x"],
  ["ѕ", "s"],
  ["і", "i"],
  ["ј", "j"],
  ["Ү", "Y"],
  ["ℐ", "I"],
  ["ℑ", "I"],
  ["ℒ", "L"],
  // Latin Extended lookalikes
  ["ℓ", "l"],
  ["ℛ", "R"],
  ["ℨ", "Z"],
  ["ℳ", "M"],
]);

/**
 * Normalize a string by replacing homoglyphs and stripping zero-width chars.
 * This prevents bypassing injection filters with lookalike characters.
 */
function normalizeUnicodeForSecurity(input: string): string {
  // First apply NFKC normalization (handles fullwidth, superscripts, etc.)
  let result = input.normalize("NFKC");

  // Strip zero-width and invisible characters
  result = result.replace(ZERO_WIDTH_CHARS, "");

  // Replace known homoglyphs with ASCII equivalents
  result = result
    .split("")
    .map((char) => HOMOGLYPH_MAP.get(char) ?? char)
    .join("");

  return result;
}

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
 * Applies basic sanitization, Unicode normalization (including homoglyph
 * replacement), and replaces known injection patterns with safe placeholders.
 * Use for high-risk inputs like user messages.
 *
 * SECURITY: This function defends against:
 * - Cyrillic/Greek homoglyphs ("IMPORTАNT" with Cyrillic А)
 * - Zero-width character insertion ("IMP\u200BORTANT")
 * - Common injection patterns (SYSTEM:, ignore instructions, etc.)
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

  // SECURITY: Apply homoglyph normalization BEFORE pattern matching
  // This prevents bypasses like "IMPORTАNT:" with Cyrillic А
  let sanitized = normalizeUnicodeForSecurity(input)
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
 * SECURITY: Applies homoglyph normalization before checking patterns
 * to detect bypasses like "IMPORTАNT:" with Cyrillic А.
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

  // SECURITY: Normalize before checking to catch homoglyph bypasses
  const normalized = normalizeUnicodeForSecurity(input);

  // Create fresh regex instances to avoid global flag state issues
  return INJECTION_PATTERNS.some(({ pattern }) => {
    const freshPattern = new RegExp(pattern.source, pattern.flags);
    return freshPattern.test(normalized);
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
