# Renovate setup for jonathanperis/* repos

This `.github` repo hosts the **shared Renovate preset** at `default.json`. Every other repo extends it with a tiny `renovate.json`.

## To roll out to a new repo

1. Add `renovate.json` at the repo root:

   ```json
   {
     "$schema": "https://docs.renovatebot.com/renovate-schema.json",
     "extends": ["github>jonathanperis/.github"]
   }
   ```

2. (Optional) Override anything per-repo by adding extra fields to that file.

3. Install the [Renovate GitHub App](https://github.com/apps/renovate) once and grant it access to your repos.

## What the preset does

- **Semantic-commit messages** (`chore(deps): bump foo to 1.2.3`)
- **Dependency Dashboard** issue per repo (single source of truth)
- **Weekly schedule** with `lockFileMaintenance` Monday before 5am
- **Auto-merge** for ordinary patch, minor, and digest updates after required CI passes
- **Manual review** for major bumps, GitHub Actions updates, and vulnerability-alert PRs
- **Three-day release age** for routine updates; security-alert PRs are raised immediately
- **Full commit pins** for GitHub Actions, maintained by Renovate
- **Group rules**:
  - `github-actions` — pinned action updates grouped into a reviewable PR
  - `dotnet-msft-otel` — Microsoft.* + OpenTelemetry.* + Azure.*
  - `dotnet-testing` — xunit, Moq, FluentAssertions, coverlet, Test.Sdk
  - `lynx` — all `@lynx-js/*` packages
  - `astro-tailwind` — Astro + Tailwind ecosystem
- **Native Bun lockfile support** and weekly lockfile maintenance; no unsupported `bunInstall` post-update option

## Migrating off Dependabot

Once Renovate's Dependency Dashboard is running cleanly:

1. Delete `.github/dependabot.yml` (or rename to `.dependabot.yml.disabled` for reference)
2. Disable Dependabot version updates in repo Settings → Code security → Dependabot version updates
3. Keep **Dependabot security updates** enabled — Renovate's `vulnerabilityAlerts` covers this too but having both doesn't hurt
