#!/usr/bin/env python3
"""Read-only repository security drift audit using the authenticated gh CLI."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import re
import subprocess
import sys
from urllib.parse import quote

REQUIRED_LANGUAGES = {
    ".github": {"actions", "python"},
    "blazor-mudblazor-starter": {"actions", "csharp", "javascript-typescript"},
    "cpnucleo": {"actions", "csharp", "javascript-typescript"},
    "jonathanperis": {"actions"},
    "jonathanperis.github.io": {"actions", "javascript-typescript"},
    "solar-system-simulator": {"actions", "c-cpp", "javascript-typescript"},
    "speedy-bird-lynx": {"actions", "javascript-typescript"},
    "super-mango-editor": {"actions", "c-cpp"},
}
ALLOWED_COLLABORATORS = {"jonathanperis/super-mango-editor": {"fersantos"}}


class ApiError(RuntimeError):
    def __init__(self, status):
        self.status = str(status or "unknown")
        super().__init__(f"GitHub API unavailable (HTTP {self.status})")


def api(path, *, paginate=False, projection=None):
    command = ["gh", "api", path]
    if paginate:
        command.append("--paginate")
        if not projection:
            command.append("--slurp")
    if projection:
        command.extend(["--jq", projection])
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if paginate and projection and result.returncode == 0:
        # gh forbids --slurp with --jq and emits one filtered JSON value per page.
        decoder = json.JSONDecoder()
        remaining = result.stdout.strip()
        pages = []
        try:
            while remaining:
                page, end = decoder.raw_decode(remaining)
                pages.append(page)
                remaining = remaining[end:].lstrip()
        except json.JSONDecodeError:
            raise ApiError(None) from None
        if not pages:
            raise ApiError(None)
        if isinstance(pages[0], int):
            return sum(pages)
        return [item for page in pages for item in page]
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        raise ApiError(None) from None
    if result.returncode:
        error = data[0] if isinstance(data, list) and data else data
        status = error.get("status") if isinstance(error, dict) else None
        if not status:
            match = re.search(r"HTTP (\d{3})", result.stderr)
            status = match.group(1) if match else None
        raise ApiError(status)
    return [item for page in data for item in page] if paginate and not projection else data


def findings_for(snapshot, now):
    """Assess collected metadata; unavailable controls never count as passing."""
    findings = []

    def finding(level, control, detail):
        findings.append({"level": level, "control": control, "detail": detail})

    def require(condition, control, detail):
        if not condition:
            finding("fail", control, detail)

    for control, status in snapshot.get("unavailable", {}).items():
        finding("unknown", control, f"API unavailable: HTTP {status}")

    secret_alerts = snapshot.get("secret_alerts")
    if secret_alerts is not None:
        require(not secret_alerts, "secret-alerts", f"{len(secret_alerts)} open secret alerts")

    if snapshot["archived"]:
        if snapshot.get("secret_count", 0):
            finding("warn", "archived-secrets", f"{snapshot['secret_count']} retained repository secret entries")
        return findings

    if "pull_requests_enabled" in snapshot:
        if snapshot["pull_requests_enabled"] is None:
            finding("unknown", "pull-request-feature", "Pull request availability was not returned")
        else:
            require(snapshot["pull_requests_enabled"], "pull-request-feature", "Enable pull requests before requiring them")

    security = snapshot.get("security")
    if security is None and "security" not in snapshot.get("unavailable", {}):
        finding("unknown", "security", "Security settings omitted; verify token permissions")
    elif security is not None:
        for key in ("secret_scanning", "secret_scanning_push_protection"):
            require(security.get(key, {}).get("status") == "enabled", key, "Must be enabled")

    classic = snapshot.get("classic")
    rules = snapshot.get("rules")
    if classic is not None and rules is not None:
        by_type = {rule["type"]: rule for rule in rules}
        pr = by_type.get("pull_request", {}).get("parameters", {})
        require("pull_request" in by_type or classic.get("required_pull_request_reviews") is not None,
                "pull-requests", "Default branch must require pull requests")
        require("deletion" in by_type or bool(classic) and not classic.get("allow_deletions", {}).get("enabled", True),
                "branch-deletion", "Default branch deletion must be blocked")
        require("non_fast_forward" in by_type or bool(classic) and not classic.get("allow_force_pushes", {}).get("enabled", True),
                "force-push", "Default branch force pushes must be blocked")
        require("required_linear_history" in by_type or classic.get("required_linear_history", {}).get("enabled"),
                "linear-history", "Linear history must be enforced")
        require(pr.get("required_review_thread_resolution") or classic.get("required_conversation_resolution", {}).get("enabled"),
                "review-conversations", "Review conversations must be resolved")
        checks = by_type.get("required_status_checks", {}).get("parameters", {}).get("required_status_checks", [])
        checks = checks or classic.get("required_status_checks", {}).get("checks", [])
        require(bool(checks), "required-ci", "Require the repository's verified PR checks")
        tools = by_type.get("code_scanning", {}).get("parameters", {}).get("code_scanning_tools", [])
        require(any(tool.get("tool") == "CodeQL" and tool.get("security_alerts_threshold") in
                    ("high_or_higher", "medium_or_higher", "all") for tool in tools),
                "security-gate", "Require CodeQL to block high/critical findings")

    for field, expected in (("default_workflow_permissions", "read"), ("can_approve_pull_request_reviews", False)):
        if "token_permissions" in snapshot:
            require(snapshot["token_permissions"].get(field) == expected, "workflow-token", f"{field} must be {expected}")
    if "actions" in snapshot:
        require(snapshot["actions"].get("sha_pinning_required") is True, "action-pins", "Enforce full-SHA action pins")
        require(snapshot["actions"].get("allowed_actions") == "selected", "allowed-actions", "Restrict allowed Actions")
    if "immutable" in snapshot:
        require(snapshot["immutable"].get("enabled") is True, "immutable-releases", "Enable release immutability")
    if "rulesets" in snapshot:
        tag_rules = [ruleset for ruleset in snapshot["rulesets"] if ruleset.get("target") == "tag"
                     and ruleset.get("enforcement") == "active"
                     and "refs/tags/v*" in ruleset.get("conditions", {}).get("ref_name", {}).get("include", [])
                     and not ruleset.get("conditions", {}).get("ref_name", {}).get("exclude")]
        require(any({"deletion", "non_fast_forward"}.issubset({rule["type"] for rule in ruleset.get("rules", [])})
                    and not ruleset.get("bypass_actors") for ruleset in tag_rules),
                "release-tags", "Protect release tags against replacement/deletion without bypasses")
        active_ids = {rule["ruleset_id"] for rule in snapshot.get("rules", []) if "ruleset_id" in rule}
        for ruleset in snapshot["rulesets"]:
            if ruleset.get("id") in active_ids:
                require(not ruleset.get("bypass_actors"), "branch-bypass", "Default-branch rules must not have routine bypass actors")
    if "reporting" in snapshot:
        require(snapshot["reporting"].get("enabled") is True, "private-reporting", "Enable private vulnerability reporting")
    if "updates" in snapshot:
        require(snapshot["updates"].get("enabled") and not snapshot["updates"].get("paused"),
                "security-updates", "Dependabot security updates are disabled or paused")

    if "workflows" in snapshot:
        codeql = [workflow for workflow in snapshot["workflows"] if workflow.get("path") == ".github/workflows/codeql.yml"]
        require(bool(codeql) and all(workflow.get("state") == "active" for workflow in codeql),
                "codeql-workflow", "CodeQL workflow is absent or disabled")
        if snapshot.get("repo") == "jonathanperis/.github":
            monitor = [workflow for workflow in snapshot["workflows"] if workflow.get("path") == ".github/workflows/security-audit.yml"]
            require(bool(monitor) and all(workflow.get("state") == "active" for workflow in monitor),
                    "audit-workflow", "Account security audit workflow is absent or disabled")
    if "analyses" in snapshot:
        analyses = snapshot["analyses"]
        require(bool(analyses), "codeql-analysis", "No default-branch analysis found")
        latest = {}
        for analysis in analyses:
            category = analysis.get("category", "unknown")
            if category not in latest:
                latest[category] = analysis
        require(any("actions" in category for category in latest), "actions-analysis", "Actions-language analysis is missing")
        repo_name = snapshot.get("repo", "").rsplit("/", 1)[-1]
        expected = REQUIRED_LANGUAGES.get(repo_name)
        if expected is None:
            finding("unknown", "language-coverage", "Declare required CodeQL languages for this repository")
        else:
            actual = {category.rsplit("/language:", 1)[-1] for category in latest}
            require(expected <= actual, "language-coverage", "Missing analysis languages: " + ", ".join(sorted(expected - actual)))
        for category, analysis in latest.items():
            if expected is not None and category not in {f"/language:{language}" for language in expected}:
                continue  # Superseded analysis categories are not active scanner configurations.
            timestamp = datetime.fromisoformat(analysis["created_at"].replace("Z", "+00:00"))
            require(timestamp >= now - timedelta(days=14) and not analysis.get("error"),
                    "codeql-freshness", f"Analysis is stale or failed: {category}")

    for kind in ("dependency_alerts", "code_alerts"):
        if kind in snapshot:
            urgent = [alert for alert in snapshot[kind] if alert.get("severity") in ("high", "critical")]
            require(not urgent, kind, f"{len(urgent)} open high/critical alerts")
    for kind in ("deploy_keys", "webhooks", "invitations", "runners"):
        if kind in snapshot:
            require(not snapshot[kind], kind, f"Review {snapshot[kind]} configured access entries")
    if "collaborators" in snapshot:
        owner = snapshot["repo"].split("/", 1)[0]
        allowed = {owner} | ALLOWED_COLLABORATORS.get(snapshot["repo"], set())
        unexpected = [member["login"] for member in snapshot["collaborators"] if member["login"] not in allowed]
        require(not unexpected, "collaborators", "Review unexpected collaborators: " + ", ".join(unexpected))
    if "environments" in snapshot:
        for environment in snapshot["environments"]:
            if environment["name"].startswith("production"):
                policy = environment.get("deployment_branch_policy") or {}
                refs = environment.get("allowed_refs", [])
                trusted = policy.get("protected_branches") or (policy.get("custom_branch_policies") and bool(refs)
                           and all(ref.get("name") == "main" and ref.get("type") == "branch" for ref in refs))
                require(trusted, "production-environment", f"Unrestricted deployment environment: {environment['name']}")
    return findings


def collect(repository):
    base = f"repos/{repository['full_name']}"
    snapshot = {"repo": repository["full_name"], "archived": repository["archived"], "unavailable": {}}

    def read(control, suffix="", *, projection=None, absent=None, paginate=False):
        try:
            value = api(base + suffix, projection=projection, paginate=paginate)
        except ApiError as error:
            if error.status == "404" and absent is not None:
                value = absent
            else:
                snapshot["unavailable"][control] = error.status
                return
        snapshot[control] = value

    # Filter at the gh boundary: never retain or print returned secret values.
    read("secret_alerts", "/secret-scanning/alerts?state=open&per_page=100", projection="[.[] | {number}]", paginate=True)
    read("secret_count", "/actions/secrets", projection=".total_count")
    if repository["archived"]:
        return snapshot
    read("security", projection="{has_pull_requests,security_and_analysis}")
    if "security" in snapshot:
        settings = snapshot["security"]
        snapshot["pull_requests_enabled"] = settings["has_pull_requests"]
        snapshot["security"] = settings["security_and_analysis"]
    branch = quote(repository["default_branch"], safe="")
    read("classic", f"/branches/{branch}/protection", absent={})
    read("rules", f"/rules/branches/{branch}")
    try:
        snapshot["rulesets"] = [api(base + "/rulesets/" + str(ruleset["id"]))
                                for ruleset in api(base + "/rulesets?per_page=100", paginate=True)]
    except ApiError as error:
        snapshot["unavailable"]["rulesets"] = error.status
    read("actions", "/actions/permissions")
    read("token_permissions", "/actions/permissions/workflow")
    read("immutable", "/immutable-releases")
    read("reporting", "/private-vulnerability-reporting")
    read("updates", "/automated-security-fixes")
    read("workflows", "/actions/workflows?per_page=100", projection=".workflows | map({path,state})")
    read("analyses", f"/code-scanning/analyses?ref=refs/heads/{branch}&per_page=100",
         projection="map({category,created_at,error})", absent=[], paginate=True)
    read("dependency_alerts", "/dependabot/alerts?state=open&per_page=100",
         projection="map({number,severity:.security_advisory.severity})", paginate=True)
    read("code_alerts", "/code-scanning/alerts?state=open&per_page=100",
         projection="map({number,severity:.rule.security_severity_level})", absent=[], paginate=True)
    for control, suffix in (("deploy_keys", "/keys"), ("webhooks", "/hooks"), ("invitations", "/invitations")):
        read(control, suffix + "?per_page=100", projection="length", paginate=True)
    read("collaborators", "/collaborators?affiliation=all&per_page=100", projection="map({login})", paginate=True)
    read("runners", "/actions/runners", projection=".total_count")
    read("environments", "/environments?per_page=100",
         projection=".environments | map({name,deployment_branch_policy})")
    for environment in snapshot.get("environments", []):
        if environment["name"].startswith("production") and (environment.get("deployment_branch_policy") or {}).get("custom_branch_policies"):
            name = quote(environment["name"], safe="")
            try:
                environment["allowed_refs"] = api(base + f"/environments/{name}/deployment-branch-policies?per_page=100",
                                                  projection=".branch_policies | map({name,type})")
            except ApiError as error:
                snapshot["unavailable"]["environment-refs:" + environment["name"]] = error.status
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default="jonathanperis")
    parser.add_argument("--json", action="store_true", help="Emit only sanitized findings as JSON")
    args = parser.parse_args()
    try:
        repositories = api("user/repos?affiliation=owner&per_page=100", paginate=True)
        repositories = [repo for repo in repositories if repo["owner"]["login"].lower() == args.owner.lower()]
        if not repositories:
            raise ApiError(None)
        with ThreadPoolExecutor(max_workers=4) as pool:
            snapshots = list(pool.map(collect, sorted(repositories, key=lambda repo: repo["full_name"])))
    except ApiError as error:
        print(f"Audit incomplete: {error}. Verify the account and read-only token permissions.", file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc)
    report = [{"repo": snapshot["repo"], "archived": snapshot["archived"],
               "findings": findings_for(snapshot, now)} for snapshot in snapshots]
    if args.json:
        print(json.dumps({"checked_at": now.isoformat(), "repositories": report}, indent=2))
    else:
        for result in report:
            print(result["repo"] + (" [archived]" if result["archived"] else ""))
            for finding in result["findings"]:
                print(f"  {finding['level'].upper()}: {finding['control']}: {finding['detail']}")
            if not result["findings"]:
                print("  PASS: checked controls match the baseline")
    levels = {finding["level"] for result in report for finding in result["findings"]}
    return 2 if "unknown" in levels else 1 if "fail" in levels else 0


if __name__ == "__main__":
    sys.exit(main())
