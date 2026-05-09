import { createHash } from "node:crypto";
import type { Page } from "@playwright/test";
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

function sha256Base64(value: string): string {
  return createHash("sha256").update(value, "utf8").digest("base64");
}

async function extractInlineScriptHashes(page: Page): Promise<string[]> {
  const inlineScriptContents = await page
    .locator("script:not([src]):not([nonce])")
    .evaluateAll((scripts) =>
      scripts
        .map((script) => script.textContent ?? "")
        .filter((content) => content.trim().length > 0)
    );

  return Array.from(
    new Set(inlineScriptContents.map((content) => `'sha256-${sha256Base64(content)}'`))
  );
}

test("CSP allows production scripts via nonce, hashes, or public inline compatibility", async ({
  page,
}) => {
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
  const hasNonce = scriptSrc.includes("'nonce-");
  const requiresNonce =
    scriptSrc.includes("'strict-dynamic'") || !scriptSrc.includes("'unsafe-inline'");

  if (requiresNonce && hasNonce) {
    const nonce = extractNonceFromCsp(cspHeader);

    // Nonces can be hidden/stripped from DOM APIs in some browsers; assert against raw HTML.
    const html = await response.text();
    expect(html).toMatch(new RegExp(`nonce=("|')${escapeRegExp(nonce)}\\1`));
  } else if (requiresNonce) {
    const inlineScriptHashes = await extractInlineScriptHashes(page);

    expect(inlineScriptHashes.length).toBeGreaterThan(0);
    for (const hash of inlineScriptHashes) {
      expect(scriptSrc).toContain(hash);
    }
  } else {
    // Public static routes cannot receive per-request nonces. In this mode we relax
    // script CSP for framework inline payload compatibility.
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
