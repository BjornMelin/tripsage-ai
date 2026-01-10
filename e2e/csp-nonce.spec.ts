import { expect, test } from "@playwright/test";

function getCspDirectiveValue(cspHeader: string, directive: string): string | null {
  const parts = cspHeader
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);

  for (const part of parts) {
    if (part === directive) return "";
    if (part.startsWith(`${directive} `)) return part.slice(directive.length + 1);
  }

  return null;
}

function extractNonceFromCsp(cspHeader: string): string {
  const match = /'nonce-([^']+)'/.exec(cspHeader);
  if (!match?.[1]) {
    throw new Error(`Expected nonce in CSP header, got: ${cspHeader}`);
  }
  return match[1];
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

test("CSP nonce is present and applied to scripts", async ({ page }) => {
  const consoleMessages: string[] = [];

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleMessages.push(message.text());
    }
  });

  const response = await page.goto("/", { waitUntil: "domcontentloaded" });
  expect(response).not.toBeNull();
  if (!response) {
    throw new Error("Expected initial navigation response");
  }

  const cspHeader = response.headers()["content-security-policy"];
  expect(cspHeader).toBeTruthy();
  if (!cspHeader) {
    throw new Error("Expected Content-Security-Policy response header");
  }

  const scriptSrc = getCspDirectiveValue(cspHeader, "script-src") ?? "";
  const requiresNonce =
    scriptSrc.includes("'strict-dynamic'") || !scriptSrc.includes("'unsafe-inline'");

  if (requiresNonce) {
    const nonce = extractNonceFromCsp(cspHeader);

    // Nonces can be hidden/stripped from DOM APIs in some browsers; assert against raw HTML.
    const html = await response.text();
    expect(html).toMatch(new RegExp(`nonce=("|')${escapeRegExp(nonce)}\\1`));
  } else {
    // Development/HMR commonly relies on inline scripts. In this mode we relax CSP,
    // so scripts may not be explicitly nonced.
    expect(scriptSrc).toContain("'unsafe-inline'");
  }

  // Guard against runtime breakage: if CSP blocks scripts, browsers emit console errors.
  const cspViolations = consoleMessages.filter((text) =>
    /content security policy|violates the following content security policy|refused to (load|execute)/i.test(
      text
    )
  );
  expect(cspViolations).toEqual([]);
});
