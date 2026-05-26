/** @vitest-environment node */

import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";

const scriptPath = join(process.cwd(), "scripts/check-doc-links.mjs");

function writeFiles(root: string, files: Record<string, string>) {
  for (const [filePath, contents] of Object.entries(files)) {
    const absolutePath = join(root, filePath);
    mkdirSync(dirname(absolutePath), { recursive: true });
    writeFileSync(absolutePath, contents);
  }
}

function runDocsCheck(files: Record<string, string>, targets: string[] = []) {
  const tempDir = mkdtempSync(join(tmpdir(), "tripsage-doc-links-"));

  try {
    writeFiles(tempDir, files);
    return spawnSync(process.execPath, [scriptPath, ...targets], {
      cwd: tempDir,
      encoding: "utf8",
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

describe("check-doc-links", () => {
  it("accepts valid relative links, anchors, reference links, and directory indexes", () => {
    const result = runDocsCheck({
      "docs/guide.md": `# Quick Start

## Explicit Section {#explicit-id}
`,
      "docs/runbook/README.md": "# Operations\n",
      "README.md": `# TripSage

See [Guide](docs/guide.md#quick-start), [Directory](docs/runbook/),
[Extensionless](docs/guide#explicit-id), and [Reference][runbook].

[runbook]: docs/runbook/README.md#operations
`,
    });

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("Checked 3 active Markdown file(s)");
  });

  it("reports missing relative link targets", () => {
    const result = runDocsCheck({
      "README.md": `# TripSage

See [Missing](docs/missing.md).
`,
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("Found 1 broken active doc link");
    expect(result.stderr).toContain("README.md: missing docs/missing.md");
  });

  it("reports missing heading anchors after normalizing generated markdown anchors", () => {
    const result = runDocsCheck({
      "docs/guide.md": "# Quick `Start`!\n",
      "README.md": `# TripSage

See [Wrong Anchor](docs/guide.md#missing-anchor).
`,
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "README.md: missing anchor docs/guide.md#missing-anchor"
    );
  });

  it("ignores links in code fences and skippable external schemes", () => {
    const result = runDocsCheck({
      "README.md": `# TripSage

[External](https://example.com)
[Mail](mailto:hello@example.com)
[App](app://local)

\`\`\`md
[Ignored](docs/missing.md)
\`\`\`
`,
    });

    expect(result.status).toBe(0);
  });

  it("excludes archive and review documentation from active link checks", () => {
    const result = runDocsCheck({
      "docs/plans/archive/old-plan.md": `# Archived Plan

[Historical broken link](../missing.md)
`,
      "docs/reviews/2026-01-01/report.md": `# Review

[Historical broken link](../missing.md)
`,
      "README.md": "# TripSage\n",
    });

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("Checked 1 active Markdown file");
  });

  it("checks explicit target arguments instead of the default README and docs set", () => {
    const result = runDocsCheck(
      {
        "notes/custom.md": `# Custom

[Self](#custom)
`,
        "README.md": `# TripSage

[Broken](docs/missing.md)
`,
      },
      ["notes"]
    );

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("Checked 1 active Markdown file");
  });
});
