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
          { type: "feat", release: "minor" },
          { type: "fix", release: "patch" },
          { type: "chore", release: false }
        ]
      }
    ],
    ["@semantic-release/release-notes-generator", { preset: "conventionalcommits" }],
    ["@semantic-release/changelog", { changelogFile: "CHANGELOG.md" }],
    ["@semantic-release/npm", { npmPublish: false }],
    [
      "@semantic-release/git",
      {
        assets: ["CHANGELOG.md", "package.json"],
        message: "chore(release): ${nextRelease.version} [skip ci]"
      }
    ],
    "@semantic-release/github"
  ]
};
