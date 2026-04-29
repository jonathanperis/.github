# CodeRabbit setup for jonathanperis/* repos

[CodeRabbit](https://www.coderabbit.ai/) is an AI code-review assistant. It posts inline comments on PRs, summarizes diffs, and catches common bugs/anti-patterns. **Free for open-source.**

## One-time setup

1. Install the [CodeRabbit GitHub App](https://github.com/apps/coderabbitai) and grant access to all jonathanperis/* public repos.
2. (Optional) Add per-repo overrides via `.coderabbit.yaml` at repo root — see template below.
3. Open a PR — CodeRabbit will start posting reviews automatically.

## Default behaviour (no config needed)
- Reviews every PR
- Summarizes the diff in the PR description area
- Posts inline review comments on questionable patterns
- Re-reviews on each new commit

## Recommended per-repo `.coderabbit.yaml` (copy as starting point)

```yaml
# yaml-language-server: $schema=https://coderabbit.ai/integrations/schema.v2.json
language: en-US
early_access: false

reviews:
  profile: chill           # less noisy than `assertive`
  request_changes_workflow: false
  high_level_summary: true
  poem: false              # haiku summaries are off
  review_status: true
  collapse_walkthrough: true

  auto_review:
    enabled: true
    drafts: false
    base_branches:
      - main
    ignore_title_keywords:
      - WIP
      - DRAFT

  path_filters:
    - "!**/dist/**"
    - "!**/build/**"
    - "!**/*.min.js"
    - "!**/package-lock.json"
    - "!**/bun.lock"
    - "!**/bun.lockb"

  path_instructions:
    - path: "**/*.cs"
      instructions: |
        Follow .NET coding conventions. Flag missing async/await,
        ConfigureAwait(false) where appropriate in library code,
        IDisposable patterns.
    - path: "**/*.tsx"
      instructions: |
        Flag missing `key` props in lists, useEffect deps,
        accessibility issues (alt, aria-*).
    - path: "**/*.go"
      instructions: |
        Flag missing error checks, channel leaks, goroutine leaks.

chat:
  auto_reply: true
```

Pairs well with admin-enforced branch protection — CodeRabbit becomes the de-facto reviewer on a solo-dev account.
