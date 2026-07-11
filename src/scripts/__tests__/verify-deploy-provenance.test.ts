/** @vitest-environment node */

import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";

let verifyDeployProvenance: typeof import("../../../scripts/verify-deploy-provenance.mjs").verifyDeployProvenance;

const candidateSha = "a".repeat(40);
const staleSha = "b".repeat(40);

beforeAll(async () => {
  ({ verifyDeployProvenance } = await import(
    "../../../scripts/verify-deploy-provenance.mjs"
  ));
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

function createGithubFetch({
  defaultHeadSha = candidateSha,
  workflowRuns = [
    {
      conclusion: "success",
      event: "push",
      head_branch: "main",
      head_sha: candidateSha,
      id: 12345,
      status: "completed",
    },
  ],
}: {
  defaultHeadSha?: string;
  workflowRuns?: unknown[];
} = {}) {
  const requests: string[] = [];
  const requestSignals: Array<AbortSignal | null | undefined> = [];
  const fetchImpl: typeof fetch = (input, init) => {
    const url = String(input);
    requests.push(url);
    requestSignals.push(init?.signal);
    if (url.endsWith("/repos/BjornMelin/tripsage-ai")) {
      return Promise.resolve(jsonResponse({ default_branch: "main" }));
    }
    if (url.endsWith("/repos/BjornMelin/tripsage-ai/branches/main")) {
      return Promise.resolve(jsonResponse({ commit: { sha: defaultHeadSha } }));
    }
    if (url.includes("/actions/workflows/ci.yml/runs?")) {
      return Promise.resolve(jsonResponse({ workflow_runs: workflowRuns }));
    }
    return Promise.resolve(jsonResponse({ message: "Not found" }, 404));
  };
  return { fetchImpl, requestSignals, requests };
}

function productionInput(fetchImpl: typeof fetch) {
  return {
    apiUrl: "https://api.github.com",
    environment: "production",
    eventName: "workflow_dispatch",
    fetchImpl,
    ref: "refs/heads/main",
    repository: "BjornMelin/tripsage-ai",
    sha: candidateSha,
    token: "test-token",
  };
}

describe("verify-deploy-provenance", () => {
  it.each([
    "development",
    "staging",
  ])("skips GitHub reads for %s deployments", async (environment) => {
    const { fetchImpl, requests } = createGithubFetch();

    const result = await verifyDeployProvenance({
      ...productionInput(fetchImpl),
      environment,
    });

    expect(result).toMatchObject({ environment, status: "skipped" });
    expect(requests).toEqual([]);
  });

  it("requires the production workflow ref to be main", async () => {
    const { fetchImpl, requests } = createGithubFetch();

    await expect(
      verifyDeployProvenance({
        ...productionInput(fetchImpl),
        ref: "refs/heads/feature/unsafe",
      })
    ).rejects.toMatchObject({ code: "invalid_ref" });
    expect(requests).toEqual([]);
  });

  it("does not bypass production ref checks for workflow_call", async () => {
    const { fetchImpl } = createGithubFetch();

    await expect(
      verifyDeployProvenance({
        ...productionInput(fetchImpl),
        eventName: "workflow_call",
        ref: "refs/heads/feature/caller",
      })
    ).rejects.toMatchObject({ code: "invalid_ref" });
  });

  it("rejects a candidate that is not the live default-branch head", async () => {
    const { fetchImpl, requests } = createGithubFetch({
      defaultHeadSha: staleSha,
    });

    await expect(
      verifyDeployProvenance(productionInput(fetchImpl))
    ).rejects.toMatchObject({ code: "stale_candidate" });
    expect(requests).toHaveLength(2);
  });

  it("rejects an exact head without a completed successful CI run", async () => {
    const { fetchImpl } = createGithubFetch({
      workflowRuns: [
        {
          conclusion: "failure",
          event: "push",
          head_branch: "main",
          head_sha: candidateSha,
          id: 12345,
          status: "completed",
        },
      ],
    });

    await expect(
      verifyDeployProvenance(productionInput(fetchImpl))
    ).rejects.toMatchObject({ code: "ci_not_successful" });
  });

  it.each([
    {
      conclusion: "success",
      event: "push",
      head_branch: "main",
      head_sha: staleSha,
      id: 12345,
      status: "completed",
    },
    {
      conclusion: null,
      event: "push",
      head_branch: "main",
      head_sha: candidateSha,
      id: 12345,
      status: "in_progress",
    },
  ])("rejects a CI run that is not successful for the exact SHA", async (run) => {
    const { fetchImpl } = createGithubFetch({ workflowRuns: [run] });

    await expect(
      verifyDeployProvenance(productionInput(fetchImpl))
    ).rejects.toMatchObject({ code: "ci_not_successful" });
  });

  it.each([
    { event: "pull_request", head_branch: "main" },
    { event: "push", head_branch: "feature/unverified" },
  ])("rejects a successful run outside a main-branch push", async (identity) => {
    const { fetchImpl } = createGithubFetch({
      workflowRuns: [
        {
          conclusion: "success",
          head_sha: candidateSha,
          id: 12345,
          status: "completed",
          ...identity,
        },
      ],
    });

    await expect(
      verifyDeployProvenance(productionInput(fetchImpl))
    ).rejects.toMatchObject({ code: "ci_not_successful" });
  });

  it("accepts the live main head with a completed successful CI run", async () => {
    const { fetchImpl, requestSignals, requests } = createGithubFetch();

    const result = await verifyDeployProvenance(productionInput(fetchImpl));

    expect(result).toMatchObject({
      ciRunId: 12345,
      defaultBranch: "main",
      sha: candidateSha,
      status: "passed",
      workflow: "ci.yml",
    });
    expect(requests).toHaveLength(3);
    expect(requests[2]).toContain("branch=main&event=push");
    expect(requestSignals).toHaveLength(3);
    expect(requestSignals.every((signal) => signal instanceof AbortSignal)).toBe(true);
  });

  it("wires provenance before secrets and immediately before production promotion", () => {
    const workflow = readFileSync(
      path.join(process.cwd(), ".github/workflows/deploy.yml"),
      "utf8"
    );
    const initialProvenanceStep = workflow.indexOf(
      "- name: Verify production deployment provenance"
    );
    const secretStep = workflow.indexOf("- name: Validate required GitHub secrets");
    const byokStep = workflow.indexOf("- name: Run BYOK health smoke check");
    const finalProvenanceMarker = "- name: Reverify production deployment provenance";
    const finalProvenanceStep = workflow.indexOf(finalProvenanceMarker);
    const promoteStep = workflow.indexOf("- name: Promote production deployment");
    const stepsBetweenRecheckAndPromotion = workflow
      .slice(finalProvenanceStep + finalProvenanceMarker.length, promoteStep)
      .match(/^ {6}-\s+\S/gm);

    expect(workflow).toMatch(/permissions:\n(?:\s+#.*\n)*\s+actions: read\n/);
    expect(workflow).toMatch(/CANDIDATE_SHA: \$\{\{ github\.sha \}\}/);
    expect(workflow.match(/node scripts\/verify-deploy-provenance\.mjs/g)).toHaveLength(
      2
    );
    expect(initialProvenanceStep).toBeGreaterThan(-1);
    expect(initialProvenanceStep).toBeLessThan(secretStep);
    expect(finalProvenanceStep).toBeGreaterThan(byokStep);
    expect(finalProvenanceStep).toBeLessThan(promoteStep);
    expect(workflow.slice(finalProvenanceStep, promoteStep)).toContain(
      "if: steps.vercel_env.outputs.promote_after_smoke == 'true'"
    );
    expect(stepsBetweenRecheckAndPromotion).toBeNull();
  });
});
