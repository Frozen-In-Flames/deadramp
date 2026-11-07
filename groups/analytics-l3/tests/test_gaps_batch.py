"""Final GAPS batch tests — Analytics L3-adjacent extension surface.

Traces to: GAPS.md "Group 3 — Analytics L3-adjacent (54 forks)", the
three entries still open at batch time (idx 23 alerts / monitoring,
idx 24 predictive ML remainder, idx 25 the bundled twelve Extended
families), each drafted ``stub-engine`` in gaps-batch/inventory.json
and shipped as a labeled reference implementation in
``analytics/extensions.py``; DECISION.md (batch pattern);
PLATFORM-LAYER.md decisions 2–3 (no build cryptography of its own);
UNION-SPEC.md High uplifts (AU-5 fail closed, AU-9 hash chain, AC-5
auditor role) as they bind the extension.
"""

import os
import tempfile
import unittest

from analytics_helpers import ADMIN, ANALYST, AUDITOR, VIEWER, make_store

from analytics.audit import AuditLog
from analytics.errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from analytics.extensions import (
    EXTENDED_FAMILY_CLAIM_COUNTS,
    AnalyticsExtensions,
)
from analytics.store import DatasetStore


def _break_log_file(log):
    """Replace a file-backed log's JSONL file with a directory of
    the same name, so the next append raises IsADirectoryError (an
    OSError) — the core AU-5 tests' deterministic trick."""
    if os.path.exists(log.path):
        os.remove(log.path)
    os.mkdir(log.path)


class TestAlertReferenceRecords(unittest.TestCase):
    """Idx 23 — alerts, monitoring & detection (reference)."""

    def setUp(self):
        self.store, self.dataset_id = make_store(audit=AuditLog())
        self.ext = AnalyticsExtensions(self.store)

    def test_rule_record_shape_and_labels(self):
        """Idx 23: a rule record is a labeled reference record —
        reference_stub True, monitoring_here False, no derived key."""
        rule = self.ext.create_alert_rule(
            "units mean watch", self.dataset_id, "units", "mean", "gt",
            25, ADMIN)
        self.assertEqual(
            set(rule),
            {"id", "name", "dataset_id", "column", "statistic", "op",
             "threshold", "reference_stub", "state", "monitoring_here",
             "created_by", "created_utc"})
        self.assertEqual(rule["id"], "alr-1")
        self.assertIs(rule["reference_stub"], True)
        self.assertEqual(rule["state"], "recorded_reference_only")
        self.assertIs(rule["monitoring_here"], False)

    def test_rule_validation_rejects_and_consumes_no_id(self):
        """Idx 23 / SI-10: bad column, statistic, op, or a bool
        threshold are rejected before id allocation."""
        with self.assertRaises(ValidationError):
            self.ext.create_alert_rule(
                "x", self.dataset_id, "nope", "mean", "gt", 1, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_alert_rule(
                "x", self.dataset_id, "units", "mode", "gt", 1, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_alert_rule(
                "x", self.dataset_id, "units", "mean", "near", 1, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_alert_rule(
                "x", self.dataset_id, "units", "mean", "gt", True, ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.create_alert_rule(
                "x", "ds-99", "units", "mean", "gt", 1, ADMIN)
        rule = self.ext.create_alert_rule(
            "ok", self.dataset_id, "units", "mean", "gt", 1, ADMIN)
        self.assertEqual(rule["id"], "alr-1")

    def test_evaluation_receipt_is_point_in_time_over_core_describe(self):
        """Idx 23: an evaluation receipt deterministically compares
        the core describe statistic (units mean = 30.0) against the
        recorded threshold at this moment; it is a receipt, not
        monitoring — the rule record itself gains no derived key."""
        rule = self.ext.create_alert_rule(
            "mean above 25", self.dataset_id, "units", "mean", "gt",
            25, ADMIN)
        receipt = self.ext.record_alert_evaluation(rule["id"], ANALYST)
        self.assertEqual(receipt["value"], 30.0)
        self.assertIs(receipt["breached"], True)
        self.assertEqual(receipt["method"],
                         "recorded_evaluation_over_core_describe")
        self.assertIs(receipt["reference_stub"], True)
        self.assertIs(receipt["monitoring_here"], False)
        rule2 = self.ext.create_alert_rule(
            "mean below 25", self.dataset_id, "units", "mean", "lt",
            25, ADMIN)
        receipt2 = self.ext.record_alert_evaluation(rule2["id"], ANALYST)
        self.assertIs(receipt2["breached"], False)

    def test_rule_view_derives_rollup_at_read(self):
        """Idx 23: evaluation count and last outcome are derived at
        read and never stored on the rule record."""
        rule = self.ext.create_alert_rule(
            "max watch", self.dataset_id, "units", "max", "ge", 50, ADMIN)
        view = self.ext.alert_rule_view(rule["id"], VIEWER)
        self.assertEqual(view["evaluation_count"], 0)
        self.assertIsNone(view["last_breached"])
        self.ext.record_alert_evaluation(rule["id"], ADMIN)
        view = self.ext.alert_rule_view(rule["id"], VIEWER)
        self.assertEqual(view["evaluation_count"], 1)
        self.assertIs(view["last_breached"], True)
        stored = self.ext._alert_rules[rule["id"]]
        self.assertNotIn("evaluation_count", stored)
        self.assertNotIn("last_breached", stored)

    def test_no_monitor_or_watch_method_on_surface(self):
        """Idx 23: the registry never monitors — no monitor, watch,
        or fire method exists on the extension surface."""
        for name in ("monitor", "watch", "fire_alert", "start_monitoring"):
            self.assertFalse(hasattr(self.ext, name), name)


class TestModelReferenceRecords(unittest.TestCase):
    """Idx 24 — predictive ML remainder (reference)."""

    def setUp(self):
        self.store, self.dataset_id = make_store(audit=AuditLog())
        self.ext = AnalyticsExtensions(self.store)

    def test_model_record_shape_and_labels(self):
        """Idx 24: a model record is a labeled reference record —
        nothing is trained or predicted here."""
        model = self.ext.register_model_reference(
            "churn model", "classification", ADMIN,
            dataset_id=self.dataset_id)
        self.assertEqual(
            set(model),
            {"id", "name", "model_kind", "dataset_id", "reference_stub",
             "state", "trained_here", "predicted_here", "created_by",
             "created_utc"})
        self.assertIs(model["reference_stub"], True)
        self.assertIs(model["trained_here"], False)
        self.assertIs(model["predicted_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_model_reference("x", "magic", ADMIN)

    def test_run_record_holds_reported_figures_verbatim(self):
        """Idx 24: a reported run stores its outcome and figures
        verbatim as reported; no figure is computed here."""
        model = self.ext.register_model_reference(
            "forecast", "forecasting", ADMIN)
        run = self.ext.record_model_run_reference(
            model["id"], "nightly run completed", ANALYST,
            reported_figures={"reported_accuracy": 0.91, "rows_scored": 1200})
        self.assertIs(run["executed"], False)
        self.assertIs(run["computed_here"], False)
        self.assertEqual(run["reported_figures"],
                         {"reported_accuracy": 0.91, "rows_scored": 1200})
        view = self.ext.model_view(model["id"], VIEWER)
        self.assertEqual(view["run_count"], 1)
        self.assertNotIn("run_count", self.ext._models[model["id"]])

    def test_reported_figures_reject_bools_and_non_objects(self):
        """Idx 24: reported figures are validated as data — bools
        are not numbers, and a non-object is rejected whole."""
        model = self.ext.register_model_reference(
            "m", "regression", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_model_run_reference(
                model["id"], "run", ADMIN, reported_figures={"x": True})
        with self.assertRaises(ValidationError):
            self.ext.record_model_run_reference(
                model["id"], "run", ADMIN, reported_figures=[1, 2])
        view = self.ext.model_view(model["id"], ADMIN)
        self.assertEqual(view["run_count"], 0)

    def test_no_train_or_predict_method_on_surface(self):
        """Idx 24: there is deliberately no train, predict, fit, or
        infer method on the extension surface."""
        for name in ("train", "train_model", "predict", "fit",
                     "fit_model", "infer", "run_inference"):
            self.assertFalse(hasattr(self.ext, name), name)


class TestBundleReferenceRecords(unittest.TestCase):
    """Idx 25 — the bundled twelve Extended families (reference)."""

    def setUp(self):
        self.store, self.dataset_id = make_store(audit=AuditLog())
        self.ext = AnalyticsExtensions(self.store)

    def test_family_vocabulary_is_the_entry_text(self):
        """Idx 25: the family vocabulary and sibling counts are the
        GAPS entry's own text — twelve families, KPI at its
        recorded zero."""
        self.assertEqual(len(EXTENDED_FAMILY_CLAIM_COUNTS), 12)
        self.assertEqual(EXTENDED_FAMILY_CLAIM_COUNTS["real_time_streaming"], 18)
        self.assertEqual(EXTENDED_FAMILY_CLAIM_COUNTS["collaboration"], 17)
        self.assertEqual(EXTENDED_FAMILY_CLAIM_COUNTS["proprietary_connectors"], 17)
        self.assertEqual(EXTENDED_FAMILY_CLAIM_COUNTS["kpi"], 0)

    def test_family_reference_record_shape_and_labels(self):
        """Idx 25: one reference record per family, labeled, with
        the family's recorded sibling count held as data."""
        ref = self.ext.register_extended_family_reference("governance", ADMIN)
        self.assertEqual(
            set(ref),
            {"id", "family", "siblings_claiming", "reference_stub",
             "state", "implemented_here", "created_by", "created_utc"})
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["implemented_here"], False)
        self.assertEqual(ref["siblings_claiming"], 11)

    def test_family_registration_unique_and_validated(self):
        """Idx 25: a family registers once; an unknown family is
        rejected and consumes no id."""
        with self.assertRaises(ValidationError):
            self.ext.register_extended_family_reference("teleportation", ADMIN)
        first = self.ext.register_extended_family_reference("archiving", ADMIN)
        self.assertEqual(first["id"], "efr-1")
        with self.assertRaises(ValidationError):
            self.ext.register_extended_family_reference("archiving", ADMIN)

    def test_family_report_holds_outcome_verbatim(self):
        """Idx 25: a family report stores its outcome and reported
        figures verbatim; nothing is performed or computed here.
        KPI values arrive in exactly this reported form."""
        ref = self.ext.register_extended_family_reference("kpi", ADMIN)
        report = self.ext.record_extended_family_report(
            ref["id"], "monthly KPI pack received", ANALYST,
            reported_figures={"reported_uptime_pct": 99.9})
        self.assertIs(report["performed_here"], False)
        self.assertIs(report["computed_here"], False)
        self.assertEqual(report["reported_figures"],
                         {"reported_uptime_pct": 99.9})
        view = self.ext.extended_family_view(ref["id"], VIEWER)
        self.assertEqual(view["report_count"], 1)
        self.assertNotIn("report_count", self.ext._family_refs[ref["id"]])

    def test_stream_batches_are_reported_receipts_only(self):
        """Idx 25 (streaming): batch receipts carry
        reference_transport and ingest nothing — the core store's
        dataset set is unchanged after recording them."""
        ref = self.ext.register_extended_family_reference(
            "real_time_streaming", ADMIN)
        before = [d["id"] for d in self.store.list()]
        self.ext.record_stream_batch_reference(ref["id"], 4, ANALYST)
        batch = self.ext.record_stream_batch_reference(ref["id"], 3, ANALYST)
        self.assertIs(batch["reference_stub"], True)
        self.assertIs(batch["reference_transport"], True)
        self.assertIs(batch["ingested_here"], False)
        self.assertIs(batch["streamed_here"], False)
        self.assertEqual([d["id"] for d in self.store.list()], before)
        view = self.ext.extended_family_view(ref["id"], VIEWER)
        self.assertEqual(view["batch_count"], 2)
        self.assertEqual(view["reported_rows_total"], 7)

    def test_connector_syncs_are_reported_receipts_only(self):
        """Idx 25 (connectors): sync receipts carry
        reference_transport and connect nothing."""
        ref = self.ext.register_extended_family_reference(
            "proprietary_connectors", ADMIN)
        sync = self.ext.record_connector_sync_reference(ref["id"], 5, ANALYST)
        self.ext.record_connector_sync_reference(ref["id"], 2, ANALYST)
        self.assertIs(sync["reference_transport"], True)
        self.assertIs(sync["connected_here"], False)
        self.assertIs(sync["ingested_here"], False)
        view = self.ext.extended_family_view(ref["id"], VIEWER)
        self.assertEqual(view["sync_count"], 2)
        self.assertEqual(view["reported_rows_total"], 7)

    def test_receipts_bind_to_their_own_family(self):
        """Idx 25: a stream batch cannot bind to the governance
        family reference, nor a connector sync to the streaming
        one — the receipt forms are family-specific."""
        gov = self.ext.register_extended_family_reference("governance", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_stream_batch_reference(gov["id"], 1, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_connector_sync_reference(gov["id"], 1, ADMIN)

    def test_bundle_view_derives_rollups_at_read(self):
        """Idx 25: the bundle view derives per-family counts and
        the reported-rows total at read; nothing is stored."""
        stream = self.ext.register_extended_family_reference(
            "real_time_streaming", ADMIN)
        conn = self.ext.register_extended_family_reference(
            "proprietary_connectors", ADMIN)
        self.ext.record_stream_batch_reference(stream["id"], 4, ADMIN)
        self.ext.record_connector_sync_reference(conn["id"], 3, ADMIN)
        view = self.ext.extended_bundle_view(VIEWER)
        self.assertEqual(view["registered_family_count"], 2)
        self.assertEqual(view["reported_rows_total"], 7)
        by_family = {f["family"]: f for f in view["families"]}
        self.assertEqual(by_family["real_time_streaming"]["batch_count"], 1)
        self.assertEqual(by_family["proprietary_connectors"]["sync_count"], 1)


class _FirstCountEchoExtensions(AnalyticsExtensions):
    """Mutant: the reported-rows seam echoes the first count."""

    @staticmethod
    def _sum_reported_counts(counts):
        return counts[0] if counts else 0


class TestReportedRowsNegativeControl(unittest.TestCase):
    """Fresh negative control: the reported-rows total seam.

    Canonical expectation, stated once: receipts reporting 4 and 3
    rows derive a reported_rows_total of 7 — the total is the SUM
    of the recorded reports. The real implementation meets it; a
    first-count-echo mutant is rejected by it.
    """

    EXPECTED = 7

    def _drive(self, ext):
        ref = ext.register_extended_family_reference(
            "real_time_streaming", ADMIN)
        ext.record_stream_batch_reference(ref["id"], 4, ADMIN)
        ext.record_stream_batch_reference(ref["id"], 3, ADMIN)
        return ext.extended_family_view(ref["id"], ADMIN)

    def test_canonical_expectation_holds_for_seam(self):
        """NC: the seam itself sums the recorded reports."""
        self.assertEqual(
            AnalyticsExtensions._sum_reported_counts([4, 3]), self.EXPECTED)
        self.assertEqual(AnalyticsExtensions._sum_reported_counts([]), 0)

    def test_real_implementation_meets_expectation(self):
        """NC: the real family view derives the summed total."""
        store, _ds = make_store(audit=AuditLog())
        view = self._drive(AnalyticsExtensions(store))
        self.assertEqual(view["reported_rows_total"], self.EXPECTED)

    def test_first_count_echo_mutant_is_rejected(self):
        """NC: the echo mutant's total (4) fails the canonical
        expectation — asserting equality must raise AssertionError."""
        store, _ds = make_store(audit=AuditLog())
        view = self._drive(_FirstCountEchoExtensions(store))
        self.assertEqual(view["reported_rows_total"], 4)
        with self.assertRaises(AssertionError):
            self.assertEqual(view["reported_rows_total"], self.EXPECTED)


class TestHighApparatusBindsExtension(unittest.TestCase):
    """The High uplifts as they bind the extension: AC-5 auditor
    separation, AU-9 chained audit, AU-5 fail-closed writes."""

    def setUp(self):
        self.audit = AuditLog()
        self.store, self.dataset_id = make_store(audit=self.audit)
        self.ext = AnalyticsExtensions(self.store)

    def test_auditor_denied_mutation_and_view_denials_audited(self):
        """AC-5: the auditor holds audit_read only, so every
        extension operation is denied — and the denial itself is
        recorded on the chained log with the :denied suffix."""
        with self.assertRaises(PermissionDenied):
            self.ext.create_alert_rule(
                "x", self.dataset_id, "units", "mean", "gt", 1, AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.register_extended_family_reference("kpi", AUDITOR)
        rule = self.ext.create_alert_rule(
            "ok", self.dataset_id, "units", "mean", "gt", 1, ADMIN)
        with self.assertRaises(PermissionDenied):
            self.ext.alert_rule_view(rule["id"], AUDITOR)
        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertEqual(len(denied), 3)
        self.assertTrue(all(e["actor"] == "dana" for e in denied))

    def test_auditor_core_audit_duty_still_works(self):
        """AC-5 / AU-6 / AU-9: after extension activity (including
        audited denials), the auditor's own duty — reading and
        verifying the core audit log — is intact, and every
        extension entry sits on the hash chain."""
        self.ext.register_model_reference("m", "regression", ADMIN)
        with self.assertRaises(PermissionDenied):
            self.ext.register_model_reference("m2", "regression", AUDITOR)
        entries = self.audit.query(actor="alice")
        self.assertTrue(any(e["action"] == "ext_register_model_reference"
                            for e in entries))
        self.assertEqual(self.audit.verify_chain(), (True, None))
        ext_entries = [e for e in self.audit.entries()
                       if e["action"].startswith("ext_")]
        self.assertTrue(ext_entries)
        for entry in ext_entries:
            self.assertIn("seq", entry)
            self.assertIn("prev_hash", entry)
            self.assertIn("hash", entry)

    def test_extension_write_fails_closed_on_audit_failure(self):
        """AU-5: when the chained log's write fails, an extension
        registration raises AuditWriteError, stores no record, and
        consumes no id — mirroring the core store's ingest
        rollback."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = DatasetStore(audit=audit)
            ext = AnalyticsExtensions(store)
            first = ext.register_model_reference("m1", "regression", ADMIN)
            self.assertEqual(first["id"], "mdl-1")
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                ext.register_model_reference("m2", "regression", ADMIN)
            with self.assertRaises(NotFoundError):
                ext.model_view("mdl-2", ADMIN)
            self.assertEqual(audit.verify_chain(), (True, None))
            os.rmdir(path)
            second = ext.register_model_reference("m2", "regression", ADMIN)
            self.assertEqual(second["id"], "mdl-2")
            self.assertEqual(audit.verify_chain(), (True, None))


if __name__ == "__main__":
    unittest.main()
