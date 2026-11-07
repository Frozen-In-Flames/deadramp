"""Final GAPS batch, second unit — Remainder Addition surface tests.

Traces to: GAPS.md "Remainder Addition — Analytics L1 (+1 fork)",
the 2 Extended functions named in ADDENDUM.md §5 for the addition
fork (HP WXP Collaboration), closed per
../../gaps-batch/DECISION.md: the UC telemetry engine shipped as
a labeled reference implementation in
``analytics/extensions_addition.py`` (nothing collects, connects,
or ingests), and the end-user experience & productivity
analytics engine built as records plus the core's descriptive
statistics over recorded dataset values — with no score defined
or computed anywhere. See ../BATCH-ADDITION.md.

Fixtures use the canonical sales dataset from analytics_helpers
(units 10..50: count 5, mean 30, median 30, min 10, max 50).
"""

import unittest

from analytics.audit import AuditLog
from analytics.errors import NotFoundError, PermissionDenied, ValidationError
from analytics.extensions_addition import AnalyticsExtensionsAddition
from analytics.query import describe
from analytics.store import DatasetStore

from analytics_helpers import ADMIN, ANALYST, VIEWER, sales_json_text


def make_addition():
    audit = AuditLog()
    store = DatasetStore(audit=audit)
    dataset = store.ingest_json("sales", sales_json_text(), ADMIN)
    return AnalyticsExtensionsAddition(store), store, dataset["id"], audit


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.exta, self.store, self.ds, self.audit = make_addition()


def _all_keys(node):
    keys = set()
    if isinstance(node, dict):
        for key, value in node.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            keys |= _all_keys(item)
    return keys


# -- UC telemetry engine (reference implementation) -----------------------


class TestTelemetryReference(AdditionFixture):
    def test_source_record_shape_and_labels(self):
        """UC telemetry (reference): the source definition is a
        labeled reference record; nothing collects or connects."""
        src = self.exta.register_telemetry_source_reference(
            "WXP Collaboration", "HP WXP", "unified_communications",
            ANALYST)
        self.assertEqual(src["id"], "uct-1")
        self.assertEqual(src["vendor_label"], "HP WXP")
        self.assertEqual(src["source_kind"], "unified_communications")
        self.assertTrue(src["reference_stub"])
        self.assertEqual(src["state"], "recorded_reference_only")
        self.assertFalse(src["collected_here"])
        self.assertFalse(src["connected_here"])

    def test_report_record_labels_and_outcome_verbatim(self):
        src = self.exta.register_telemetry_source_reference(
            "WXP", "HP WXP", "mixed_vendor", ANALYST)
        rep = self.exta.record_telemetry_report(
            src["id"], 12, 540, ANALYST, outcome="reported_complete")
        self.assertEqual(rep["id"], "uctr-1")
        self.assertTrue(rep["reference_stub"])
        self.assertTrue(rep["reference_transport"])
        self.assertFalse(rep["collected_here"])
        self.assertFalse(rep["ingested_here"])
        self.assertEqual(rep["outcome"], "reported_complete")

    def test_view_totals_are_sums_of_reports(self):
        """Reported rollups derive at read as sums of the recorded
        reports, stated as sums of reports."""
        src = self.exta.register_telemetry_source_reference(
            "WXP", "HP WXP", "unified_communications", ANALYST)
        self.exta.record_telemetry_report(src["id"], 4, 300, ANALYST)
        self.exta.record_telemetry_report(src["id"], 3, 150, ANALYST)
        view = self.exta.telemetry_source_view(src["id"], VIEWER)
        self.assertEqual(view["report_count"], 2)
        self.assertEqual(view["reported_sessions_total"], 7)
        self.assertEqual(view["reported_minutes_total"], 450)
        self.assertNotIn("reported_sessions_total", src)
        self.assertNotIn("report_count", src)

    def test_recording_reports_changes_no_core_dataset(self):
        """Telemetry is reported, never ingested: the core store's
        dataset set is byte-identical before and after reports."""
        before = [d["id"] for d in self.store.list()]
        src = self.exta.register_telemetry_source_reference(
            "WXP", "HP WXP", "endpoints", ANALYST)
        self.exta.record_telemetry_report(src["id"], 9, 90, ANALYST)
        self.assertEqual([d["id"] for d in self.store.list()], before)
        self.assertEqual(self.store.get(self.ds)["row_count"], 5)

    def test_unknown_source_and_bad_counts_rejected(self):
        with self.assertRaises(NotFoundError):
            self.exta.record_telemetry_report("uct-99", 1, 1, ANALYST)
        src = self.exta.register_telemetry_source_reference(
            "WXP", "HP WXP", "endpoints", ANALYST)
        for bad in (-1, 1.5, True):
            with self.assertRaises(ValidationError):
                self.exta.record_telemetry_report(src["id"], bad, 10,
                                                  ANALYST)
            with self.assertRaises(ValidationError):
                self.exta.record_telemetry_report(src["id"], 10, bad,
                                                  ANALYST)
        rep = self.exta.record_telemetry_report(src["id"], 1, 1, ANALYST)
        self.assertEqual(rep["id"], "uctr-1")  # failures consumed no id

    def test_bad_source_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.exta.register_telemetry_source_reference(
                "WXP", "HP WXP", "satellite", ANALYST)

    def test_viewer_denied_registration_and_denial_audited(self):
        with self.assertRaises(PermissionDenied):
            self.exta.register_telemetry_source_reference(
                "WXP", "HP WXP", "endpoints", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn(
            "exta_register_telemetry_source_reference:denied", actions)

    def test_no_collection_method_on_surface(self):
        for name in ("collect", "connect", "ingest_telemetry", "poll",
                     "subscribe", "stream"):
            self.assertFalse(hasattr(self.exta, name), name)


# -- End-user experience & productivity analytics (built) ------------------


class TestExperienceBuilt(AdditionFixture):
    def test_profile_record_shape_stores_no_figure(self):
        """Experience profile (built): a definition over a core
        dataset column; the stored record carries no figure and
        states on its face that no score is computed."""
        prof = self.exta.create_experience_profile(
            "Session experience", self.ds, "units", ANALYST)
        self.assertEqual(
            set(prof.keys()),
            {"id", "name", "dataset_id", "column", "method", "basis",
             "measured_here", "created_by", "created_utc"})
        self.assertEqual(prof["method"], "core_describe_derivation")
        self.assertEqual(prof["basis"], "recorded_dataset_values")
        self.assertFalse(prof["measured_here"])

    def test_profile_unknown_dataset_and_column_rejected(self):
        with self.assertRaises(NotFoundError):
            self.exta.create_experience_profile("X", "ds-999", "units",
                                                ANALYST)
        with self.assertRaises(ValidationError):
            self.exta.create_experience_profile("X", self.ds, "nope",
                                                ANALYST)

    def test_observation_record_shape_and_labels(self):
        prof = self.exta.create_experience_profile(
            "Session experience", self.ds, "units", ANALYST)
        obs = self.exta.record_experience_observation(
            prof["id"], "call_quality", "reported_good", 7, ANALYST)
        self.assertEqual(obs["id"], "expo-1")
        self.assertEqual(obs["dimension"], "call_quality")
        self.assertEqual(obs["reported_label"], "reported_good")
        self.assertEqual(obs["reported_count"], 7)
        self.assertFalse(obs["measured_here"])
        self.assertFalse(obs["computed_here"])

    def test_observation_bad_dimension_and_count_rejected(self):
        prof = self.exta.create_experience_profile(
            "Session experience", self.ds, "units", ANALYST)
        with self.assertRaises(ValidationError):
            self.exta.record_experience_observation(
                prof["id"], "happiness", "ok", 1, ANALYST)
        with self.assertRaises(ValidationError):
            self.exta.record_experience_observation(
                prof["id"], "call_quality", "ok", -2, ANALYST)
        with self.assertRaises(NotFoundError):
            self.exta.record_experience_observation(
                "exp-99", "call_quality", "ok", 1, ANALYST)

    def test_view_statistics_are_core_describe_over_recorded_values(self):
        """The view's figures are exactly the core's descriptive
        statistics over the recorded dataset column — statistics
        of recorded data, derived at read, not a score."""
        prof = self.exta.create_experience_profile(
            "Session experience", self.ds, "units", ANALYST)
        view = self.exta.experience_view(prof["id"], VIEWER)
        expected = describe(self.store, self.ds, "units", ADMIN)
        self.assertEqual(view["statistics"], expected)
        self.assertEqual(view["statistics"]["count"], 5)
        self.assertEqual(view["statistics"]["mean"], 30)
        self.assertEqual(view["statistics_basis"],
                         "recorded_dataset_values")

    def test_view_observation_rollup_derived_at_read(self):
        prof = self.exta.create_experience_profile(
            "Session experience", self.ds, "units", ANALYST)
        self.exta.record_experience_observation(
            prof["id"], "call_quality", "reported_good", 7, ANALYST)
        self.exta.record_experience_observation(
            prof["id"], "call_quality", "reported_poor", 2, ANALYST)
        self.exta.record_experience_observation(
            prof["id"], "productivity", "reported_good", 5, ANALYST)
        view = self.exta.experience_view(prof["id"], VIEWER)
        self.assertEqual(view["observation_count"], 3)
        self.assertEqual(view["reported_observations_total"], 14)
        self.assertEqual(view["observations_by_dimension"],
                         {"call_quality": 2, "productivity": 1})
        self.assertEqual(view["observations_by_label"],
                         {"reported_good": 2, "reported_poor": 1})
        self.assertNotIn("observation_count", prof)
        self.assertNotIn("reported_observations_total", prof)

    def test_no_score_key_anywhere_on_surface(self):
        """No score is defined or computed: a recursive scan of
        every record and view this surface produces finds no
        score-shaped key, and no method accepts a score."""
        prof = self.exta.create_experience_profile(
            "Session experience", self.ds, "units", ANALYST)
        obs = self.exta.record_experience_observation(
            prof["id"], "productivity", "reported_good", 3, ANALYST)
        view = self.exta.experience_view(prof["id"], VIEWER)
        for node in (prof, obs, view):
            for key in _all_keys(node):
                self.assertNotIn("score", key)
        with self.assertRaises(TypeError):
            self.exta.record_experience_observation(
                prof["id"], "productivity", "ok", 1, ANALYST, score=9.5)
        with self.assertRaises(TypeError):
            self.exta.create_experience_profile(
                "X", self.ds, "units", ANALYST, score_threshold=0.8)

    def test_viewer_cannot_create_profile(self):
        with self.assertRaises(PermissionDenied):
            self.exta.create_experience_profile(
                "X", self.ds, "units", VIEWER)


# -- Fresh negative control: the reported-counts sum seam -------------------


class _FirstCountEchoAddition(AnalyticsExtensionsAddition):
    """Mutant: reported totals echo the first reported count."""

    @staticmethod
    def _sum_reported_counts(counts):
        return counts[0] if counts else 0


class TestReportedCountsNegativeControl(AdditionFixture):
    """The canonical expectation: a reported total is the sum of
    every recorded report (4 + 3 sessions = 7; 7 + 5 observed =
    12). The first-count-echo mutant understates both and must
    be rejected by that expectation."""

    def setUp(self):
        super().setUp()
        self.mutant = _FirstCountEchoAddition(self.store)
        self.src_id = None
        for ext in (self.exta, self.mutant):
            src = ext.register_telemetry_source_reference(
                "WXP", "HP WXP", "unified_communications", ANALYST)
            self.src_id = src["id"]  # "uct-1" in each own registry
            ext.record_telemetry_report(src["id"], 4, 300, ANALYST)
            ext.record_telemetry_report(src["id"], 3, 150, ANALYST)

    def test_canonical_totals_sum_all_reports(self):
        view = self.exta.telemetry_source_view(self.src_id, VIEWER)
        self.assertEqual(view["reported_sessions_total"], 7)
        self.assertEqual(view["reported_minutes_total"], 450)

    def test_mutant_echo_is_rejected_by_canonical_expectation(self):
        view = self.mutant.telemetry_source_view(self.src_id, VIEWER)
        self.assertEqual(view["reported_sessions_total"], 4)
        with self.assertRaises(AssertionError):
            self.assertEqual(view["reported_sessions_total"], 7)
        with self.assertRaises(AssertionError):
            self.assertEqual(view["reported_minutes_total"], 450)


if __name__ == "__main__":
    unittest.main()
