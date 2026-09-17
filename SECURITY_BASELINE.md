# Repository security baseline

This account uses per-repository security settings. The public `.github` repository shares community policy, a Renovate preset, and explicitly referenced workflows; GitHub does not inherit its repository settings into other repositories.

## Active repositories

- Enable public pull requests (`pull_request_creation_policy: all`). Require PRs, resolved conversations, linear history, and the repository's verified PR checks on the default branch. Block force pushes and deletion, including routine administrator bypasses.
- Require CodeQL findings review at the high/critical security threshold. An analysis upload succeeding is not a clean security result.
- Use the same `security-and-quality` CodeQL suite for the declared application languages and GitHub Actions on PRs, default-branch pushes, and weekly. Investigate disabled workflows and analyses older than 14 days.
- Enable secret scanning, push protection, private vulnerability reporting, Dependabot alerts, and healthy security-update automation.
- Require full commit SHAs for Actions and reusable workflows. Allow only the required Actions, and let Renovate maintain the pins through reviewed PRs.
- Default workflow tokens to read-only. Give publishing jobs only their necessary write permissions. Disable workflow approval of PRs.
- Require maintainer approval for workflow runs from all external contributors.
- Restrict privileged deployments to trusted source events and refs. A `workflow_run` branch-name filter does not establish repository ownership.
- Restrict production, GitHub Pages, and security-audit environments to `main`, with administrator bypass disabled. Store deployment and audit credentials in their protected environments; prefer provider-supported short-lived credentials.
- Enable immutable releases and protect `v*` and automated `build/*` release tags against changes/deletion. Upload all assets to a draft before publishing. One workflow owns each release.
- Keep ecosystem-native dependency audits in CI. In particular, a clean GitHub Dependabot dashboard does not prove that every transitive dependency in a Bun lockfile was audited.

Solo-maintained repositories require PRs without mandatory self-approval. Independent review can be required when another maintainer is available. Existing authorized collaborator grants are preserved; review access periodically.

## Archived repositories

Keep archived repositories read-only and treat their software as unsupported. Remove retained Actions secrets that no longer have an active repository consumer. Removing a GitHub secret does not revoke its underlying provider credential: review and revoke obsolete Docker Hub or other provider tokens separately, checking for consumers outside the archived repository first.

Archiving does not remove published Pages sites, packages, or releases. Decide separately whether each published artifact should remain available. Restore the active baseline before reactivation.

## Running the drift audit

With `gh` authenticated as the owner:

```sh
python3 scripts/security_audit.py --owner jonathanperis
python3 scripts/security_audit.py --owner jonathanperis --json
```

The audit performs GET requests only. It reports sanitized metadata and findings, not credential values. Exit code 1 indicates a failed control; exit code 2 indicates incomplete visibility or an API failure. Archived retained-secret entries are warnings. Inventory covers repositories visible to the token, so select all owned repositories when provisioning its access.

The audit checks protection presence, trusted required checks, security gates, exact Action allowlists, fork approval, scanner state and language freshness, urgent alerts, release settings, deployment restrictions, and repository access entries. `REQUIRED_LANGUAGES`, `REQUIRED_CHECKS`, and `ALLOWED_ACTIONS` in `scripts/security_audit.py` declare the stack-specific requirements under this common standard. Update them and the reviewed collaborator allowlist when onboarding repositories or changing ownership. Installed-app grants, account authentication settings, provider-token validity, and application exploitability require separate review.

### Scheduled execution

`Account security audit` runs weekly and supports manual dispatch from `main`. It requires `ACCOUNT_SECURITY_AUDIT_TOKEN` in the protected `security-audit` environment: a dedicated, expiring fine-grained personal access token selecting the audited repositories and granting **read-only** Administration, Actions, Contents, Code scanning alerts, Dependabot alerts, Environments, Metadata, Secret scanning alerts, Secrets, and Webhooks permissions as required by the audited endpoints.

Provision the token directly through GitHub settings or `gh secret set ACCOUNT_SECURITY_AUDIT_TOKEN --repo jonathanperis/.github --env security-audit`; do not paste it into issues, PRs, audit output, or chat. Do not reuse a developer's broad local GitHub credential. The workflow reports an explicit setup failure if the dedicated token is absent; missing access never produces a passing audit.

GitHub cannot return existing secret values. Moving a deployment secret requires its original value or a new provider-issued credential. Verify a replacement's consumers before removing the old entry. Re-enable paused Dependabot security updates through the repository's updater controls when a settings API enable request does not clear its paused state.

GitHub can suspend scheduled workflows in inactive public repositories after 60 days. Run this read-only CLI from an external scheduler when the account is routinely inactive, or monitor the audit workflow's state independently. A schedule declaration alone does not guarantee continued execution.
