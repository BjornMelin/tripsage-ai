import { describe, expect, it } from "vitest";
import { hasSupabaseAuthCookiesFromHeader } from "../auth-cookies";

describe("hasSupabaseAuthCookiesFromHeader", () => {
  it("should return true when sb-access-token is present", () => {
    const cookie = "sb-access-token=some-token";
    expect(hasSupabaseAuthCookiesFromHeader(cookie)).toBe(true);
  });

  it("should return true when sb-refresh-token is present", () => {
    const cookie = "sb-refresh-token=some-token";
    expect(hasSupabaseAuthCookiesFromHeader(cookie)).toBe(true);
  });

  it("should return true when sb-something-auth-token is present", () => {
    const cookie = "sb-project-auth-token=some-token";
    expect(hasSupabaseAuthCookiesFromHeader(cookie)).toBe(true);
  });

  it("should return false when no supabase cookies are present", () => {
    const cookie = "other-cookie=some-value; another=one";
    expect(hasSupabaseAuthCookiesFromHeader(cookie)).toBe(false);
  });

  it("should return false for empty or null header", () => {
    expect(hasSupabaseAuthCookiesFromHeader(null)).toBe(false);
    expect(hasSupabaseAuthCookiesFromHeader("")).toBe(false);
    expect(hasSupabaseAuthCookiesFromHeader("  ")).toBe(false);
  });

  it("should handle cookie values containing '='", () => {
    // This is what the fix specifically addresses
    const cookie = "sb-access-token=token=with=equals; other=value";
    expect(hasSupabaseAuthCookiesFromHeader(cookie)).toBe(true);
  });

  it("should handle multiple cookies in the header", () => {
    const cookie = "foo=bar; sb-access-token=xyz; baz=qux";
    expect(hasSupabaseAuthCookiesFromHeader(cookie)).toBe(true);
  });

  it("should return false if cookie value is empty or just whitespace", () => {
    const cookie = "sb-access-token=; other=value";
    expect(hasSupabaseAuthCookiesFromHeader(cookie)).toBe(false);

    const cookieWhitespace = "sb-access-token=  ; other=value";
    expect(hasSupabaseAuthCookiesFromHeader(cookieWhitespace)).toBe(false);
  });
});
