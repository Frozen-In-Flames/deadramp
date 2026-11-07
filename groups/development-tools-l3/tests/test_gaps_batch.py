"""Final GAPS batch tests — Remainder Singleton 58 (DevTools L3).

Pins the extension surface in ``src/devtools/extensions.py``
against the section's 4 open Extended entries (see
``../BATCH.md``):

- Container orchestration platform (idx 701) — reference:
  cluster reference + reported outcome records; nothing is
  orchestrated or run here.
- Integrated development environment / developer workspace
  (idx 702) — built: workspace declarations + session records;
  hosting itself is not built.
- Platform monitoring & logging / observability (idx 703) —
  reference: telemetry source + report records; view totals
  are sums of the recorded report counts, stated as such.
- Platform networking (idx 704) — built: route and policy
  definitions held as data over core environments, plus
  reported route outcomes; definitions are never applied.

Plus the High apparatus on the new surface (hash chain
verifies after extension activity, audit-failure rollback,
auditor denied extension reads/writes) and the batch's fresh
negative control: the latest-label seam ``_latest_label`` — a
mutant that reads the earliest record must misstate every
derived "latest" label.
"""

import os
import tempfile
import unittest

import devtools_helpers as helpers
from devtools.audit import AuditLog
from devtools.errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from devtools.extensions import DevToolsExtensions
from devtools.store import DevToolsStore

ADMIN = helpers.ADMIN
DEVELOPER = helpers.DEVELOPER
VIEWER = helpers.VIEWER
AUDITOR = helpers.AUDITOR


def make_ext():
    """Fresh core store + audit + project + environment, plus ext."""
    audit = AuditLog()
    store, project = helpers.make_store(audit=audit)
    env = store.create_environment("prod", ADMIN)
    return store, audit, project, env, DevToolsExtensions(store)


def all_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from all_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from all_keys(item)


class TestClusterReference(unittest.TestCase):
    """Idx 701 — the orchestration platform as labeled reference."""

    def setUp(self):
        self.store, self.audit, self.project, self.env, self.ext = make_ext()
        self.pid = self.project["id"]

    def test_reference_shape_and_labels(self):
        cluster = self.ext.record_cluster_reference(
            self.pid, "apps-cluster", DEVELOPER, platform_ref="rosa-1")
        self.assertEqual(cluster["id"], "clu-1")
        self.assertTrue(cluster["reference_stub"])
        self.assertEqual(cluster["status"], "recorded_reference_only")
        self.assertFalse(cluster["orchestrated_here"])
        self.assertFalse(cluster["containers_run_here"])
        self.assertFalse(cluster["managed_here"])
        self.assertEqual(cluster["platform_ref"], "rosa-1")

    def test_outcome_verbatim_and_view_derives_latest(self):
        cluster = self.ext.record_cluster_reference(self.pid, "c", DEVELOPER)
        self.ext.record_cluster_outcome(
            cluster["id"], "reported_provisioning", DEVELOPER)
        out = self.ext.record_cluster_outcome(
            cluster["id"], "reported_ready", DEVELOPER,
            workload_ref="payments-api")
        self.assertEqual(out["id"], "clo-2")
        self.assertTrue(out["reference_stub"])
        self.assertFalse(out["orchestrated_here"])
        view = self.ext.cluster_reference_view(cluster["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_reported_status"], "reported_ready")
        # The stored reference record carries no derived key.
        stored = self.ext.get_cluster_reference(cluster["id"], ADMIN)
        self.assertNotIn("latest_reported_status", stored)
        self.assertNotIn("outcome_count", stored)
        self.assertEqual(stored["status"], "recorded_reference_only")

    def test_unknown_project_rejected_and_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_cluster_reference("prj-99", "c", DEVELOPER)
        cluster = self.ext.record_cluster_reference(self.pid, "c", DEVELOPER)
        self.assertEqual(cluster["id"], "clu-1")

    def test_outcome_for_unknown_cluster_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_cluster_outcome("clu-99", "x", DEVELOPER)


class TestWorkspaceBuilt(unittest.TestCase):
    """Idx 702 — workspace declarations + session records."""

    def setUp(self):
        self.store, self.audit, self.project, self.env, self.ext = make_ext()
        self.pid = self.project["id"]

    def test_workspace_shape_and_labels(self):
        ws = self.ext.create_workspace(
            self.pid, "payments-ws", DEVELOPER, access_modes=["browser"])
        self.assertEqual(ws["id"], "wsp-1")
        self.assertEqual(ws["access_modes"], ["browser"])
        self.assertFalse(ws["hosted_here"])
        self.assertFalse(ws["provisioned_here"])
        self.assertFalse(ws["filesystem_held_here"])
        self.assertFalse(ws["executed_here"])
        self.assertNotIn("status", ws)

    def test_access_modes_deduped_and_unknown_rejected(self):
        ws = self.ext.create_workspace(
            self.pid, "ws", DEVELOPER,
            access_modes=["browser", "browser", "ssh"])
        self.assertEqual(ws["access_modes"], ["browser", "ssh"])
        with self.assertRaises(ValidationError):
            self.ext.create_workspace(
                self.pid, "ws2", DEVELOPER, access_modes=["telepathy"])
        second = self.ext.create_workspace(self.pid, "ws2", DEVELOPER)
        self.assertEqual(second["id"], "wsp-2")

    def test_sessions_and_view_derives_counts_and_latest(self):
        ws = self.ext.create_workspace(self.pid, "ws", DEVELOPER)
        self.ext.record_workspace_session(
            ws["id"], "subj-1", "reported_active", DEVELOPER)
        self.ext.record_workspace_session(
            ws["id"], "subj-2", "reported_idle", DEVELOPER)
        third = self.ext.record_workspace_session(
            ws["id"], "subj-1", "reported_closed", DEVELOPER)
        self.assertEqual(third["id"], "wss-3")
        self.assertFalse(third["hosted_here"])
        view = self.ext.workspace_view(ws["id"], ADMIN)
        self.assertEqual(view["session_count"], 3)
        self.assertEqual(
            view["sessions_by_status"],
            {"reported_active": 1, "reported_idle": 1,
             "reported_closed": 1},
        )
        self.assertEqual(view["latest_session_status"], "reported_closed")
        stored = self.ext.get_workspace(ws["id"], ADMIN)
        self.assertNotIn("session_count", stored)
        self.assertNotIn("latest_session_status", stored)

    def test_bad_session_status_rejected_and_no_id_consumed(self):
        ws = self.ext.create_workspace(self.pid, "ws", DEVELOPER)
        with self.assertRaises(ValidationError):
            self.ext.record_workspace_session(
                ws["id"], "subj-1", "running", DEVELOPER)
        session = self.ext.record_workspace_session(
            ws["id"], "subj-1", "reported_active", DEVELOPER)
        self.assertEqual(session["id"], "wss-1")


class TestTelemetryReference(unittest.TestCase):
    """Idx 703 — telemetry sources + reports, as reported."""

    def setUp(self):
        self.store, self.audit, self.project, self.env, self.ext = make_ext()
        self.pid = self.project["id"]

    def test_source_shape_and_labels(self):
        source = self.ext.record_telemetry_source(
            self.pid, "platform-metrics", "metrics", DEVELOPER,
            source_ref="prom-1")
        self.assertEqual(source["id"], "tsrc-1")
        self.assertTrue(source["reference_stub"])
        self.assertEqual(source["status"], "recorded_reference_only")
        self.assertFalse(source["collected_here"])
        self.assertFalse(source["monitored_here"])

    def test_kind_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.record_telemetry_source(
                self.pid, "s", "events", DEVELOPER)

    def test_report_count_validation_and_no_id_consumed(self):
        source = self.ext.record_telemetry_source(
            self.pid, "s", "logs", DEVELOPER)
        for bad in (True, 1.5, -1):
            with self.assertRaises(ValidationError):
                self.ext.record_telemetry_report(
                    source["id"], "x", DEVELOPER, event_count=bad)
        report = self.ext.record_telemetry_report(
            source["id"], "window-1", DEVELOPER, event_count=10)
        self.assertEqual(report["id"], "trpt-1")
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["collected_here"])

    def test_view_totals_are_sums_of_recorded_reports(self):
        source = self.ext.record_telemetry_source(
            self.pid, "s", "metrics", DEVELOPER)
        self.ext.record_telemetry_report(
            source["id"], "window-1", DEVELOPER, event_count=10)
        self.ext.record_telemetry_report(
            source["id"], "window-2", DEVELOPER)
        self.ext.record_telemetry_report(
            source["id"], "window-3", DEVELOPER, event_count=5)
        view = self.ext.telemetry_source_view(source["id"], ADMIN)
        self.assertEqual(view["report_count"], 3)
        self.assertEqual(view["total_reported_events"], 15)
        self.assertEqual(view["reports_without_count"], 1)
        self.assertEqual(view["latest_summary_label"], "window-3")
        stored = self.ext.get_telemetry_source(source["id"], ADMIN)
        self.assertNotIn("total_reported_events", stored)


class TestNetworkBuilt(unittest.TestCase):
    """Idx 704 — route/policy definitions as data; never applied."""

    def setUp(self):
        self.store, self.audit, self.project, self.env, self.ext = make_ext()
        self.eid = self.env["id"]

    def test_route_shape_and_labels(self):
        route = self.ext.define_network_route(
            self.eid, "api-route", "svc-payments", DEVELOPER,
            host_label="api.example.internal")
        self.assertEqual(route["id"], "nrt-1")
        self.assertFalse(route["applied_here"])
        self.assertFalse(route["provisioned_here"])
        self.assertNotIn("status", route)

    def test_route_unknown_environment_rejected_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.define_network_route(
                "env-99", "r", "svc-x", DEVELOPER)
        route = self.ext.define_network_route(
            self.eid, "r", "svc-x", DEVELOPER)
        self.assertEqual(route["id"], "nrt-1")

    def test_route_outcome_verbatim_and_view(self):
        route = self.ext.define_network_route(
            self.eid, "r", "svc-x", DEVELOPER)
        before = self.ext.get_network_route(route["id"], ADMIN)
        self.ext.record_route_outcome(
            route["id"], "reported_provisioning", DEVELOPER)
        self.ext.record_route_outcome(
            route["id"], "reported_active", DEVELOPER,
            reporter_ref="platform-controller")
        after = self.ext.get_network_route(route["id"], ADMIN)
        self.assertEqual(before, after)
        view = self.ext.network_route_view(route["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_reported_status"], "reported_active")

    def test_policy_rules_held_as_data(self):
        policy = self.ext.define_network_policy(
            self.eid, "baseline",
            [{"rule_ref": "r1", "effect": "allow"},
             {"rule_ref": "r2", "effect": "deny"}],
            DEVELOPER)
        self.assertEqual(policy["id"], "npl-1")
        self.assertEqual(
            policy["rules"],
            [{"rule_ref": "r1", "effect": "allow"},
             {"rule_ref": "r2", "effect": "deny"}],
        )
        self.assertFalse(policy["enforced_here"])
        self.assertFalse(policy["applied_here"])

    def test_policy_rule_validation_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.define_network_policy(
                self.eid, "p",
                [{"rule_ref": "r1", "effect": "allow"},
                 {"rule_ref": "r1", "effect": "deny"}],
                DEVELOPER)
        with self.assertRaises(ValidationError):
            self.ext.define_network_policy(
                self.eid, "p",
                [{"rule_ref": "r1", "effect": "log"}], DEVELOPER)
        with self.assertRaises(ValidationError):
            self.ext.define_network_policy(self.eid, "p", [], DEVELOPER)
        policy = self.ext.define_network_policy(
            self.eid, "p", [{"rule_ref": "r1", "effect": "allow"}],
            DEVELOPER)
        self.assertEqual(policy["id"], "npl-1")


class TestCoreUntouched(unittest.TestCase):
    """Creating extension records writes no core record set."""

    def test_all_extension_records_change_no_core_record(self):
        store, audit, project, env, ext = make_ext()
        pid, eid = project["id"], env["id"]

        def counts():
            return (
                len(store.list_projects()),
                len(store.list_issues()),
                len(store.list_reviews()),
                len(store.list_builds()),
                len(store.list_releases()),
                len(store.list_artifacts()),
                len(store.list_environments()),
                len(store.list_deployments()),
            )

        before_counts = counts()
        before_project = store.get_project(pid, ADMIN)
        cluster = ext.record_cluster_reference(pid, "c", DEVELOPER)
        ext.record_cluster_outcome(cluster["id"], "reported_ready",
                                   DEVELOPER)
        ws = ext.create_workspace(pid, "ws", DEVELOPER)
        ext.record_workspace_session(
            ws["id"], "subj-1", "reported_active", DEVELOPER)
        source = ext.record_telemetry_source(pid, "s", "metrics",
                                             DEVELOPER)
        ext.record_telemetry_report(source["id"], "w", DEVELOPER,
                                    event_count=3)
        route = ext.define_network_route(eid, "r", "svc-x", DEVELOPER)
        ext.record_route_outcome(route["id"], "reported_active",
                                 DEVELOPER)
        ext.define_network_policy(
            eid, "p", [{"rule_ref": "r1", "effect": "allow"}], DEVELOPER)
        self.assertEqual(counts(), before_counts)
        self.assertEqual(store.get_project(pid, ADMIN), before_project)

    def test_no_score_field_anywhere(self):
        store, audit, project, env, ext = make_ext()
        pid, eid = project["id"], env["id"]
        cluster = ext.record_cluster_reference(pid, "c", DEVELOPER)
        ext.record_cluster_outcome(cluster["id"], "reported_ready",
                                   DEVELOPER)
        ws = ext.create_workspace(pid, "ws", DEVELOPER)
        ext.record_workspace_session(
            ws["id"], "subj-1", "reported_active", DEVELOPER)
        source = ext.record_telemetry_source(pid, "s", "logs", DEVELOPER)
        ext.record_telemetry_report(source["id"], "w", DEVELOPER,
                                    event_count=1)
        route = ext.define_network_route(eid, "r", "svc-x", DEVELOPER)
        ext.record_route_outcome(route["id"], "reported_active",
                                 DEVELOPER)
        policy = ext.define_network_policy(
            eid, "p", [{"rule_ref": "r1", "effect": "deny"}], DEVELOPER)
        surface = [
            cluster, ws, source, route, policy,
            ext.cluster_reference_view(cluster["id"], ADMIN),
            ext.workspace_view(ws["id"], ADMIN),
            ext.telemetry_source_view(source["id"], ADMIN),
            ext.network_route_view(route["id"], ADMIN),
        ]
        for record in surface:
            for key in all_keys(record):
                self.assertNotIn("score", key.lower())


class TestHighApparatus(unittest.TestCase):
    """The High baseline apparatus binds the extension surface."""

    def setUp(self):
        self.store, self.audit, self.project, self.env, self.ext = make_ext()
        self.pid = self.project["id"]

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_workspace(self.pid, "ws", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("deployment_write:denied", actions)
        self.assertEqual(self.ext.list_workspaces(self.pid, ADMIN), [])

    def test_auditor_denied_extension_read_and_write(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_cluster_reference(self.pid, "c", AUDITOR)
        ws = self.ext.create_workspace(self.pid, "ws", DEVELOPER)
        with self.assertRaises(PermissionDenied):
            self.ext.get_workspace(ws["id"], AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.list_workspaces(self.pid, AUDITOR)

    def test_chain_verifies_and_auditor_core_duty_works(self):
        self.ext.create_workspace(self.pid, "ws", DEVELOPER)
        self.ext.record_cluster_reference(self.pid, "c", DEVELOPER)
        self.assertEqual(self.audit.verify_chain(), (True, None))
        ext_entries = self.audit.query(action="ext_workspace_create")
        self.assertEqual(len(ext_entries), 1)
        self.assertEqual(ext_entries[0]["actor"], "bob")

    def test_audit_failure_rolls_back_record_and_id(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "audit.jsonl")
        audit = AuditLog(path=path)
        store = DevToolsStore(audit=audit)
        project = store.create_project("P", ADMIN)
        ext = DevToolsExtensions(store)
        os.remove(path)
        os.mkdir(path)
        try:
            with self.assertRaises(AuditWriteError):
                ext.create_workspace(project["id"], "ws", DEVELOPER)
        finally:
            os.rmdir(path)
        self.assertEqual(ext.list_workspaces(project["id"], ADMIN), [])
        ws = ext.create_workspace(project["id"], "ws", DEVELOPER)
        self.assertEqual(ws["id"], "wsp-1")


class _EarliestLabelExtensions(DevToolsExtensions):
    """Mutant: the latest-label seam reads the earliest record."""

    @staticmethod
    def _latest_label(records, key):
        return records[0][key] if records else None


class TestLatestLabelNegativeControl(unittest.TestCase):
    """Fresh negative control for the latest-label seam.

    Canonical expectation: a derived view's "latest" label is
    the most recently recorded one. The mutant seam reads the
    earliest record and must misstate it.
    """

    def setUp(self):
        self.store, self.audit, self.project, self.env, self.ext = make_ext()
        self.pid = self.project["id"]
        self.mutant = _EarliestLabelExtensions(self.store)
        ws = self.ext.create_workspace(self.pid, "ws", DEVELOPER)
        self.ws_id = ws["id"]
        self.ext.record_workspace_session(
            self.ws_id, "subj-1", "reported_active", DEVELOPER)
        self.ext.record_workspace_session(
            self.ws_id, "subj-1", "reported_closed", DEVELOPER)
        # The mutant shares the store but not the records; rebuild
        # the same stream on the mutant for a fair comparison.
        mws = self.mutant.create_workspace(self.pid, "ws", DEVELOPER)
        self.mws_id = mws["id"]
        self.mutant.record_workspace_session(
            self.mws_id, "subj-1", "reported_active", DEVELOPER)
        self.mutant.record_workspace_session(
            self.mws_id, "subj-1", "reported_closed", DEVELOPER)

    def test_canonical_latest_is_most_recent(self):
        view = self.ext.workspace_view(self.ws_id, ADMIN)
        self.assertEqual(view["latest_session_status"], "reported_closed")
        self.assertEqual(view["session_count"], 2)

    def test_mutant_reports_earliest(self):
        view = self.mutant.workspace_view(self.mws_id, ADMIN)
        self.assertEqual(view["latest_session_status"], "reported_active")

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self.mutant.workspace_view(self.mws_id, ADMIN)
                ["latest_session_status"],
                "reported_closed")


if __name__ == "__main__":
    unittest.main()
