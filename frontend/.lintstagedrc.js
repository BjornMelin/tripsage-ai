module.exports = {
  // Lint JavaScript and TypeScript files
  "**/*.{js,jsx,ts,tsx}": [
    "eslint --fix",
    "prettier --write",
  ],
  // Format other file types
  "**/*.{css,json,md}": [
    "prettier --write",
  ],
}