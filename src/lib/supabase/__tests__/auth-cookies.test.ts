import { describe, expect, it } from "vitest";
import {
  hasSupabaseAuthCookies,
  hasSupabaseAuthCookiesFromHeader,
  isSupabaseSsrAuthCookieName,
} from "../auth-cookies";

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

describe("isSupabaseSsrAuthCookieName", () => {
  it("returns true for chunked auth token names", () => {
    expect(isSupabaseSsrAuthCookieName("sb-proj-auth-token.0")).toBe(true);
    expect(isSupabaseSsrAuthCookieName("sb-proj-auth-token.1")).toBe(true);
  });

  it("returns true for base auth token names", () => {
    expect(isSupabaseSsrAuthCookieName("sb-proj-auth-token")).toBe(true);
  });

  it("returns false for non sb- prefixes", () => {
    expect(isSupabaseSsrAuthCookieName("proj-auth-token")).toBe(false);
    expect(isSupabaseSsrAuthCookieName("supabase-auth-token")).toBe(false);
  });

  it("returns false for similar but non-matching names", () => {
    expect(isSupabaseSsrAuthCookieName("sb-proj-auth-tokenx")).toBe(false);
    expect(isSupabaseSsrAuthCookieName("sb-proj-auth-token.")).toBe(false);
    expect(isSupabaseSsrAuthCookieName("sb-proj-auth-token.a")).toBe(false);
  });
});

describe("hasSupabaseAuthCookies", () => {
  it("returns true when array includes legacy auth cookies", () => {
    const cookies = [
      { name: "other", value: "value" },
      { name: "sb-access-token", value: "token" },
    ];
    expect(hasSupabaseAuthCookies(cookies)).toBe(true);
  });

  it("returns true when array includes SSR auth cookies", () => {
    const cookies = [
      { name: "sb-proj-auth-token.0", value: "chunk0" },
      { name: "sb-proj-auth-token.1", value: "chunk1" },
    ];
    expect(hasSupabaseAuthCookies(cookies)).toBe(true);
  });

  it("returns false when cookies are empty or whitespace", () => {
    const cookies = [
      { name: "sb-access-token", value: "" },
      { name: "sb-refresh-token", value: "   " },
      { name: "sb-proj-auth-token", value: " " },
    ];
    expect(hasSupabaseAuthCookies(cookies)).toBe(false);
  });

  it("returns false when no auth cookies are present", () => {
    const cookies = [
      { name: "foo", value: "bar" },
      { name: "session", value: "abc" },
    ];
    expect(hasSupabaseAuthCookies(cookies)).toBe(false);
  });
});
