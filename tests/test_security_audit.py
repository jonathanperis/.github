from datetime import datetime, timedelta, timezone
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch
import subprocess

spec = importlib.util.spec_from_file_location("security_audit", Path(__file__).parents[1] / "scripts/security_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SecurityAuditTests(unittest.TestCase):
    def test_cli_reports_findings_without_serializing_credential_payloads(self):
        marker = "synthetic-canary-value"
        repository = {"full_name": "jonathanperis/archived", "owner": {"login": "jonathanperis"}, "archived": True}
        snapshot = {"repo": repository["full_name"], "archived": True, "secret_count": 2,
                    "secret_alerts": [{"number": 7, "secret": marker}]}
        for arguments in ([], ["--json"]):
            with self.subTest(arguments=arguments), patch.object(audit.sys, "argv", ["security_audit.py", *arguments]), \
                    patch.object(audit, "api", return_value=[repository]), patch.object(audit, "collect", return_value=snapshot):
                output = io.StringIO()
                with redirect_stdout(output):
                    status = audit.main()
                self.assertEqual(1, status)
                self.assertIn("secret-alerts", output.getvalue())
                self.assertNotIn(marker, output.getvalue())

    def test_healthy_baseline_passes_and_missing_security_settings_do_not(self):
        now = datetime.now(timezone.utc)
        snapshot = {"repo": "jonathanperis/jonathanperis", "archived": False, "pull_requests_enabled": True,
                    "security": {key: {"status": "enabled"} for key in ("secret_scanning", "secret_scanning_push_protection")},
                    "classic": {}, "rules": [
                        {"type": "pull_request", "parameters": {"required_review_thread_resolution": True}},
                        {"type": "deletion"}, {"type": "non_fast_forward"}, {"type": "required_linear_history"},
                        {"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "build"}]}},
                        {"type": "code_scanning", "parameters": {"code_scanning_tools": [
                            {"tool": "CodeQL", "security_alerts_threshold": "high_or_higher"}]}}],
                    "actions": {"sha_pinning_required": True, "allowed_actions": "selected"},
                    "token_permissions": {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False},
                    "immutable": {"enabled": True}, "reporting": {"enabled": True}, "updates": {"enabled": True, "paused": False},
                    "workflows": [{"path": ".github/workflows/codeql.yml", "state": "active"}],
                    "analyses": [{"category": "/language:actions", "created_at": now.isoformat(), "error": ""}],
                    "rulesets": [{"target": "tag", "enforcement": "active", "bypass_actors": [],
                                  "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
                                  "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}],
                    "collaborators": [{"login": "jonathanperis"}], "secret_alerts": [], "dependency_alerts": [], "code_alerts": []}
        self.assertEqual([], audit.findings_for(snapshot, now))
        snapshot["pull_requests_enabled"] = False
        self.assertEqual(["pull-request-feature"], [item["control"] for item in audit.findings_for(snapshot, now)])
        snapshot["pull_requests_enabled"] = True
        snapshot["security"] = None
        self.assertEqual(["unknown"], [item["level"] for item in audit.findings_for(snapshot, now)])

    def test_unavailable_scanning_is_not_clean_and_archives_are_distinct(self):
        now = datetime.now(timezone.utc)
        for archived in (False, True):
            with self.subTest(archived=archived):
                snapshot = {"archived": archived, "unavailable": {"secret_alerts": "403"}, "secret_count": 2}
                findings = audit.findings_for(snapshot, now)
                self.assertIn("unknown", {item["level"] for item in findings})
                self.assertEqual(archived, any(item["control"] == "archived-secrets" for item in findings))

    def test_protection_presence_does_not_substitute_for_pr_or_security_gates(self):
        now = datetime.now(timezone.utc)
        classic = {"required_linear_history": {"enabled": True}, "required_status_checks": {"checks": [{"context": "build"}]},
                   "allow_deletions": {"enabled": False}, "allow_force_pushes": {"enabled": False}}
        snapshot = {"archived": False, "classic": classic, "rules": []}
        controls = {item["control"] for item in audit.findings_for(snapshot, now)}
        self.assertTrue({"pull-requests", "security-gate", "review-conversations"}.issubset(controls))
        self.assertFalse({"force-push", "branch-deletion", "linear-history", "required-ci"} & controls)

    def test_stale_scans_and_urgent_findings_survive_other_healthy_signals(self):
        now = datetime.now(timezone.utc)
        snapshot = {"archived": False, "workflows": [{"path": ".github/workflows/codeql.yml", "state": "active"}],
                    "analyses": [{"category": "/language:actions", "created_at": (now - timedelta(days=20)).isoformat(), "error": ""}],
                    "dependency_alerts": [{"number": 1, "severity": "high"}], "code_alerts": [{"number": 2, "severity": None}]}
        controls = {item["control"] for item in audit.findings_for(snapshot, now)}
        self.assertTrue({"codeql-freshness", "dependency_alerts"}.issubset(controls))
        self.assertFalse({"codeql-workflow", "actions-analysis", "code_alerts"} & controls)

    def test_production_custom_ref_policy_rejects_wildcards_and_tags(self):
        now = datetime.now(timezone.utc)
        for name, kind, trusted in (("main", "branch", True), ("*", "branch", False), ("main", "tag", False)):
            with self.subTest(name=name, kind=kind):
                snapshot = {"archived": False, "environments": [{"name": "production-hostinger",
                            "deployment_branch_policy": {"custom_branch_policies": True, "protected_branches": False},
                            "allowed_refs": [{"name": name, "type": kind}]}]}
                self.assertEqual(not trusted, any(item["control"] == "production-environment"
                                                 for item in audit.findings_for(snapshot, now)))

    def test_api_handles_empty_success_pagination_and_permission_failures(self):
        responses = [subprocess.CompletedProcess([], 0, "", ""),
                     subprocess.CompletedProcess([], 0, '[[{"id":1}],[{"id":2}]]', ""),
                     subprocess.CompletedProcess([], 0, '[{"number":1,"severity":"note"}]\n[{"number":101,"severity":"critical"}]\n', ""),
                     subprocess.CompletedProcess([], 1, '{"status":"403","message":"private details"}', "")]
        with patch.object(audit.subprocess, "run", side_effect=responses) as run:
            self.assertEqual({}, audit.api("repos/example/repo/vulnerability-alerts"))
            self.assertEqual([{"id": 1}, {"id": 2}], audit.api("user/repos", paginate=True))
            self.assertEqual([{"number": 1, "severity": "note"}, {"number": 101, "severity": "critical"}],
                             audit.api("repos/example/repo/alerts", paginate=True, projection="map({number,severity})"))
            projected_command = run.call_args.args[0]
            self.assertNotIn("--slurp", projected_command)
            with self.assertRaisesRegex(audit.ApiError, "HTTP 403") as failure:
                audit.api("repos/example/repo/actions/secrets")
            self.assertNotIn("private details", str(failure.exception))
            self.assertTrue(all(call.kwargs.get("capture_output") for call in run.call_args_list))


if __name__ == "__main__":
    unittest.main()
