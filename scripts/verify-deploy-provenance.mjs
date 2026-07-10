/**
 * @fileoverview Fail-closed production deployment provenance verification.
 * Usage: node scripts/verify-deploy-provenance.mjs
 */

import path from "node:path";
import { fileURLToPath } from "node:url";

const FILENAME = fileURLToPath(import.meta.url);
const EXPECTED_PRODUCTION_REF = "refs/heads/main";
const CI_WORKFLOW_ID = "ci.yml";
const SHA_PATTERN = /^[0-9a-f]{40}$/i;

const isMainModule = (() => {
  const entry = process.argv[1];
  return Boolean(entry) && path.resolve(entry) === FILENAME;
})();

class DeployProvenanceError extends Error {
  /**
   * @param {string} code Stable public-safe error code.
   * @param {string} message Public-safe error description.
   * @param {Record<string, unknown>} [evidence] Public-safe diagnostic evidence.
   */
  constructor(code, message, evidence = {}) {
    super(message);
    this.name = "DeployProvenanceError";
    this.code = code;
    this.evidence = evidence;
  }
}

/**
 * @param {string} repository GitHub owner/name identifier.
 * @returns {{ owner: string; repo: string }} Parsed repository identity.
 */
function parseRepository(repository) {
  const [owner, repo, ...rest] = repository.split("/");
  const safePart = /^[A-Za-z0-9_.-]+$/;
  if (
    rest.length > 0 ||
    !owner ||
    !repo ||
    !safePart.test(owner) ||
    !safePart.test(repo)
  ) {
    throw new DeployProvenanceError(
      "invalid_repository",
      "GITHUB_REPOSITORY must contain a valid owner and repository name."
    );
  }
  return { owner, repo };
}

/**
 * @param {string} apiUrl GitHub API base URL.
 * @param {string} route API route beginning with a slash.
 * @returns {URL} Validated GitHub API URL.
 */
function resolveApiUrl(apiUrl, route) {
  let base;
  try {
    base = new URL(apiUrl);
  } catch {
    throw new DeployProvenanceError(
      "invalid_api_url",
      "GITHUB_API_URL must be a valid HTTPS URL."
    );
  }
  if (base.protocol !== "https:") {
    throw new DeployProvenanceError(
      "invalid_api_url",
      "GITHUB_API_URL must be a valid HTTPS URL."
    );
  }
  return new URL(`${base.href.replace(/\/$/, "")}${route}`);
}

/**
 * @param {{
 *   apiUrl: string;
 *   fetchImpl: typeof fetch;
 *   route: string;
 *   token: string;
 * }} options GitHub request options.
 * @returns {Promise<unknown>} Parsed response body.
 */
async function fetchGithubJson({ apiUrl, fetchImpl, route, token }) {
  const headers = new Headers();
  headers.set("Accept", "application/vnd.github+json");
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("X-GitHub-Api-Version", "2022-11-28");
  const response = await fetchImpl(resolveApiUrl(apiUrl, route), {
    headers,
  });
  if (!response.ok) {
    throw new DeployProvenanceError(
      "github_api_failed",
      `GitHub provenance API request failed with status ${response.status}.`,
      { status: response.status }
    );
  }
  try {
    return await response.json();
  } catch {
    throw new DeployProvenanceError(
      "github_api_invalid_response",
      "GitHub provenance API returned invalid JSON."
    );
  }
}

/**
 * @typedef {Object} VerifyDeployProvenanceOptions
 * @property {string} apiUrl GitHub API base URL.
 * @property {string} environment Requested deployment environment.
 * @property {string} eventName GitHub event name.
 * @property {typeof fetch} [fetchImpl] Fetch implementation for deterministic tests.
 * @property {string} ref GitHub workflow ref.
 * @property {string} repository GitHub owner/name identifier.
 * @property {string} sha GitHub workflow SHA.
 * @property {string} token GitHub Actions token.
 */

/**
 * Verify that a production candidate is the live default-branch head with a
 * completed successful CI run. Non-production environments intentionally skip.
 *
 * @param {VerifyDeployProvenanceOptions} options Verification inputs.
 * @returns {Promise<Record<string, unknown>>} Public-safe verification summary.
 */
async function verifyDeployProvenance({
  apiUrl,
  environment,
  eventName,
  fetchImpl = fetch,
  ref,
  repository,
  sha,
  token,
}) {
  if (environment !== "production") {
    return { environment, event: eventName, status: "skipped" };
  }
  if (ref !== EXPECTED_PRODUCTION_REF) {
    throw new DeployProvenanceError(
      "invalid_ref",
      "Production deployments must run from refs/heads/main.",
      { actualRef: ref, expectedRef: EXPECTED_PRODUCTION_REF }
    );
  }
  if (!SHA_PATTERN.test(sha)) {
    throw new DeployProvenanceError(
      "invalid_sha",
      "Production candidate must be a full Git commit SHA."
    );
  }
  if (!token) {
    throw new DeployProvenanceError(
      "missing_github_token",
      "GitHub Actions token is unavailable for production provenance checks."
    );
  }

  const { owner, repo } = parseRepository(repository);
  const encodedOwner = encodeURIComponent(owner);
  const encodedRepo = encodeURIComponent(repo);
  const request = (route) => fetchGithubJson({ apiUrl, fetchImpl, route, token });

  const repositoryData = await request(`/repos/${encodedOwner}/${encodedRepo}`);
  const defaultBranch =
    repositoryData &&
    typeof repositoryData === "object" &&
    "default_branch" in repositoryData &&
    typeof repositoryData.default_branch === "string"
      ? repositoryData.default_branch
      : "";
  if (!defaultBranch) {
    throw new DeployProvenanceError(
      "missing_default_branch",
      "GitHub did not return a default branch for the repository."
    );
  }

  const branchData = await request(
    `/repos/${encodedOwner}/${encodedRepo}/branches/${encodeURIComponent(defaultBranch)}`
  );
  const defaultHeadSha =
    branchData &&
    typeof branchData === "object" &&
    "commit" in branchData &&
    branchData.commit &&
    typeof branchData.commit === "object" &&
    "sha" in branchData.commit &&
    typeof branchData.commit.sha === "string"
      ? branchData.commit.sha
      : "";
  if (!SHA_PATTERN.test(defaultHeadSha)) {
    throw new DeployProvenanceError(
      "missing_default_head",
      "GitHub did not return a valid default-branch head SHA."
    );
  }
  if (sha !== defaultHeadSha) {
    throw new DeployProvenanceError(
      "stale_candidate",
      "Production candidate SHA is not the live default-branch head.",
      { candidateSha: sha, defaultBranch, defaultHeadSha }
    );
  }

  const runsRoute =
    `/repos/${encodedOwner}/${encodedRepo}/actions/workflows/${CI_WORKFLOW_ID}/runs` +
    `?head_sha=${encodeURIComponent(sha)}&status=completed&per_page=100`;
  const runsData = await request(runsRoute);
  const workflowRuns =
    runsData &&
    typeof runsData === "object" &&
    "workflow_runs" in runsData &&
    Array.isArray(runsData.workflow_runs)
      ? runsData.workflow_runs
      : [];
  const successfulRun = workflowRuns.find(
    (run) =>
      run &&
      typeof run === "object" &&
      "head_sha" in run &&
      run.head_sha === sha &&
      "status" in run &&
      run.status === "completed" &&
      "conclusion" in run &&
      run.conclusion === "success"
  );
  if (!successfulRun) {
    throw new DeployProvenanceError(
      "ci_not_successful",
      "Production candidate has no completed successful CI workflow run.",
      {
        candidateSha: sha,
        completedRuns: workflowRuns.length,
        workflow: CI_WORKFLOW_ID,
      }
    );
  }

  return {
    ciRunId:
      "id" in successfulRun &&
      (typeof successfulRun.id === "number" || typeof successfulRun.id === "string")
        ? successfulRun.id
        : null,
    defaultBranch,
    environment,
    event: eventName,
    ref,
    sha,
    status: "passed",
    workflow: CI_WORKFLOW_ID,
  };
}

async function main() {
  try {
    const result = await verifyDeployProvenance({
      apiUrl: process.env.GITHUB_API_URL ?? "https://api.github.com",
      environment: process.env.DEPLOY_ENVIRONMENT ?? "",
      eventName: process.env.GITHUB_EVENT_NAME ?? "unknown",
      ref: process.env.GITHUB_REF ?? "",
      repository: process.env.GITHUB_REPOSITORY ?? "",
      sha: process.env.CANDIDATE_SHA ?? "",
      token: process.env.GITHUB_TOKEN ?? "",
    });
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    const failure =
      error instanceof DeployProvenanceError
        ? {
            code: error.code,
            evidence: error.evidence,
            message: error.message,
            status: "failed",
          }
        : {
            code: "unexpected_error",
            message: "Production deployment provenance verification failed.",
            status: "failed",
          };
    console.error(JSON.stringify(failure, null, 2));
    process.exitCode = 1;
  }
}

if (isMainModule) {
  await main();
}

export { verifyDeployProvenance };
