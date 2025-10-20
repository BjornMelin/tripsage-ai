# Deployments

This repository retains a manual deployment workflow (`.github/workflows/deploy.yml`).

- Trigger via `workflow_dispatch` and select the environment (development, staging, production).
- The workflow posts a deployment status in GitHub and links the environment URL.

CI and deployments are decoupled: the `CI` workflow focuses on fast feedback for PRs and pushes; deployments occur on demand.

