/**
 * Semantic-release configuration for TripSage.
 *
 * Temporary rule: breaking changes are treated as minor until we ship
 * the next stable major. Remove the breaking->minor rule when ready to
 * allow true major bumps.
 */
export default {
  branches: ["main"],
  plugins: [
    [
      "@semantic-release/commit-analyzer",
      {
        preset: "conventionalcommits",
        releaseRules: [
          { breaking: true, release: "minor" },
          { release: "minor", type: "feat" },
          { release: "patch", type: "fix" },
          { release: false, type: "chore" },
        ],
      },
    ],
    ["@semantic-release/release-notes-generator", { preset: "conventionalcommits" }],
    ["@semantic-release/changelog", { changelogFile: "CHANGELOG.md" }],
    ["@semantic-release/npm", { npmPublish: false }],
    [
      "@semantic-release/git",
      {
        assets: ["CHANGELOG.md", "package.json"],
        // biome-ignore lint/suspicious/noTemplateCurlyInString: semantic-release interpolates this placeholder.
        message: "chore(release): ${nextRelease.version} [skip ci]",
      },
    ],
    [
      "@semantic-release/github",
      {
        successCommentCondition: false,
      },
    ],
  ],
  repositoryUrl: "https://github.com/BjornMelin/tripsage-ai.git",
};
