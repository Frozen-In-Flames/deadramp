"""Final GAPS batch tests — Storage L3-adjacent singleton.

Pins the extension surface in ``storage.extensions`` for the 7
open entries of this singleton's GAPS.md section (idx 735–741;
see ``BATCH.md`` in the group directory): backup & recovery
(reference), anomaly detection & alerting (reference), granular
remediation (built), workload protection connectors
(reference), the management console (built), SaaS operations
automation (built), and the hybrid cloud synchronization
engine (built) — each in its records form over the carried
core, under the High apparatus (hash-chained audit including
denied attempts; the separated auditor denied every extension
operation).

Traces to: UNION-SPEC.md (the singleton's named gaps) and
gaps-batch/DECISION.md (the batch build pattern).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from storage.errors import (  # noqa: E402
    NotFoundError, PermissionDenied, ValidationError,
)
from storage.extensions import FORBIDDEN_KEYS, StorageExtensions  # noqa: E402

from storage_helpers import (  # noqa: E402
    ADMIN, AUDITOR, OPERATOR, VIEWER,
    AFTER_BOUNDARY, AT_BOUNDARY, BEFORE_BOUNDARY,
    make_archive, make_message, make_store,
)


def scan_forbidden(obj, path="root"):
    """Recursively collect forbidden keys in a record or view."""
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                hits.append("%s.%s" % (path, key))
            hits.extend(scan_forbidden(value, "%s.%s" % (path, key)))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            hits.extend(scan_forbidden(value, "%s[%d]" % (path, index)))
    return hits


class ExtensionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)
        self.ext = StorageExtensions(self.store)
        self.integration = self.store.create_integration(
            ADMIN, self.org["id"], "mail_platform", "M365 platform record")

    def make_job(self, actor=OPERATOR):
        return self.ext.record_backup_job(
            actor, self.collection["id"], self.integration["id"],
            "nightly", 12, 4096)


class TestBackupJobs(ExtensionFixture):
    """idx 735 — backup & recovery engine (reference)."""

    def test_job_record_shape_and_labels(self):
        job = self.make_job()
        self.assertEqual(
            set(job),
            {"id", "collection_id", "integration_id", "integration_kind",
             "schedule_label", "reported_item_count",
             "reported_byte_total", "reference_stub",
             "reference_transport", "backed_up_here",
             "created_by", "created_utc"})
        self.assertEqual(job["id"], "bak-1")
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["reference_transport"], True)
        self.assertIs(job["backed_up_here"], False)
        self.assertEqual(job["integration_kind"], "mail_platform")

    def test_recording_a_job_changes_no_core_record(self):
        message = make_message(self.store, self.collection)
        before_summary = self.store.summary(ADMIN)
        before_messages = self.store.list_messages(ADMIN)
        self.make_job()
        self.assertEqual(self.store.summary(ADMIN), before_summary)
        self.assertEqual(self.store.list_messages(ADMIN), before_messages)
        self.assertEqual(
            self.store.get_message(ADMIN, message["id"])["id"],
            message["id"])

    def test_outcome_and_recovery_labels_derive_at_read(self):
        job = self.make_job()
        view = self.ext.backup_job_view(ADMIN, job["id"])
        self.assertEqual(view["current_outcome_label"], "unreported")
        self.assertEqual(view["current_recovery_label"], "unreported")
        self.assertEqual(view["outcome_count"], 0)
        self.ext.record_backup_outcome(OPERATOR, job["id"],
                                       "reported_partial")
        self.ext.record_backup_outcome(OPERATOR, job["id"],
                                       "reported_succeeded")
        self.ext.record_recovery_report(OPERATOR, job["id"],
                                        "reported_restored")
        view = self.ext.backup_job_view(ADMIN, job["id"])
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["current_outcome_label"],
                         "reported_succeeded")
        self.assertEqual(view["recovery_count"], 1)
        self.assertEqual(view["current_recovery_label"],
                         "reported_restored")
        stored = self.ext.list_backup_jobs(ADMIN)[0]
        self.assertNotIn("current_outcome_label", stored)
        self.assertNotIn("outcome_count", stored)

    def test_unknown_labels_and_counts_rejected(self):
        job = self.make_job()
        with self.assertRaises(ValidationError):
            self.ext.record_backup_outcome(OPERATOR, job["id"], "ok")
        with self.assertRaises(ValidationError):
            self.ext.record_recovery_report(OPERATOR, job["id"],
                                            "restored")
        with self.assertRaises(ValidationError):
            self.ext.record_backup_job(
                OPERATOR, self.collection["id"], self.integration["id"],
                "nightly", 1.5, 10)
        with self.assertRaises(ValidationError):
            self.ext.record_backup_job(
                OPERATOR, self.collection["id"], self.integration["id"],
                "nightly", True, 10)
        with self.assertRaises(ValidationError):
            self.ext.record_backup_job(
                OPERATOR, self.collection["id"], self.integration["id"],
                "nightly", -1, 10)

    def test_unknown_references_refused(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_backup_job(
                OPERATOR, self.collection["id"], "int-99", "nightly", 1, 1)
        with self.assertRaises(NotFoundError):
            self.ext.record_backup_outcome(OPERATOR, "bak-99",
                                           "reported_failed")


class TestAnomalyReports(ExtensionFixture):
    """idx 736 — anomaly detection & alerting engine (reference)."""

    def test_report_shape_and_labels(self):
        report = self.ext.record_anomaly_report(
            OPERATOR, self.collection["id"], "detector-7", 3, "high")
        self.assertEqual(
            set(report),
            {"id", "collection_id", "detector_label",
             "reported_anomaly_count", "severity_label",
             "reference_stub", "detected_here",
             "created_by", "created_utc"})
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["detected_here"], False)
        self.assertEqual(report["severity_label"], "high")

    def test_dispatch_receipts_and_derived_count(self):
        report = self.ext.record_anomaly_report(
            OPERATOR, self.collection["id"], "detector-7", 3, "high")
        receipt = self.ext.record_alert_dispatch(
            OPERATOR, report["id"], "on-call channel")
        self.assertIs(receipt["reference_stub"], True)
        self.assertIs(receipt["reference_transport"], True)
        self.assertIs(receipt["alerted_here"], False)
        self.ext.record_alert_dispatch(OPERATOR, report["id"],
                                       "ticket queue")
        view = self.ext.anomaly_report_view(ADMIN, report["id"])
        self.assertEqual(view["dispatch_count"], 2)
        self.assertNotIn("dispatch_count",
                         self.ext.list_anomaly_reports(ADMIN)[0])

    def test_report_changes_no_core_record(self):
        before = self.store.summary(ADMIN)
        self.ext.record_anomaly_report(
            OPERATOR, self.collection["id"], "detector-7", 0, "none")
        self.assertEqual(self.store.summary(ADMIN), before)


class TestRemediationActions(ExtensionFixture):
    """idx 737 — granular data remediation engine (built)."""

    def make_disposed_message(self):
        message = make_message(self.store, self.collection)
        self.store.record_disposition(OPERATOR, message["id"],
                                      "shredded", at=AT_BOUNDARY)
        return message

    def test_action_record_shape(self):
        message = make_message(self.store, self.collection)
        record = self.ext.record_remediation_action(
            OPERATOR, message["id"], "quarantine_copy", "THREAT-POL-1")
        self.assertEqual(
            set(record),
            {"id", "message_id", "action_label", "policy_ref",
             "executed_here", "created_by", "created_utc"})
        self.assertIs(record["executed_here"], False)
        self.assertNotIn("reference_stub", record)

    def test_unknown_action_rejected(self):
        message = make_message(self.store, self.collection)
        with self.assertRaises(ValidationError):
            self.ext.record_remediation_action(
                OPERATOR, message["id"], "nuke", "THREAT-POL-1")

    def test_recording_changes_no_core_record(self):
        message = make_message(self.store, self.collection)
        before_view = self.store.get_message(ADMIN, message["id"])
        before_enforcements = self.store.list_enforcements(ADMIN)
        self.ext.record_remediation_action(
            OPERATOR, message["id"], "revoke_access", "THREAT-POL-1",
            at=BEFORE_BOUNDARY)
        self.assertEqual(
            self.store.get_message(ADMIN, message["id"]), before_view)
        self.assertEqual(self.store.list_enforcements(ADMIN),
                         before_enforcements)

    def test_view_derives_current_state(self):
        message = make_message(self.store, self.collection)
        record = self.ext.record_remediation_action(
            OPERATOR, message["id"], "quarantine_copy", "THREAT-POL-1",
            at=BEFORE_BOUNDARY)
        view = self.ext.remediation_action_view(
            ADMIN, record["id"], now=BEFORE_BOUNDARY)
        self.assertEqual(view["current_retention_state"], "retained")
        self.assertIs(view["currently_actionable"], True)
        view = self.ext.remediation_action_view(
            ADMIN, record["id"], now=AFTER_BOUNDARY)
        self.assertEqual(view["current_retention_state"],
                         "disposition_eligible")
        self.assertIs(view["currently_actionable"], True)
        self.store.record_disposition(OPERATOR, message["id"],
                                      "shredded", at=AT_BOUNDARY)
        view = self.ext.remediation_action_view(
            ADMIN, record["id"], now=AFTER_BOUNDARY)
        self.assertEqual(view["current_retention_state"], "disposed")
        self.assertIs(view["currently_actionable"], False)
        stored = self.ext.list_remediation_actions(ADMIN)[0]
        self.assertNotIn("current_retention_state", stored)


class AlwaysEligibleExtensions(StorageExtensions):
    """Mutant: the eligibility seam reports every state eligible."""

    @staticmethod
    def _derive_remediation_eligibility(retention_state):
        return True


class TestRemediationEligibilityNegativeControl(ExtensionFixture):
    """The fresh mutation-verified negative control: the seam
    must refuse a remediation action for a disposed message."""

    def _disposed(self, ext_store):
        message = make_message(ext_store, self.collection)
        ext_store.record_disposition(OPERATOR, message["id"],
                                     "shredded", at=AT_BOUNDARY)
        return message

    def test_canonical_refusal_on_the_real_extension(self):
        message = self._disposed(self.store)
        with self.assertRaises(ValidationError):
            self.ext.record_remediation_action(
                OPERATOR, message["id"], "quarantine_copy",
                "THREAT-POL-1")
        self.assertEqual(self.ext.list_remediation_actions(ADMIN), [])

    def test_mutant_waves_the_same_action_through(self):
        mutant = AlwaysEligibleExtensions(self.store)
        message = self._disposed(self.store)
        record = mutant.record_remediation_action(
            OPERATOR, message["id"], "quarantine_copy", "THREAT-POL-1")
        self.assertEqual(record["message_id"], message["id"])
        # The canonical expectation ("refused") FAILS against the
        # mutant: the seam is what refuses, not incidental code.


class TestWorkloadConnectors(ExtensionFixture):
    """idx 738 — workload protection connectors (reference)."""

    def test_connector_shape_and_labels(self):
        connector = self.ext.record_workload_connector(
            OPERATOR, self.org["id"], "Microsoft 365",
            "m365 protection connector")
        self.assertEqual(
            set(connector),
            {"id", "org_id", "workload_label", "connector_label",
             "reference_stub", "connected_here", "protected_here",
             "created_by", "created_utc"})
        self.assertIs(connector["reference_stub"], True)
        self.assertIs(connector["connected_here"], False)
        self.assertIs(connector["protected_here"], False)

    def test_coverage_reports_and_derived_count(self):
        connector = self.ext.record_workload_connector(
            OPERATOR, self.org["id"], "Kubernetes",
            "k8s protection connector")
        coverage = self.ext.record_connector_coverage(
            OPERATOR, connector["id"], 140)
        self.assertIs(coverage["reference_stub"], True)
        self.assertIs(coverage["reference_transport"], True)
        self.assertIs(coverage["protected_here"], False)
        self.assertEqual(coverage["reported_protected_count"], 140)
        view = self.ext.workload_connector_view(ADMIN, connector["id"])
        self.assertEqual(view["coverage_count"], 1)
        self.assertNotIn(
            "coverage_count",
            self.ext.list_workload_connectors(ADMIN)[0])

    def test_connector_changes_no_core_record(self):
        before = self.store.summary(ADMIN)
        self.ext.record_workload_connector(
            OPERATOR, self.org["id"], "Endpoint",
            "endpoint protection connector")
        self.assertEqual(self.store.summary(ADMIN), before)


class TestConsolePanels(ExtensionFixture):
    """idx 739 — management console (built)."""

    def test_panel_shape(self):
        panel = self.ext.record_console_panel(
            ADMIN, self.org["id"], "Protection overview", "estate",
            ["backup status", "anomaly feed"])
        self.assertEqual(
            set(panel),
            {"id", "org_id", "panel_label", "scope_label",
             "widget_labels", "rendered_here",
             "created_by", "created_utc"})
        self.assertIs(panel["rendered_here"], False)
        self.assertNotIn("reference_stub", panel)

    def test_panel_definition_is_admin_plane(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_console_panel(
                OPERATOR, self.org["id"], "P", "estate", ["w"])
        denied = [e for e in self.audit.entries()
                  if e["action"] == "ext_console_panel_record:denied"]
        self.assertEqual(len(denied), 1)

    def test_console_view_derives_from_records(self):
        make_message(self.store, self.collection)
        self.ext.record_console_panel(
            ADMIN, self.org["id"], "Protection overview", "estate",
            ["backup status"])
        self.make_job()
        view = self.ext.console_view(ADMIN)
        self.assertEqual(view["core_summary"]["messages"], 1)
        self.assertEqual(view["panel_count"], 1)
        self.assertEqual(view["extension_counts"]["backup_jobs"], 1)
        self.assertEqual(view["extension_counts"]["console_panels"], 1)
        self.assertIs(view["rendered_here"], False)

    def test_widget_labels_validated(self):
        with self.assertRaises(ValidationError):
            self.ext.record_console_panel(
                ADMIN, self.org["id"], "P", "estate", [])
        with self.assertRaises(ValidationError):
            self.ext.record_console_panel(
                ADMIN, self.org["id"], "P", "estate", ["ok", ""])


class TestAutomationRules(ExtensionFixture):
    """idx 740 — SaaS operations automation (built)."""

    def test_rule_shape(self):
        rule = self.ext.record_automation_rule(
            ADMIN, self.org["id"], "Patch cycle", "monthly window",
            "apply vendor patches")
        self.assertEqual(
            set(rule),
            {"id", "org_id", "rule_label", "trigger_label",
             "action_label", "executed_here", "operated_here",
             "created_by", "created_utc"})
        self.assertIs(rule["executed_here"], False)
        self.assertIs(rule["operated_here"], False)
        self.assertNotIn("reference_stub", rule)

    def test_run_reports_derive_current_outcome(self):
        rule = self.ext.record_automation_rule(
            ADMIN, self.org["id"], "Upgrade train", "release channel",
            "apply vendor upgrades")
        view = self.ext.automation_rule_view(ADMIN, rule["id"])
        self.assertEqual(view["current_outcome_label"], "unreported")
        self.ext.record_automation_run(OPERATOR, rule["id"],
                                       "reported_applied")
        self.ext.record_automation_run(OPERATOR, rule["id"],
                                       "reported_skipped")
        view = self.ext.automation_rule_view(ADMIN, rule["id"])
        self.assertEqual(view["run_count"], 2)
        self.assertEqual(view["current_outcome_label"],
                         "reported_skipped")
        run = self.ext.list_automation_runs(ADMIN)[0]
        self.assertIs(run["executed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_automation_run(OPERATOR, rule["id"], "ran")


class TestSyncConditions(ExtensionFixture):
    """idx 741 — hybrid cloud synchronization engine (built)."""

    def test_condition_shape(self):
        condition = self.ext.record_sync_condition(
            OPERATOR, self.collection["id"], self.integration["id"],
            "estate-mirror")
        self.assertEqual(
            set(condition),
            {"id", "collection_id", "integration_id",
             "integration_kind", "condition_label",
             "synchronized_here", "created_by", "created_utc"})
        self.assertIs(condition["synchronized_here"], False)
        self.assertNotIn("reference_stub", condition)

    def test_outcomes_derive_current_state(self):
        condition = self.ext.record_sync_condition(
            OPERATOR, self.collection["id"], self.integration["id"],
            "estate-mirror")
        view = self.ext.sync_condition_view(ADMIN, condition["id"])
        self.assertEqual(view["current_outcome_label"], "unreported")
        self.assertIsNone(view["latest_reported_object_count"])
        self.ext.record_sync_outcome(OPERATOR, condition["id"],
                                     "reported_diverged", 40)
        self.ext.record_sync_outcome(OPERATOR, condition["id"],
                                     "reported_in_sync", 57)
        view = self.ext.sync_condition_view(ADMIN, condition["id"])
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["current_outcome_label"],
                         "reported_in_sync")
        self.assertEqual(view["latest_reported_object_count"], 57)
        stored = self.ext.list_sync_conditions(ADMIN)[0]
        self.assertNotIn("current_outcome_label", stored)
        outcome = self.ext.list_sync_outcomes(ADMIN)[0]
        self.assertIs(outcome["synchronized_here"], False)

    def test_unknown_outcome_and_count_rejected(self):
        condition = self.ext.record_sync_condition(
            OPERATOR, self.collection["id"], self.integration["id"],
            "estate-mirror")
        with self.assertRaises(ValidationError):
            self.ext.record_sync_outcome(OPERATOR, condition["id"],
                                         "synced", 1)
        with self.assertRaises(ValidationError):
            self.ext.record_sync_outcome(OPERATOR, condition["id"],
                                         "reported_in_sync", 2.5)

    def test_sync_changes_no_core_record(self):
        before = self.store.summary(ADMIN)
        condition = self.ext.record_sync_condition(
            OPERATOR, self.collection["id"], self.integration["id"],
            "estate-mirror")
        self.ext.record_sync_outcome(OPERATOR, condition["id"],
                                     "reported_in_sync", 3)
        self.assertEqual(self.store.summary(ADMIN), before)


class TestCrossCutting(ExtensionFixture):
    """Discipline pins over the whole extension surface."""

    def _exercise_everything(self):
        message = make_message(self.store, self.collection)
        job = self.make_job()
        self.ext.record_backup_outcome(OPERATOR, job["id"],
                                       "reported_succeeded")
        self.ext.record_recovery_report(OPERATOR, job["id"],
                                        "reported_restored")
        report = self.ext.record_anomaly_report(
            OPERATOR, self.collection["id"], "detector-7", 1, "low")
        self.ext.record_alert_dispatch(OPERATOR, report["id"], "queue")
        self.ext.record_remediation_action(
            OPERATOR, message["id"], "quarantine_copy", "THREAT-POL-1")
        connector = self.ext.record_workload_connector(
            OPERATOR, self.org["id"], "Endpoint", "endpoint connector")
        self.ext.record_connector_coverage(OPERATOR, connector["id"], 5)
        self.ext.record_console_panel(
            ADMIN, self.org["id"], "Overview", "estate", ["status"])
        rule = self.ext.record_automation_rule(
            ADMIN, self.org["id"], "Patch", "window", "patch")
        self.ext.record_automation_run(OPERATOR, rule["id"],
                                       "reported_applied")
        condition = self.ext.record_sync_condition(
            OPERATOR, self.collection["id"], self.integration["id"],
            "estate-mirror")
        self.ext.record_sync_outcome(OPERATOR, condition["id"],
                                     "reported_in_sync", 2)
        return job, report, connector, rule, condition

    def test_no_forbidden_key_anywhere(self):
        job, report, connector, rule, condition = \
            self._exercise_everything()
        surfaces = [
            self.ext.list_backup_jobs(ADMIN),
            self.ext.list_backup_outcomes(ADMIN),
            self.ext.list_recovery_reports(ADMIN),
            self.ext.backup_job_view(ADMIN, job["id"]),
            self.ext.list_anomaly_reports(ADMIN),
            self.ext.list_alert_dispatches(ADMIN),
            self.ext.anomaly_report_view(ADMIN, report["id"]),
            self.ext.list_remediation_actions(ADMIN),
            self.ext.list_workload_connectors(ADMIN),
            self.ext.list_connector_coverages(ADMIN),
            self.ext.workload_connector_view(ADMIN, connector["id"]),
            self.ext.list_console_panels(ADMIN),
            self.ext.console_view(ADMIN),
            self.ext.list_automation_rules(ADMIN),
            self.ext.list_automation_runs(ADMIN),
            self.ext.automation_rule_view(ADMIN, rule["id"]),
            self.ext.list_sync_conditions(ADMIN),
            self.ext.list_sync_outcomes(ADMIN),
            self.ext.sync_condition_view(ADMIN, condition["id"]),
            self.ext.extension_summary(ADMIN),
        ]
        for surface in surfaces:
            self.assertEqual(scan_forbidden(surface), [])

    def test_smuggled_kwargs_raise_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_backup_job(
                OPERATOR, self.collection["id"], self.integration["id"],
                "nightly", 1, 1, content=b"bytes")
        with self.assertRaises(TypeError):
            self.ext.record_anomaly_report(
                OPERATOR, self.collection["id"], "d", 1, "low",
                payload=b"bytes")
        with self.assertRaises(TypeError):
            self.ext.record_sync_condition(
                OPERATOR, self.collection["id"], self.integration["id"],
                "estate-mirror", key_material="material")

    def test_failed_operation_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.record_backup_job(
                OPERATOR, self.collection["id"], self.integration["id"],
                "nightly", -3, 10)
        job = self.make_job()
        self.assertEqual(job["id"], "bak-1")

    def test_viewer_writes_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_backup_job(
                VIEWER, self.collection["id"], self.integration["id"],
                "nightly", 1, 1)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "ext_backup_job_record:denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(self.ext.list_backup_jobs(ADMIN), [])

    def test_auditor_denied_every_extension_operation(self):
        job = self.make_job()
        with self.assertRaises(PermissionDenied):
            self.ext.list_backup_jobs(AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.backup_job_view(AUDITOR, job["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.record_anomaly_report(
                AUDITOR, self.collection["id"], "d", 1, "low")
        with self.assertRaises(PermissionDenied):
            self.ext.console_view(AUDITOR)
        # Audit review itself stays the auditor's, via the core.
        trail = self.store.audit_read(AUDITOR)
        self.assertGreater(trail["count"], 0)

    def test_audit_chain_verifies_after_extension_flow(self):
        self._exercise_everything()
        ok, first_bad = self.audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(first_bad)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_backup_job_record", actions)
        self.assertIn("ext_remediation_action_record", actions)
        self.assertIn("ext_sync_outcome_record", actions)

    def test_extension_summary_counts(self):
        self._exercise_everything()
        summary = self.ext.extension_summary(ADMIN)
        self.assertEqual(summary["backup_jobs"], 1)
        self.assertEqual(summary["anomaly_reports"], 1)
        self.assertEqual(summary["remediation_actions"], 1)
        self.assertEqual(summary["sync_outcomes"], 1)
        self.assertEqual(summary["console_panels"], 1)


if __name__ == "__main__":
    unittest.main()
