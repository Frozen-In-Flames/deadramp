"""Final GAPS batch tests, second unit — Data Management L1.

Traces to: the two Extended functions registered by this group's
remainder addition fork (DevResults) in GAPS.md under "Remainder
Addition — Data Management L1 (+1 fork)", disposed in
../BATCH-ADDITION.md — M&E / results-management platform functions
(built, records form) and data-capture tooling & collection
instruments (built, records form) — plus this unit's fresh negative
control: the latest-report seam in ``datamgmt.extensions_addition``
(TestLatestReportNegativeControl).

Every test pins the honesty bound on its face: nothing in this
surface measures progress or collects programme data, no record
shape can hold a response value or dataset content, and every
figure in a summary is either a count of this module's own records
or a figure stored verbatim as reported.
"""

import unittest

from datamgmt.audit import AuditLog
from datamgmt.errors import NotFoundError, PermissionDenied, ValidationError
from datamgmt.extensions_addition import DataMgmtExtensionsAddition
from datamgmt.store import DataMgmtStore

from datamgmt_helpers import ADMIN, STEWARD, VIEWER

FORBIDDEN_KEYS = {
    "content", "payload", "response", "response_value", "answer",
    "answers", "record", "records", "row", "rows", "value",
    "respondent", "subject", "participant", "name_value",
}


def results_store():
    """Fresh store + a partner-results dataset + a field-reports source."""
    audit = AuditLog()
    store = DataMgmtStore(audit=audit)
    dataset = store.create_dataset(
        "Partner Activity Results",
        "Partner-reported activity results",
        STEWARD,
        classification="internal",
        tags=["results", "partners"],
        schema=[
            {"name": "indicator", "type": "string", "required": True,
             "sensitive": False},
            {"name": "value", "type": "number", "required": True,
             "sensitive": False},
        ],
    )
    source = store.register_source(
        "field-reports", "manual", STEWARD, location="partners.internal"
    )
    return store, audit, dataset, source


def make_framework(ext, dataset, actor=STEWARD):
    return ext.define_results_framework(
        "Partner Results FY26", "prog-partners", actor,
        dataset_id=dataset["id"],
    )


def make_indicator(ext, framework, actor=STEWARD):
    return ext.register_indicator(
        framework["id"], "Households reached", actor,
        unit_label="households", baseline_reported=1200,
        target_reported=5000,
    )


def make_ingestion(store, dataset, source, actor=STEWARD, count=1200,
                   status="completed"):
    return store.record_ingestion(
        dataset["id"], source["id"], actor, mode="full",
        record_count=count, checksum="deadbeef", status=status,
    )


def walk(obj):
    """Yield every (key, value) pair in a nested record/view."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key, value
            yield from walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


class TestResultsFrameworks(unittest.TestCase):
    """GAPS idx 665 — frameworks are definitions, never measurements."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = results_store()
        self.ext = DataMgmtExtensionsAddition(self.store)

    def test_define_framework_shape_and_labels(self):
        framework = make_framework(self.ext, self.dataset)
        self.assertEqual(framework["id"], "rfw-1")
        self.assertEqual(framework["program_ref"], "prog-partners")
        self.assertEqual(framework["dataset_id"], self.dataset["id"])
        self.assertIs(framework["measured_here"], False)
        self.assertIs(framework["values_held"], False)
        # The stored record carries no count, total, or status: the
        # key set is pinned so no derived figure can creep in.
        self.assertEqual(
            set(framework),
            {"id", "name", "program_ref", "dataset_id", "measured_here",
             "values_held", "created_by", "created_utc"},
        )

    def test_define_framework_unknown_dataset_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.define_results_framework(
                "Ghost", "prog-ghost", STEWARD, dataset_id="ds-99")
        framework = make_framework(self.ext, self.dataset)
        self.assertEqual(framework["id"], "rfw-1")

    def test_define_framework_unbound_is_allowed(self):
        framework = self.ext.define_results_framework(
            "Standalone", "prog-solo", STEWARD)
        self.assertIsNone(framework["dataset_id"])

    def test_define_framework_viewer_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.define_results_framework(
                "Nope", "prog-nope", VIEWER, dataset_id=self.dataset["id"])
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("exta_framework_define:denied", actions)
        self.assertEqual(self.ext.list_results_frameworks(actor=ADMIN), [])


class TestIndicators(unittest.TestCase):
    """GAPS idx 665 — indicators are definitions with declared terms."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = results_store()
        self.ext = DataMgmtExtensionsAddition(self.store)
        self.framework = make_framework(self.ext, self.dataset)

    def test_register_indicator_shape_and_declared_terms(self):
        indicator = make_indicator(self.ext, self.framework)
        self.assertEqual(indicator["id"], "ind-1")
        self.assertEqual(indicator["framework_id"], self.framework["id"])
        self.assertEqual(indicator["unit_label"], "households")
        self.assertEqual(indicator["baseline_reported"], 1200)
        self.assertEqual(indicator["target_reported"], 5000)
        self.assertIs(indicator["measured_here"], False)

    def test_register_indicator_duplicate_name_rejected(self):
        make_indicator(self.ext, self.framework)
        with self.assertRaises(ValidationError):
            make_indicator(self.ext, self.framework)
        self.assertEqual(
            len(self.ext.list_indicators(self.framework["id"], ADMIN)), 1)

    def test_register_indicator_unknown_framework(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_indicator("rfw-99", "X", STEWARD)

    def test_register_indicator_bool_figure_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_indicator(
                self.framework["id"], "Bad", STEWARD,
                baseline_reported=True)


class TestProgressReports(unittest.TestCase):
    """GAPS idx 665 — progress arrives as reports, bound to core records."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = results_store()
        self.ext = DataMgmtExtensionsAddition(self.store)
        self.framework = make_framework(self.ext, self.dataset)
        self.indicator = make_indicator(self.ext, self.framework)
        self.ingestion = make_ingestion(self.store, self.dataset,
                                        self.source)

    def test_record_progress_report_shape_and_labels(self):
        report = self.ext.record_progress_report(
            self.indicator["id"], self.ingestion["id"],
            "reported_progressing", STEWARD, value_reported=2750)
        self.assertEqual(report["id"], "prg-1")
        self.assertEqual(report["ingestion_id"], self.ingestion["id"])
        self.assertEqual(report["value_reported"], 2750)
        self.assertIs(report["measured_here"], False)
        self.assertIs(report["computed_here"], False)

    def test_record_progress_report_cross_dataset_rejected(self):
        other = self.store.create_dataset(
            "Other Results", "Unrelated", STEWARD, schema=[])
        foreign = make_ingestion(self.store, other, self.source)
        with self.assertRaises(ValidationError):
            self.ext.record_progress_report(
                self.indicator["id"], foreign["id"],
                "reported_progressing", STEWARD)
        self.assertEqual(self.ext.list_progress_reports(
            self.indicator["id"], ADMIN), [])

    def test_record_progress_report_duplicate_binding_rejected(self):
        self.ext.record_progress_report(
            self.indicator["id"], self.ingestion["id"],
            "reported_progressing", STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.record_progress_report(
                self.indicator["id"], self.ingestion["id"],
                "reported_on_track", STEWARD)

    def test_record_progress_report_bad_outcome_and_bool_value(self):
        with self.assertRaises(ValidationError):
            self.ext.record_progress_report(
                self.indicator["id"], self.ingestion["id"],
                "on_track", STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.record_progress_report(
                self.indicator["id"], self.ingestion["id"],
                "reported_progressing", STEWARD, value_reported=False)

    def test_record_progress_report_viewer_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_progress_report(
                self.indicator["id"], self.ingestion["id"],
                "reported_progressing", VIEWER)


class TestResultsSummary(unittest.TestCase):
    """GAPS idx 665 — the summary derives at read and stores nothing."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = results_store()
        self.ext = DataMgmtExtensionsAddition(self.store)
        self.framework = make_framework(self.ext, self.dataset)
        self.indicator = make_indicator(self.ext, self.framework)

    def test_summary_derives_counts_latest_and_core_total(self):
        first = make_ingestion(self.store, self.dataset, self.source,
                               count=1200)
        second = make_ingestion(self.store, self.dataset, self.source,
                                count=800)
        failed = make_ingestion(self.store, self.dataset, self.source,
                                count=50, status="failed")
        self.ext.record_progress_report(
            self.indicator["id"], first["id"], "reported_progressing",
            STEWARD, value_reported=1900)
        self.ext.record_progress_report(
            self.indicator["id"], second["id"], "reported_on_track",
            STEWARD, value_reported=2750)
        summary = self.ext.results_summary(self.framework["id"], ADMIN)
        self.assertEqual(summary["indicators"], 1)
        self.assertEqual(summary["progress_reports"], 2)
        self.assertEqual(summary["reports_by_outcome"],
                         {"reported_progressing": 1, "reported_on_track": 1})
        # Latest = the most recent report, not the first.
        self.assertEqual(summary["latest_outcome"], "reported_on_track")
        self.assertEqual(summary["latest_value_reported"], 2750)
        # Core provenance counts completed ingestions only.
        self.assertEqual(summary["total_records"], 2000)
        self.assertIs(summary["measured_here"], False)
        self.assertIs(summary["computed_here"], False)
        self.assertIs(summary["values_held"], False)
        self.assertNotEqual(failed["id"], second["id"])

    def test_summary_empty_framework(self):
        summary = self.ext.results_summary(self.framework["id"], ADMIN)
        self.assertEqual(summary["indicators"], 1)
        self.assertEqual(summary["progress_reports"], 0)
        self.assertEqual(summary["reports_by_outcome"], {})
        self.assertIsNone(summary["latest_outcome"])
        self.assertIsNone(summary["latest_value_reported"])
        self.assertEqual(summary["total_records"], 0)

    def test_summary_unbound_framework_has_no_core_total(self):
        framework = self.ext.define_results_framework(
            "Standalone", "prog-solo", STEWARD)
        summary = self.ext.results_summary(framework["id"], ADMIN)
        self.assertIsNone(summary["total_records"])

    def test_summary_unknown_framework(self):
        with self.assertRaises(NotFoundError):
            self.ext.results_summary("rfw-99", ADMIN)


class TestCollectionInstruments(unittest.TestCase):
    """GAPS idx 666 — instruments are definitions held as data."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = results_store()
        self.ext = DataMgmtExtensionsAddition(self.store)

    def test_define_instrument_shape_and_labels(self):
        instrument = self.ext.define_collection_instrument(
            "Household Survey v3", "survey_form", STEWARD,
            version_label="v3")
        self.assertEqual(instrument["id"], "cin-1")
        self.assertEqual(instrument["kind"], "survey_form")
        self.assertIs(instrument["collected_here"], False)
        self.assertIs(instrument["content_held"], False)

    def test_define_instrument_bad_kind_rejected_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.define_collection_instrument(
                "Bad", "web_form", STEWARD)
        instrument = self.ext.define_collection_instrument(
            "Good", "field_form", STEWARD)
        self.assertEqual(instrument["id"], "cin-1")

    def test_define_instrument_viewer_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.define_collection_instrument(
                "Nope", "survey_form", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("exta_instrument_define:denied", actions)


class TestInstrumentFields(unittest.TestCase):
    """GAPS idx 666 — field definitions are shapes, never values."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = results_store()
        self.ext = DataMgmtExtensionsAddition(self.store)
        self.instrument = self.ext.define_collection_instrument(
            "Household Survey v3", "survey_form", STEWARD)

    def test_add_field_shape(self):
        field = self.ext.add_instrument_field(
            self.instrument["id"], "household_size", "number", STEWARD,
            required=True)
        self.assertEqual(field["id"], "cif-1")
        self.assertEqual(field["field_kind"], "number")
        self.assertIs(field["required"], True)
        self.assertIs(field["content_held"], False)
        # A field definition's key set is pinned: no value slot.
        self.assertEqual(
            set(field),
            {"id", "instrument_id", "field_name", "field_kind",
             "required", "collected_here", "content_held", "created_by",
             "created_utc"},
        )

    def test_add_field_duplicate_name_rejected(self):
        self.ext.add_instrument_field(
            self.instrument["id"], "household_size", "number", STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.add_instrument_field(
                self.instrument["id"], "household_size", "text", STEWARD)

    def test_add_field_bad_kind_and_non_bool_required(self):
        with self.assertRaises(ValidationError):
            self.ext.add_instrument_field(
                self.instrument["id"], "x", "essay", STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.add_instrument_field(
                self.instrument["id"], "x", "text", STEWARD,
                required="yes")


class TestCaptureRuns(unittest.TestCase):
    """GAPS idx 666 — capture runs bind instruments to core ingestions."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = results_store()
        self.ext = DataMgmtExtensionsAddition(self.store)
        self.instrument = self.ext.define_collection_instrument(
            "Household Survey v3", "survey_form", STEWARD)
        self.ingestion = make_ingestion(self.store, self.dataset,
                                        self.source)

    def test_record_capture_run_takes_binding_from_core(self):
        run = self.ext.record_capture_run(
            self.instrument["id"], self.ingestion["id"],
            "reported_completed", STEWARD, records_reported=1200)
        self.assertEqual(run["id"], "crn-1")
        # Dataset and source come from the core ingestion record,
        # never from the caller.
        self.assertEqual(run["dataset_id"], self.dataset["id"])
        self.assertEqual(run["source_id"], self.source["id"])
        self.assertEqual(run["records_reported"], 1200)
        self.assertIs(run["collected_here"], False)
        self.assertIs(run["content_held"], False)

    def test_record_capture_run_duplicate_binding_rejected(self):
        self.ext.record_capture_run(
            self.instrument["id"], self.ingestion["id"],
            "reported_completed", STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.record_capture_run(
                self.instrument["id"], self.ingestion["id"],
                "reported_partial", STEWARD)

    def test_record_capture_run_bad_outcome_and_negative_count(self):
        with self.assertRaises(ValidationError):
            self.ext.record_capture_run(
                self.instrument["id"], self.ingestion["id"],
                "completed", STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.record_capture_run(
                self.instrument["id"], self.ingestion["id"],
                "reported_completed", STEWARD, records_reported=-1)

    def test_record_capture_run_unknown_ingestion(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_capture_run(
                self.instrument["id"], "ing-99", "reported_completed",
                STEWARD)


class TestInstrumentSummary(unittest.TestCase):
    """GAPS idx 666 — the instrument summary derives at read."""

    def test_summary_counts_tallies_and_reported_total(self):
        store, audit, dataset, source = results_store()
        ext = DataMgmtExtensionsAddition(store)
        instrument = ext.define_collection_instrument(
            "Household Survey v3", "survey_form", STEWARD)
        ext.add_instrument_field(instrument["id"], "household_size",
                                 "number", STEWARD, required=True)
        ext.add_instrument_field(instrument["id"], "village", "text",
                                 STEWARD)
        first = make_ingestion(store, dataset, source, count=1200)
        second = make_ingestion(store, dataset, source, count=300)
        third = make_ingestion(store, dataset, source, count=10)
        ext.record_capture_run(instrument["id"], first["id"],
                               "reported_completed", STEWARD,
                               records_reported=1200)
        ext.record_capture_run(instrument["id"], second["id"],
                               "reported_partial", STEWARD,
                               records_reported=280)
        ext.record_capture_run(instrument["id"], third["id"],
                               "reported_failed", STEWARD)
        summary = ext.instrument_summary(instrument["id"], ADMIN)
        self.assertEqual(summary["fields"], 2)
        self.assertEqual(summary["capture_runs"], 3)
        self.assertEqual(summary["runs_by_outcome"],
                         {"reported_completed": 1, "reported_partial": 1,
                          "reported_failed": 1})
        # The total is a sum of reported counts — reports, stated as
        # such; the count-less run is tallied separately.
        self.assertEqual(summary["total_records_reported"], 1480)
        self.assertEqual(summary["runs_without_reported_count"], 1)
        self.assertIs(summary["collected_here"], False)
        self.assertIs(summary["content_held"], False)

    def test_summary_unknown_instrument(self):
        store, audit, dataset, source = results_store()
        ext = DataMgmtExtensionsAddition(store)
        with self.assertRaises(NotFoundError):
            ext.instrument_summary("cin-99", ADMIN)


class TestNoContentSurface(unittest.TestCase):
    """The substrate's hard privacy rule, pinned over the new surface."""

    def _full_surface(self):
        store, audit, dataset, source = results_store()
        ext = DataMgmtExtensionsAddition(store)
        framework = make_framework(ext, dataset)
        indicator = make_indicator(ext, framework)
        ingestion = make_ingestion(store, dataset, source)
        report = ext.record_progress_report(
            indicator["id"], ingestion["id"], "reported_progressing",
            STEWARD, value_reported=1900)
        instrument = ext.define_collection_instrument(
            "Household Survey v3", "survey_form", STEWARD)
        field = ext.add_instrument_field(
            instrument["id"], "household_size", "number", STEWARD)
        run = ext.record_capture_run(
            instrument["id"], ingestion["id"], "reported_completed",
            STEWARD, records_reported=1200)
        objects = [
            framework, indicator, report, instrument, field, run,
            ext.results_summary(framework["id"], ADMIN),
            ext.instrument_summary(instrument["id"], ADMIN),
        ]
        return ext, objects

    def test_no_record_or_view_holds_content_shaped_keys(self):
        _, objects = self._full_surface()
        for obj in objects:
            for key, _value in walk(obj):
                self.assertNotIn(
                    key, FORBIDDEN_KEYS,
                    "content-shaped key %r on %r" % (key, obj.get("id")))

    def test_no_collection_or_execution_method_exists(self):
        ext, _ = self._full_surface()
        for name in ("collect", "collect_response", "submit_response",
                     "render_instrument", "field_instrument",
                     "measure", "measure_progress", "compute_progress",
                     "execute", "run_instrument"):
            self.assertFalse(hasattr(ext, name), name)


class MutantExtensionsAddition(DataMgmtExtensionsAddition):
    """The drill mutant: the latest-report seam reads the earliest."""

    @staticmethod
    def _latest_progress_report(reports):
        return reports[0] if reports else None


class TestLatestReportNegativeControl(unittest.TestCase):
    """Fresh negative control: latest means latest in the summary.

    The traced claim is that the results summary's latest reported
    outcome and value are the *most recent* progress report's —
    the derivation the M&E surface's honesty rests on (a summary
    that silently read the earliest report would misstate reported
    progress while looking well-formed). Each case asserts the
    canonical expectation from the real implementation, that the
    mutant (seam reading the earliest report) would NOT produce
    it, and — via a literal ``assertRaises(AssertionError)`` —
    that treating the mutant's outcome as the expected outcome
    fails.
    """

    def _summary(self, ext_cls):
        store, audit, dataset, source = results_store()
        ext = ext_cls(store)
        framework = make_framework(ext, dataset)
        indicator = make_indicator(ext, framework)
        first = make_ingestion(store, dataset, source, count=1200)
        second = make_ingestion(store, dataset, source, count=800)
        ext.record_progress_report(
            indicator["id"], first["id"], "reported_progressing",
            STEWARD, value_reported=1900)
        ext.record_progress_report(
            indicator["id"], second["id"], "reported_on_track",
            STEWARD, value_reported=2750)
        return ext.results_summary(framework["id"], ADMIN)

    def test_canonical_summary_reads_latest_report(self):
        summary = self._summary(DataMgmtExtensionsAddition)
        self.assertEqual(summary["latest_outcome"], "reported_on_track")
        self.assertEqual(summary["latest_value_reported"], 2750)

    def test_mutant_reads_earliest_and_expectation_fails(self):
        summary = self._summary(MutantExtensionsAddition)
        self.assertEqual(summary["latest_outcome"],
                         "reported_progressing")
        self.assertEqual(summary["latest_value_reported"], 1900)
        with self.assertRaises(AssertionError):
            self.assertEqual(summary["latest_outcome"],
                             "reported_on_track")
        with self.assertRaises(AssertionError):
            self.assertEqual(summary["latest_value_reported"], 2750)


if __name__ == "__main__":
    unittest.main()
