# Cursor Bugbot setup for jonathanperis/* repos

[Cursor Bugbot](https://cursor.com/docs/bugbot) is the AI code reviewer for these repos. It reviews PRs, posts inline comments on likely bugs and posts a PR summary.

## One-time setup

1. In the [Cursor dashboard](https://cursor.com/dashboard), connect GitHub and grant the Cursor app access to the jonathanperis/* repos.
2. Turn Bugbot on for each repo under Bugbot settings.
3. Open a PR. Bugbot reviews it automatically, or comment `bugbot run` to trigger a review by hand.

## Per-repo files

- `.cursor/BUGBOT.md`: review rules, written as plain Markdown. Bugbot always reads the root file, plus any `.cursor/BUGBOT.md` in the directories of the changed files, so a subfolder can add its own rules.
- `.cursor/config/bugbot.yaml`: review behavior. Bugbot reads it from the PR's base branch.

## Recommended `.cursor/config/bugbot.yaml`

```yaml
version: 1
triggers:
  drafts: false          # skip draft PRs
  frequency: everyPush   # or oncePerPr
prSummary:
  mode: comment          # disabled | description | comment
```

## Recommended `.cursor/BUGBOT.md` starting point

```markdown
# Bugbot review rules

Report real bugs, security issues and regressions. Skip style nitpicks
and preference-only suggestions.

## Generated and vendored files

Do not comment on these paths; they are generated, vendored or lockfiles:

- `**/dist/**`
- `**/build/**`
- `**/*.min.js`
- `**/package-lock.json`
- `**/bun.lock`

## Path-specific rules

### `**/*.cs`

Follow .NET coding conventions. Flag missing async/await,
ConfigureAwait(false) where appropriate in library code,
IDisposable patterns.

### `.github/workflows/**/*.yml`

Flag any user-controlled input interpolated directly in
run: blocks (workflow injection risk). Recommend env: + quoting.
```

Pairs well with admin-enforced branch protection: Bugbot becomes the de-facto reviewer on a solo-dev account.
