"""Final GAPS batch tests, second unit — Collaboration L3-adjacent
remainder addition.

Traces to: GAPS.md section "Remainder Addition — Collaboration
L3-adjacent (+1 fork)", inventory idx 656 (see
``../BATCH-ADDITION.md`` for the disposition); gaps-batch/DECISION.md
(batch pattern); ADDENDUM.md §2/§5 (the fork's closing sentence names
an agency–vendor collaborative continuous-monitoring arrangement with
no family in this taxonomy). Pins the extension surface of
``collab/extensions_addition.py``: the labeled reference
implementation of the continuous-monitoring service — arrangement
records and monitoring-report records carrying ``reference_stub:
True`` and ``monitored_here: False``, with counts and the current
reported outcome derived at read. Includes this unit's fresh
negative control: the latest-report derivation
(``CollabExtensionsAddition._latest_report_label``), three-legged in
``TestNegativeControlLatestReport`` and mutation-verified live
against the real module (recorded in tests/README.md).
"""

import copy
import unittest

from collab_helpers import (
    AUDITOR,
    MEMBER,
    OUTSIDER,
    VIEWER,
    make_store,
    share_sample_file,
)
from collab.errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from collab.extensions_addition import (
    CADENCE_LABELS,
    REPORT_LABELS,
    CollabExtensionsAddition,
)

ARRANGEMENT_KEYS = {
    "id", "workspace_id", "arrangement_ref", "agency_ref", "vendor_ref",
    "cadence_label", "reference_stub", "state", "monitored_here",
    "created_by", "created_utc",
}
REPORT_KEYS = {
    "id", "workspace_id", "arrangement_id", "period_label",
    "outcome_label", "findings_reported", "reference_stub",
    "monitored_here", "created_by", "created_utc",
}

FORBIDDEN_KEY_PARTS = ("score", "grade", "rating", "percent", "rank")


def assert_no_score_keys(case, node, path="root"):
    """Recursive scan: no computed-score-shaped key anywhere."""
    if isinstance(node, dict):
        for key, value in node.items():
            for part in FORBIDDEN_KEY_PARTS:
                case.assertNotIn(
                    part, str(key).lower(),
                    "forbidden key part %r at %s.%s" % (part, path, key))
            assert_no_score_keys(case, value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            assert_no_score_keys(case, value, "%s[%d]" % (path, index))


class AdditionFixture(unittest.TestCase):
    """Canonical fixture: core store + workspace (MEMBER owns, VIEWER
    is a member) and the second-unit extension wrapper."""

    def setUp(self):
        self.store, self.ws = make_store()
        self.ext = CollabExtensionsAddition(self.store)

    def register(self, ref="conmon-1", cadence="quarterly", actor=MEMBER):
        return self.ext.register_monitoring_arrangement(
            actor, self.ws, ref, "agency-ref-1", "vendor-ref-1", cadence)

    def report(self, arrangement_id, period="2026-Q1",
               outcome="reported_current", findings=0, actor=MEMBER):
        return self.ext.record_monitoring_report(
            actor, self.ws, arrangement_id, period, outcome,
            findings_reported=findings)


class TestArrangements(AdditionFixture):
    """Idx 656: arrangement reference records — shape and labels."""

    def test_arrangement_shape_and_labels(self):
        record = self.register()
        self.assertEqual(set(record), ARRANGEMENT_KEYS)
        self.assertEqual(record["id"], "mon-1")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["monitored_here"], False)
        self.assertEqual(record["cadence_label"], "quarterly")
        for label in CADENCE_LABELS:
            self.assertIn(label, CADENCE_LABELS)

    def test_ids_sequential_and_failed_ops_consume_none(self):
        with self.assertRaises(ValidationError):
            self.register(cadence="weekly")
        with self.assertRaises(ValidationError):
            self.register(ref="")
        first = self.register()
        second = self.register(ref="conmon-2")
        self.assertEqual((first["id"], second["id"]), ("mon-1", "mon-2"))

    def test_list_and_get(self):
        self.register()
        self.register(ref="conmon-2")
        listed = self.ext.list_monitoring_arrangements(MEMBER, self.ws)
        self.assertEqual([r["id"] for r in listed], ["mon-1", "mon-2"])
        got = self.ext.get_monitoring_arrangement(MEMBER, self.ws, "mon-2")
        self.assertEqual(got["arrangement_ref"], "conmon-2")
        with self.assertRaises(NotFoundError):
            self.ext.get_monitoring_arrangement(MEMBER, self.ws, "mon-99")

    def test_arrangement_scoped_to_its_workspace(self):
        record = self.register()
        other = self.store.create_workspace("other-room", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.get_monitoring_arrangement(MEMBER, other["id"],
                                                record["id"])


class TestReports(AdditionFixture):
    """Idx 656: monitoring-report records — verbatim reported values."""

    def test_report_shape_and_labels(self):
        arrangement = self.register()
        record = self.report(arrangement["id"], findings=3)
        self.assertEqual(set(record), REPORT_KEYS)
        self.assertEqual(record["id"], "monr-1")
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["monitored_here"], False)
        self.assertEqual(record["findings_reported"], 3)
        self.assertEqual(record["outcome_label"], "reported_current")
        for label in REPORT_LABELS:
            self.assertIn(label, REPORT_LABELS)

    def test_report_validation(self):
        arrangement = self.register()
        with self.assertRaises(ValidationError):
            self.report(arrangement["id"], outcome="all_clear")
        with self.assertRaises(ValidationError):
            self.report(arrangement["id"], findings=-1)
        with self.assertRaises(ValidationError):
            self.report(arrangement["id"], findings=1.5)
        with self.assertRaises(ValidationError):
            self.report(arrangement["id"], findings=True)
        with self.assertRaises(ValidationError):
            self.report(arrangement["id"], period="")
        # No id was consumed by the failures.
        record = self.report(arrangement["id"])
        self.assertEqual(record["id"], "monr-1")
        self.assertEqual(record["findings_reported"], 0)

    def test_report_requires_existing_arrangement(self):
        with self.assertRaises(NotFoundError):
            self.report("mon-99")

    def test_no_content_can_be_smuggled(self):
        arrangement = self.register()
        with self.assertRaises(TypeError):
            self.ext.record_monitoring_report(
                MEMBER, self.ws, arrangement["id"], "2026-Q1",
                "reported_current", report_text="raw findings")
        with self.assertRaises(TypeError):
            self.ext.register_monitoring_arrangement(
                MEMBER, self.ws, "conmon-x", "agency-ref-1",
                "vendor-ref-1", "monthly", telemetry="stream")


class TestViews(AdditionFixture):
    """Idx 656: derived-at-read views — counts and latest outcome."""

    def test_view_derives_counts_total_and_current(self):
        arrangement = self.register()
        self.report(arrangement["id"], period="2026-Q1",
                    outcome="reported_findings", findings=2)
        self.report(arrangement["id"], period="2026-Q2",
                    outcome="reported_current", findings=0)
        self.report(arrangement["id"], period="2026-Q3",
                    outcome="reported_delayed", findings=5)
        view = self.ext.monitoring_view(MEMBER, self.ws, arrangement["id"])
        self.assertEqual(view["report_count"], 3)
        self.assertEqual(view["reports_by_outcome"]["reported_findings"], 1)
        self.assertEqual(view["reports_by_outcome"]["reported_current"], 1)
        self.assertEqual(view["reports_by_outcome"]["reported_delayed"], 1)
        self.assertEqual(view["reports_by_outcome"]["reported_clean"], 0)
        # The total is a sum of the recorded reports' reported counts.
        self.assertEqual(view["findings_reported_total"], 7)
        # First and latest outcomes differ by design, so this pin
        # discriminates the latest-report derivation.
        self.assertEqual(view["current_outcome"], "reported_delayed")
        self.assertIs(view["derived"], True)
        # The stored record carries none of the derived keys.
        stored = self.ext.get_monitoring_arrangement(
            MEMBER, self.ws, arrangement["id"])
        self.assertEqual(set(stored), ARRANGEMENT_KEYS)

    def test_view_with_no_reports(self):
        arrangement = self.register()
        view = self.ext.monitoring_view(MEMBER, self.ws, arrangement["id"])
        self.assertEqual(view["report_count"], 0)
        self.assertEqual(view["findings_reported_total"], 0)
        self.assertEqual(view["current_outcome"], "recorded")

    def test_summary_derives_workspace_counts(self):
        first = self.register()
        second = self.register(ref="conmon-2")
        self.report(first["id"], outcome="reported_clean", findings=1)
        self.report(second["id"], outcome="reported_delayed", findings=4)
        self.report(second["id"], period="2026-Q2",
                    outcome="reported_delayed", findings=2)
        summary = self.ext.monitoring_summary(MEMBER, self.ws)
        self.assertEqual(summary["arrangement_count"], 2)
        self.assertEqual(summary["report_count"], 3)
        self.assertEqual(summary["reports_by_outcome"]["reported_delayed"], 2)
        self.assertEqual(summary["findings_reported_total"], 7)
        self.assertIs(summary["derived"], True)

    def test_no_score_keys_anywhere(self):
        arrangement = self.register()
        report = self.report(arrangement["id"], findings=2)
        view = self.ext.monitoring_view(MEMBER, self.ws, arrangement["id"])
        summary = self.ext.monitoring_summary(MEMBER, self.ws)
        for node in (arrangement, report, view, summary):
            assert_no_score_keys(self, node)


class TestCoreUnchanged(AdditionFixture):
    """Idx 656: the reference surface changes no core record."""

    def test_register_and_report_change_no_core_record(self):
        shared = share_sample_file(self.store, self.ws)
        workspace_before = copy.deepcopy(
            self.store.get_workspace(self.ws, MEMBER))
        file_before = copy.deepcopy(
            self.store.get_file(self.ws, shared["id"], MEMBER))
        arrangement = self.register()
        self.report(arrangement["id"], outcome="reported_findings",
                    findings=2)
        self.assertEqual(self.store.get_workspace(self.ws, MEMBER),
                         workspace_before)
        self.assertEqual(
            self.store.get_file(self.ws, shared["id"], MEMBER), file_before)


class TestAccessDiscipline(AdditionFixture):
    """High apparatus on this surface: membership boundary, RBAC,
    separated auditor, hash-chained fail-closed audit."""

    def test_auditor_denied_every_operation(self):
        arrangement = self.register()
        with self.assertRaises(PermissionDenied):
            self.register(actor=AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.get_monitoring_arrangement(AUDITOR, self.ws,
                                                arrangement["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.monitoring_view(AUDITOR, self.ws, arrangement["id"])
        with self.assertRaises(PermissionDenied):
            self.report(arrangement["id"], actor=AUDITOR)
        # The auditor's core duty is untouched: the chain verifies.
        self.assertEqual(self.store.audit.verify_chain(), (True, None))

    def test_outsider_denied(self):
        arrangement = self.register()
        with self.assertRaises(PermissionDenied):
            self.ext.monitoring_view(OUTSIDER, self.ws, arrangement["id"])
        with self.assertRaises(PermissionDenied):
            self.register(actor=OUTSIDER)

    def test_viewer_reads_but_write_denied_and_audited(self):
        arrangement = self.register()
        view = self.ext.monitoring_view(VIEWER, self.ws, arrangement["id"])
        self.assertEqual(view["id"], arrangement["id"])
        with self.assertRaises(PermissionDenied):
            self.register(actor=VIEWER)
        denied = [e for e in self.store.audit.entries()
                  if e["action"] ==
                  "exta_monitoring_arrangement_register:denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")

    def test_mutations_on_hash_chained_log(self):
        arrangement = self.register()
        self.report(arrangement["id"])
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_monitoring_arrangement_register", actions)
        self.assertIn("exta_monitoring_report_record", actions)
        self.assertEqual(self.store.audit.verify_chain(), (True, None))

    def test_audit_failure_fails_closed(self):
        original = self.store.audit.record

        def boom(*args, **kwargs):
            raise AuditWriteError("audit write failed")

        self.store.audit.record = boom
        try:
            with self.assertRaises(AuditWriteError):
                self.register()
        finally:
            self.store.audit.record = original
        self.assertEqual(
            self.ext.list_monitoring_arrangements(MEMBER, self.ws), [])
        record = self.register()
        self.assertEqual(record["id"], "mon-1")


class EarliestReportMutant(CollabExtensionsAddition):
    """Mutant: the current outcome reads the EARLIEST report."""

    @staticmethod
    def _latest_report_label(reports):
        if not reports:
            return "recorded"
        return reports[0]["outcome_label"]


class TestNegativeControlLatestReport(AdditionFixture):
    """Fresh negative control: the latest-report derivation. The
    traced claim is that the current reported outcome follows the
    latest recorded report, so a superseding report changes what
    the arrangement reads as current."""

    def _two_reports(self, ext):
        arrangement = ext.register_monitoring_arrangement(
            MEMBER, self.ws, "conmon-nc", "agency-ref-1", "vendor-ref-1",
            "quarterly")
        ext.record_monitoring_report(
            MEMBER, self.ws, arrangement["id"], "2026-Q1",
            "reported_findings", findings_reported=2)
        ext.record_monitoring_report(
            MEMBER, self.ws, arrangement["id"], "2026-Q2",
            "reported_current", findings_reported=0)
        return arrangement

    def test_canonical_latest_label_wins(self):
        arrangement = self._two_reports(self.ext)
        view = self.ext.monitoring_view(MEMBER, self.ws, arrangement["id"])
        self.assertEqual(view["current_outcome"], "reported_current")

    def test_mutant_reads_earliest(self):
        mutant = EarliestReportMutant(self.store)
        arrangement = self._two_reports(mutant)
        view = mutant.monitoring_view(MEMBER, self.ws, arrangement["id"])
        self.assertEqual(view["current_outcome"], "reported_findings")

    def test_mutant_outcome_fails_canonical_expectation(self):
        mutant = EarliestReportMutant(self.store)
        arrangement = self._two_reports(mutant)
        view = mutant.monitoring_view(MEMBER, self.ws, arrangement["id"])
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_outcome"], "reported_current")


if __name__ == "__main__":
    unittest.main()
