---
name: Organization-Wide Policies
description: Default community health files inherited by all jonathanperis repos, security reporting process, contribution workflow
type: reference
---

## Files Inherited by All Repos

These apply to any jonathanperis repo that doesn't define its own:
- **CODE_OF_CONDUCT.md** — Contributor Covenant v2.1
- **CONTRIBUTING.md** — Fork → branch → commit → test → PR workflow
- **SECURITY.md** — Private vulnerability reporting (48-hour acknowledgment)
- **SUPPORT.md** — Directs to issue templates and GitHub Discussions
- **LICENSE** — MIT License (2026 Jonathan Peris)
- **PR template** — Summary, Changes, Test Plan sections
- **Issue templates** — Bug report (YAML, auto-labeled "bug") and Feature request (YAML, auto-labeled "enhancement")
- **FUNDING.yml** — GitHub Sponsors + Buy Me A Coffee

## Security Policy

Vulnerabilities must be reported via GitHub's private vulnerability reporting — NOT public issues. Response timeline: 48-hour acknowledgment.

## Contribution Workflow

Standard fork-based: Fork → create branch → commit → run tests → open PR. Style conventions specified in CONTRIBUTING.md.

**How to apply:** When creating new repos, these files are automatically inherited. Only create repo-specific versions if the project needs different policies.
