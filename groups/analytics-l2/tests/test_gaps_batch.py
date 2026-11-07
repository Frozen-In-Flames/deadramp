"""Final GAPS batch — extension surface tests for Analytics L2.

Traces to: GAPS.md "Group 1 — Analytics L2 (128 forks)", the 14
Extended families of UNION-SPEC.md, closed per
../../gaps-batch/DECISION.md: 10 built as records plus deterministic
derivations in ``analytics/extensions.py``, 4 shipped as labeled
reference implementations (predictive ML, alerts/monitoring,
streaming, proprietary-source connectors). See ../BATCH.md.

Fixtures use the canonical sales dataset from analytics_helpers
(units sum 150, revenue mean 320) plus a small notes dataset for the
text derivations.
"""

import json
import unittest

from analytics.audit import AuditLog
from analytics.errors import NotFoundError, PermissionDenied, ValidationError
from analytics.extensions import AnalyticsExtensions
from analytics.store import DatasetStore

from analytics_helpers import ADMIN, ANALYST, VIEWER, sales_json_text

NOTES_ROWS = [
    {"note": "Widget sales rose"},
    {"note": "widget SALES fell"},
    {"note": "Gadget sales rose"},
]


def make_extensions():
    audit = AuditLog()
    store = DatasetStore(audit=audit)
    dataset = store.ingest_json("sales", sales_json_text(), ADMIN)
    notes = store.ingest_json("notes", json.dumps(NOTES_ROWS), ADMIN)
    return AnalyticsExtensions(store), store, dataset["id"], notes["id"], audit


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.ds, self.notes, self.audit = make_extensions()


# -- Collaboration -------------------------------------------------------


class TestCollaboration(BatchFixture):
    def test_workspace_member_share_and_derived_view(self):
        """Collaboration: workspace/member/share records; counts derived."""
        ws = self.ext.create_workspace("Revenue pod", ANALYST)
        self.assertEqual(set(ws.keys()),
                         {"id", "name", "created_by", "created_utc"})
        self.ext.add_workspace_member(ws["id"], "person-ref-7", "editor", ANALYST)
        self.ext.share_dataset(ws["id"], self.ds, ANALYST)
        view = self.ext.workspace_view(ws["id"], VIEWER)
        self.assertEqual(view["member_count"], 1)
        self.assertEqual(view["share_count"], 1)
        self.assertEqual(view["shares"][0]["target_kind"], "dataset")
        # The stored record carries no derived keys.
        self.assertNotIn("member_count", ws)

    def test_share_unknown_dataset_rejected(self):
        ws = self.ext.create_workspace("Pod", ANALYST)
        with self.assertRaises(NotFoundError):
            self.ext.share_dataset(ws["id"], "ds-999", ANALYST)

    def test_bad_member_role_rejected(self):
        ws = self.ext.create_workspace("Pod", ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.add_workspace_member(ws["id"], "ref-1", "owner", ANALYST)


# -- Data transformation / ETL --------------------------------------------


def _north_transform(ext, ds):
    return ext.create_transform(
        "north only", ds,
        [{"step": "filter", "column": "region", "op": "eq", "value": "north"}],
        ANALYST)


def _canonical_filter_expectation(testcase, ext, ds):
    """The canonical expectation the negative control defends:
    a filter step actually filters (3 of 5 sales rows are north)."""
    transform = _north_transform(ext, ds)
    result = ext.run_transform(transform["id"], ANALYST)
    testcase.assertEqual(result["row_count"], 3)
    testcase.assertTrue(all(r["region"] == "north" for r in result["rows"]))
    testcase.assertEqual(result["method"], "deterministic_rules")


class _FilterBlindExtensions(AnalyticsExtensions):
    """Mutant: filter steps are silently dropped before applying."""

    def _apply_transform_steps(self, rows, columns, steps):
        steps = [s for s in steps if s.get("step") != "filter"]
        return super()._apply_transform_steps(rows, columns, steps)


class TestTransform(BatchFixture):
    def test_filter_run_and_run_record(self):
        """ETL: stated-rule steps derive rows; the run record stores
        counts and method only, never the derived rows."""
        _canonical_filter_expectation(self, self.ext, self.ds)
        transform = _north_transform(self.ext, self.ds)
        result = self.ext.run_transform(transform["id"], ANALYST)
        view = self.ext.transform_view(transform["id"], ANALYST)
        self.assertEqual(view["run_count"], 1)
        run = view["runs"][0]
        self.assertEqual((run["rows_in"], run["rows_out"]), (5, 3))
        self.assertNotIn("rows", run)
        self.assertEqual(result["rows"][0]["units"], 10)

    def test_rename_select_sort_limit_chain(self):
        transform = self.ext.create_transform("chain", self.ds, [
            {"step": "rename", "from": "product", "to": "item"},
            {"step": "select_columns", "columns": ["region", "item", "units"]},
            {"step": "sort", "column": "units", "direction": "desc"},
            {"step": "limit", "limit": 2},
        ], ANALYST)
        result = self.ext.run_transform(transform["id"], ANALYST)
        self.assertEqual(result["columns"], ["region", "item", "units"])
        self.assertEqual([r["units"] for r in result["rows"]], [50, 40])

    def test_invalid_step_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_transform("bad", self.ds,
                                      [{"step": "filter", "column": "nope",
                                        "op": "eq", "value": 1}], ANALYST)
        good = _north_transform(self.ext, self.ds)
        self.assertEqual(good["id"], "tr-1")

    def test_reported_run_recorded_verbatim(self):
        transform = _north_transform(self.ext, self.ds)
        run = self.ext.record_reported_transform_run(
            transform["id"], 1000, 990, ANALYST, note="external engine")
        self.assertTrue(run["reported"])
        self.assertEqual(run["method"], "reported")
        self.assertEqual((run["rows_in"], run["rows_out"]), (1000, 990))


class TestTransformNegativeControl(BatchFixture):
    def test_mutant_is_rejected(self):
        """Fresh negative control, in the house three-part form:
        the canonical expectation is stated, the real
        implementation meets it, and the filter-blind mutant is
        rejected by it -- proving the suite catches a non-filtering
        filter, not merely that code ran. Verified against the real
        file by the drill recorded in tests/README.md."""
        _canonical_filter_expectation(self, self.ext, self.ds)
        audit = AuditLog()
        store = DatasetStore(audit=audit)
        ds = store.ingest_json("sales", sales_json_text(), ADMIN)["id"]
        mutant = _FilterBlindExtensions(store)
        with self.assertRaises(AssertionError):
            _canonical_filter_expectation(self, mutant, ds)


# -- Governance -------------------------------------------------------------


class TestGovernance(BatchFixture):
    def test_policy_and_review_rollup(self):
        """Governance: policy records + review decisions recorded
        verbatim; current decision derived at read."""
        self.ext.create_policy(self.ds, "classification", "internal use", ANALYST)
        self.ext.record_access_review(self.ds, "reviewer-1", "approved", ADMIN)
        view = self.ext.governance_view(self.ds, VIEWER)
        self.assertEqual(view["policy_count"], 1)
        self.assertEqual(view["current_decision"], "approved")
        self.ext.record_access_review(self.ds, "reviewer-2",
                                      "changes_requested", ADMIN)
        view = self.ext.governance_view(self.ds, VIEWER)
        self.assertEqual(view["current_decision"], "changes_requested")
        self.assertEqual(view["reviews_by_decision"],
                         {"approved": 1, "changes_requested": 1})

    def test_review_is_admin_only(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_access_review(self.ds, "reviewer-1", "approved",
                                          ANALYST)


# -- Geospatial ----------------------------------------------------------------


class TestGeospatial(BatchFixture):
    def setUp(self):
        super().setUp()
        self.ext.register_place("origin", 0, 0, ANALYST)
        self.ext.register_place("east", 0, 1, ANALYST)
        self.ext.register_place("north", 1, 0, ANALYST)

    def test_distance_is_haversine_derivation(self):
        """Geospatial: one degree of longitude on the equator is
        111.195 km by the haversine formula; stored records hold
        coordinates only."""
        result = self.ext.distance_km("origin", "east", VIEWER)
        self.assertAlmostEqual(result["distance_km"], 111.195, delta=0.01)
        self.assertEqual(result["method"], "haversine_great_circle")
        record = self.ext.place_record("east", VIEWER)
        self.assertEqual(set(record.keys()),
                         {"id", "place_ref", "latitude", "longitude",
                          "created_by", "created_utc"})

    def test_bearing_and_nearest(self):
        bearing = self.ext.initial_bearing_degrees("origin", "east", VIEWER)
        self.assertAlmostEqual(bearing["bearing_degrees"], 90.0, delta=1e-9)
        nearest = self.ext.nearest_place("origin", VIEWER)
        self.assertIn(nearest["nearest_ref"], ("east", "north"))
        self.assertAlmostEqual(nearest["distance_km"], 111.195, delta=0.01)

    def test_coordinate_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.register_place("bad", 91, 0, ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.register_place("bad2", 0, True, ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.register_place("origin", 5, 5, ANALYST)


# -- Text / NLP ------------------------------------------------------------------


class TestTextAnalytics(BatchFixture):
    def test_term_counts_are_deterministic(self):
        """Text: lowercase alphanumeric token counts over held text;
        counts only, no inference."""
        result = self.ext.analyze_text(self.notes, "note", VIEWER)
        self.assertEqual(result["document_count"], 3)
        self.assertEqual(result["token_count"], 9)
        self.assertEqual(result["distinct_terms"], 5)
        self.assertEqual(result["top_terms"][0], {"term": "sales", "count": 3})
        self.assertEqual(result["method"], "deterministic_token_count")

    def test_term_count(self):
        result = self.ext.term_count(self.notes, "note", "WIDGET", VIEWER)
        self.assertEqual((result["count"], result["document_count"]), (2, 2))
        with self.assertRaises(ValidationError):
            self.ext.term_count(self.notes, "note", "two words", VIEWER)


# -- Archiving ---------------------------------------------------------------------


class TestArchiving(BatchFixture):
    def test_archive_record_deletes_nothing(self):
        """Archiving: the record is a disposition record only; the
        dataset remains fully present (PLATFORM-LAYER decision 4)."""
        before = self.store.rows(self.ds)
        status = self.ext.archive_status(self.ds, VIEWER)
        self.assertFalse(status["archived"])
        record = self.ext.create_archive_record("dataset", self.ds, ANALYST,
                                                reason="quarterly snapshot")
        self.assertEqual(record["disposition"], "record_only")
        self.assertEqual(record["retention_execution"],
                         "embedding_organization")
        self.assertEqual(self.store.get(self.ds)["row_count"], 5)
        self.assertEqual(self.store.rows(self.ds), before)
        status = self.ext.archive_status(self.ds, VIEWER)
        self.assertTrue(status["archived"])
        self.assertEqual(status["latest_archive_id"], record["id"])


# -- Self-service BI -------------------------------------------------------------------


class TestSelfServiceBI(BatchFixture):
    def test_saved_view_runs_live_and_stores_no_result(self):
        """Self-service BI: a saved view stores its query definition;
        running it derives from the live dataset via the core."""
        view = self.ext.create_saved_view(
            "units by region", self.ds,
            {"group_by": ["region"],
             "aggregates": [{"func": "sum", "column": "units",
                             "alias": "total"}]}, ANALYST)
        self.assertEqual(set(view.keys()),
                         {"id", "name", "dataset_id", "query",
                          "created_by", "created_utc"})
        result = self.ext.run_saved_view(view["id"], VIEWER)
        totals = {r["region"]: r["total"] for r in result["rows"]}
        self.assertEqual(totals, {"north": 90, "south": 60})
        stored = self.ext.get_saved_view(view["id"], VIEWER)
        self.assertNotIn("result", stored)

    def test_invalid_view_query_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_saved_view("bad", self.ds,
                                       {"select": ["nope"]}, ANALYST)

    def test_dashboard_panels(self):
        view = self.ext.create_saved_view("v", self.ds, {"select": ["region"]},
                                          ANALYST)
        dash = self.ext.create_dashboard("Ops board", ANALYST)
        self.ext.add_dashboard_panel(dash["id"], view["id"], "Regions", ANALYST)
        board = self.ext.dashboard_view(dash["id"], VIEWER)
        self.assertEqual(board["panel_count"], 1)
        self.assertEqual(board["panels"][0]["view_name"], "v")
        self.assertEqual(board["panels"][0]["position"], 1)


# -- KPI management ------------------------------------------------------------------------


class TestKPI(BatchFixture):
    def test_describe_kpi_value_derived_never_stored(self):
        """KPI: the definition holds measure + target as data; the
        value (revenue mean 320) is derived at read from describe."""
        kpi = self.ext.define_kpi(
            "avg revenue", self.ds,
            {"kind": "describe", "column": "revenue", "statistic": "mean"},
            ANALYST, target=300)
        self.assertNotIn("value", self.ext.get_kpi(kpi["id"], VIEWER))
        result = self.ext.kpi_value(kpi["id"], VIEWER)
        self.assertEqual(result["value"], 320.0)
        self.assertEqual(result["delta"], 20.0)

    def test_aggregate_kpi_with_where(self):
        kpi = self.ext.define_kpi(
            "north units", self.ds,
            {"kind": "aggregate", "func": "sum", "column": "units",
             "where": [{"column": "region", "op": "eq", "value": "north"}]},
            ANALYST)
        self.assertEqual(self.ext.kpi_value(kpi["id"], VIEWER)["value"], 90)


# -- Scheduling --------------------------------------------------------------------------------


class TestScheduling(BatchFixture):
    def test_schedule_and_recorded_receipts(self):
        """Scheduling: definitions + recorded receipts only; nothing
        executes (executed_here False) and rollups derive at read."""
        view = self.ext.create_saved_view("v", self.ds, {}, ANALYST)
        sched = self.ext.create_schedule("nightly view", "saved_view",
                                         view["id"], "daily", ANALYST)
        receipt = self.ext.record_schedule_run(sched["id"], "completed", ANALYST)
        self.assertFalse(receipt["executed_here"])
        view_out = self.ext.schedule_view(sched["id"], VIEWER)
        self.assertEqual(view_out["run_count"], 1)
        self.assertEqual(view_out["last_outcome"], "completed")
        self.assertNotIn("run_count", sched)


# -- Media analytics ------------------------------------------------------------------------------


class TestMediaAnalytics(BatchFixture):
    def test_metadata_records_and_derived_summary(self):
        """Media: metadata records only (no content, no analysis);
        the summary is counts derived at read."""
        self.ext.register_media_asset("img-1", "image", ANALYST,
                                      duration_seconds=30)
        self.ext.register_media_asset("img-2", "image", ANALYST)
        asset = self.ext.register_media_asset("vid-1", "video", ANALYST,
                                              duration_seconds=120)
        self.assertEqual(asset["analysis"], "metadata_only")
        summary = self.ext.media_summary(VIEWER)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_kind"], {"image": 2, "video": 1})
        self.assertEqual(summary["total_duration_seconds"], 150)


# -- Reference stubs ------------------------------------------------------------------------


class TestPredictiveMLReference(BatchFixture):
    def test_model_reference_is_labeled_and_never_trains(self):
        """Predictive ML (stub): reference records only; there is no
        training or prediction anywhere on the surface."""
        model = self.ext.register_model_reference("churn model", "regression",
                                                  ANALYST, dataset_id=self.ds)
        self.assertTrue(model["reference_stub"])
        self.assertEqual(model["state"], "recorded_reference_only")
        self.assertFalse(model["trained_here"])
        self.assertFalse(hasattr(self.ext, "predict"))
        self.assertFalse(hasattr(self.ext, "train_model"))
        run = self.ext.record_model_run_reference(model["id"], "reported rmse 4.2",
                                                  ANALYST)
        self.assertFalse(run["executed"])
        self.assertEqual(self.ext.model_view(model["id"], VIEWER)["run_count"], 1)


class TestAlertsReference(BatchFixture):
    def test_rule_and_recorded_evaluation(self):
        """Alerts (stub): rules are records and monitoring_here is
        False; the only evaluation is a point-in-time receipt over
        the core describe statistic (revenue mean 320)."""
        rule = self.ext.create_alert_rule("rev watch", self.ds, "revenue",
                                          "mean", "gt", 300, ANALYST)
        self.assertTrue(rule["reference_stub"])
        self.assertFalse(rule["monitoring_here"])
        receipt = self.ext.record_alert_evaluation(rule["id"], ANALYST)
        self.assertEqual(receipt["value"], 320.0)
        self.assertTrue(receipt["breached"])
        self.assertEqual(receipt["method"],
                         "recorded_evaluation_over_core_describe")
        calm = self.ext.create_alert_rule("calm", self.ds, "revenue", "mean",
                                          "gt", 1000, ANALYST)
        self.assertFalse(
            self.ext.record_alert_evaluation(calm["id"], ANALYST)["breached"])
        view = self.ext.alert_rule_view(rule["id"], VIEWER)
        self.assertEqual(view["evaluation_count"], 1)
        self.assertTrue(view["last_breached"])


class TestStreamingReference(BatchFixture):
    def test_stream_reference_ingests_nothing(self):
        """Streaming (stub): batch receipts are reported counts; the
        core store is untouched by them."""
        stream = self.ext.register_stream_reference("events", "src-ref-1",
                                                    ANALYST)
        self.assertTrue(stream["reference_stub"])
        self.assertFalse(stream["streaming_here"])
        before = len(self.store.list())
        batch = self.ext.record_stream_batch_reference(stream["id"], 500, ANALYST)
        self.assertTrue(batch["reference_transport"])
        self.assertFalse(batch["ingested_here"])
        self.assertEqual(len(self.store.list()), before)
        view = self.ext.stream_view(stream["id"], VIEWER)
        self.assertEqual(view["reported_rows_total"], 500)


class TestConnectorsReference(BatchFixture):
    def test_connector_reference_connects_nothing(self):
        """Connectors (stub): reference records only; core ingest
        (open CSV/JSON) is unchanged and nothing is ingested."""
        conn = self.ext.register_connector_reference("warehouse x", "warehouse",
                                                     ANALYST)
        self.assertTrue(conn["reference_stub"])
        self.assertFalse(conn["connected_here"])
        sync = self.ext.record_connector_sync_reference(conn["id"], 42, ANALYST)
        self.assertFalse(sync["ingested_here"])
        self.assertEqual(len(self.store.list()), 2)
        view = self.ext.connector_view(conn["id"], VIEWER)
        self.assertEqual(view["reported_rows_total"], 42)


# -- Cross-cutting: RBAC + audit -------------------------------------------------


class TestRbacAndAudit(BatchFixture):
    def test_viewer_mutation_denied_and_audited(self):
        """RBAC: viewer holds query/export only; a denied extension
        mutation is recorded on the core audit log as :denied."""
        with self.assertRaises(PermissionDenied):
            self.ext.create_workspace("nope", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_create_workspace:denied", actions)

    def test_successful_mutations_audited_with_ext_prefix(self):
        self.ext.create_workspace("pod", ANALYST)
        self.ext.register_place("p1", 10, 20, ANALYST)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_create_workspace", actions)
        self.assertIn("ext_register_place", actions)


if __name__ == "__main__":
    unittest.main()
