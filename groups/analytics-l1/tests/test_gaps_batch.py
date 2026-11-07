"""Final GAPS batch — extension surface tests for Analytics L1.

Traces to: GAPS.md "Group 7 — Analytics L1 (16 forks)", the 8
Extended families of UNION-SPEC.md, closed per
../../gaps-batch/DECISION.md: 4 built as records plus deterministic
derivations in ``analytics/extensions.py`` (collaboration, archiving,
transformation, text/NLP in request-records form), 4 shipped as
labeled reference implementations (streaming, proprietary-source
connectors, predictive ML, alerts/monitoring). See ../BATCH.md.

Fixtures use the canonical sales dataset from analytics_helpers
(units sum 150, revenue mean 320; 3 of 5 rows are north).
"""

import hashlib
import json
import unittest

from analytics.audit import AuditLog
from analytics.errors import NotFoundError, PermissionDenied, ValidationError
from analytics.extensions import AnalyticsExtensions
from analytics.store import DatasetStore

from analytics_helpers import ADMIN, ANALYST, VIEWER, sales_json_text


def make_extensions():
    audit = AuditLog()
    store = DatasetStore(audit=audit)
    dataset = store.ingest_json("sales", sales_json_text(), ADMIN)
    return AnalyticsExtensions(store), store, dataset["id"], audit


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.ds, self.audit = make_extensions()


# -- Collaboration -------------------------------------------------------


class TestCollaboration(BatchFixture):
    def test_workspace_member_share_annotation_and_derived_view(self):
        """Collaboration (built): workspace/member/share/annotation
        records over core datasets and report refs; counts derived
        at read, never stored."""
        ws = self.ext.create_workspace("Revenue pod", ANALYST)
        self.assertEqual(set(ws.keys()),
                         {"id", "name", "created_by", "created_utc"})
        self.ext.add_workspace_member(ws["id"], "person-ref-7", "editor",
                                      ANALYST)
        self.ext.share_dataset(ws["id"], self.ds, ANALYST)
        ann = self.ext.add_annotation("dataset", self.ds,
                                      "check north totals", ANALYST)
        self.assertEqual(ann["text"], "check north totals")
        self.ext.add_annotation("report", "report-ref-1", "looks right",
                                ANALYST)
        view = self.ext.workspace_view(ws["id"], VIEWER)
        self.assertEqual(view["member_count"], 1)
        self.assertEqual(view["share_count"], 1)
        self.assertEqual(view["shares"][0]["target_kind"], "dataset")
        self.assertNotIn("member_count", ws)
        notes = self.ext.annotations_for(self.ds, VIEWER)
        self.assertEqual(notes["annotation_count"], 1)
        self.assertEqual(notes["annotations"][0]["id"], ann["id"])

    def test_share_unknown_dataset_rejected(self):
        ws = self.ext.create_workspace("Pod", ANALYST)
        with self.assertRaises(NotFoundError):
            self.ext.share_dataset(ws["id"], "ds-999", ANALYST)

    def test_annotation_on_unknown_dataset_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.add_annotation("dataset", "ds-999", "note", ANALYST)

    def test_bad_member_role_rejected(self):
        ws = self.ext.create_workspace("Pod", ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.add_workspace_member(ws["id"], "ref-1", "owner", ANALYST)


# -- Archiving -------------------------------------------------------------


class TestArchiving(BatchFixture):
    def test_archive_record_checksum_and_deletes_nothing(self):
        """Archiving (built): the record carries metadata plus a
        SHA-256 checksum over the core rows; the dataset remains
        fully present (PLATFORM-LAYER decision 4)."""
        before = self.store.rows(self.ds)
        status = self.ext.archive_status(self.ds, VIEWER)
        self.assertFalse(status["archived"])
        record = self.ext.create_archive_record(
            "dataset", self.ds, ANALYST, reason="quarterly snapshot")
        self.assertEqual(record["disposition"], "record_only")
        self.assertEqual(record["retention_execution"],
                         "embedding_organization")
        expected = hashlib.sha256(
            json.dumps(before, sort_keys=True, default=str)
            .encode("utf-8")).hexdigest()
        self.assertEqual(record["checksum"], expected)
        self.assertEqual(self.store.get(self.ds)["row_count"], 5)
        self.assertEqual(self.store.rows(self.ds), before)
        status = self.ext.archive_status(self.ds, VIEWER)
        self.assertTrue(status["archived"])
        self.assertEqual(status["latest_checksum"], expected)

    def test_report_archive_carries_no_checksum(self):
        record = self.ext.create_archive_record("report", "report-ref-9",
                                                ANALYST)
        self.assertIsNone(record["checksum"])


# -- Transformation ----------------------------------------------------------


def _north_transform(ext, ds):
    return ext.create_transform(
        "north only", ds,
        {"where": [{"column": "region", "op": "eq", "value": "north"}]},
        ANALYST)


def _canonical_run_expectation(testcase, ext, ds):
    """The canonical expectation the negative control defends: a
    transform run over the canonical sales dataset with a
    region-eq-north definition derives exactly the 3 north rows,
    and its run record reports rows_in 5 / rows_out 3."""
    transform = _north_transform(ext, ds)
    result = ext.run_transform(transform["id"], ANALYST)
    testcase.assertEqual(result["row_count"], 3)
    testcase.assertTrue(all(r["region"] == "north" for r in result["rows"]))
    testcase.assertEqual(result["method"], "core_query_derivation")
    view = ext.transform_view(transform["id"], ANALYST)
    testcase.assertEqual(view["run_count"], 1)
    run = view["runs"][0]
    testcase.assertEqual((run["rows_in"], run["rows_out"]), (5, 3))
    testcase.assertTrue(run["executed_here"])
    testcase.assertNotIn("rows", run)


class _RowsOutEchoExtensions(AnalyticsExtensions):
    """Mutant: the run record's rows_out merely echoes rows_in."""

    @staticmethod
    def _derive_rows_out(result, rows_in):
        return rows_in


class TestTransform(BatchFixture):
    def test_run_derives_through_core_and_records_counts_only(self):
        _canonical_run_expectation(self, self.ext, self.ds)

    def test_aggregate_transform_uses_core_aggregation(self):
        """Transformation: a group_by/aggregates definition derives
        through the core's deterministic aggregation machinery
        (north units 90, south units 60)."""
        transform = self.ext.create_transform(
            "units by region", self.ds,
            {"group_by": ["region"],
             "aggregates": [{"func": "sum", "column": "units",
                             "alias": "total"}]}, ANALYST)
        result = self.ext.run_transform(transform["id"], ANALYST)
        totals = {r["region"]: r["total"] for r in result["rows"]}
        self.assertEqual(totals, {"north": 90, "south": 60})

    def test_invalid_definition_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_transform("bad", self.ds,
                                      {"select": ["nope"]}, ANALYST)
        good = _north_transform(self.ext, self.ds)
        self.assertEqual(good["id"], "tr-1")

    def test_reported_run_recorded_verbatim_not_executed(self):
        transform = _north_transform(self.ext, self.ds)
        run = self.ext.record_reported_transform_run(
            transform["id"], 1000, 990, ANALYST, note="external engine")
        self.assertTrue(run["reported"])
        self.assertFalse(run["executed_here"])
        self.assertEqual(run["method"], "reported")
        self.assertEqual((run["rows_in"], run["rows_out"]), (1000, 990))


class TestTransformNegativeControl(BatchFixture):
    def test_mutant_is_rejected(self):
        """Fresh negative control, in the house three-part form: the
        canonical expectation is stated, the real implementation
        meets it, and the rows_out-echo mutant is rejected by it --
        proving the suite catches a run record that reports its
        input size as its output size. Verified against the real
        file by the drill recorded in tests/README.md."""
        _canonical_run_expectation(self, self.ext, self.ds)
        audit = AuditLog()
        store = DatasetStore(audit=audit)
        ds = store.ingest_json("sales", sales_json_text(), ADMIN)["id"]
        mutant = _RowsOutEchoExtensions(store)
        with self.assertRaises(AssertionError):
            _canonical_run_expectation(self, mutant, ds)


# -- Text / NLP -----------------------------------------------------------------


class TestTextNLP(BatchFixture):
    def test_request_and_result_records_analyze_nothing(self):
        """Text/NLP (built, request-records form): a request names a
        dataset column and an analysis kind; the result is held as
        an opaque ref and/or verbatim reported labels; nothing is
        analyzed here and no text content is stored."""
        request = self.ext.create_text_analysis_request(
            self.ds, "product", "topics", ANALYST)
        self.assertEqual(set(request.keys()),
                         {"id", "dataset_id", "column", "analysis_kind",
                          "analyzed_here", "requested_by", "requested_utc"})
        self.assertFalse(request["analyzed_here"])
        result = self.ext.record_text_analysis_result(
            request["id"], ANALYST, result_ref="nlp-result-1",
            reported_labels=["widget", "gadget"])
        self.assertFalse(result["analyzed_here"])
        self.assertEqual(result["reported_labels"], ["widget", "gadget"])
        view = self.ext.text_analysis_view(request["id"], VIEWER)
        self.assertEqual(view["result_count"], 1)
        self.assertNotIn("result_count", request)

    def test_result_requires_ref_or_labels(self):
        request = self.ext.create_text_analysis_request(
            self.ds, "product", "sentiment", ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.record_text_analysis_result(request["id"], ANALYST)

    def test_unknown_column_and_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_text_analysis_request(
                self.ds, "nope", "topics", ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.create_text_analysis_request(
                self.ds, "product", "telepathy", ANALYST)

    def test_text_content_kwarg_rejected(self):
        request = self.ext.create_text_analysis_request(
            self.ds, "product", "keywords", ANALYST)
        with self.assertRaises(TypeError):
            self.ext.record_text_analysis_result(
                request["id"], ANALYST, result_ref="r-1", text="raw text")


# -- Real-time / streaming (reference) --------------------------------------------


class TestStreamingReference(BatchFixture):
    def test_stream_reference_ingests_nothing(self):
        """Streaming (stub): definitions as data plus reported
        event-count records; streamed_here False and the core store
        is untouched by the reports."""
        stream = self.ext.register_stream_reference("events", "src-ref-1",
                                                    ANALYST)
        self.assertTrue(stream["reference_stub"])
        self.assertFalse(stream["streamed_here"])
        before = len(self.store.list())
        report = self.ext.record_stream_event_report(stream["id"], 500,
                                                     ANALYST)
        self.assertTrue(report["reference_transport"])
        self.assertFalse(report["ingested_here"])
        self.assertFalse(report["streamed_here"])
        self.assertEqual(len(self.store.list()), before)
        self.ext.record_stream_event_report(stream["id"], 250, ANALYST)
        view = self.ext.stream_view(stream["id"], VIEWER)
        self.assertEqual(view["reported_events_total"], 750)
        self.assertEqual(view["report_count"], 2)
        self.assertNotIn("report_count", stream)


# -- Proprietary-source connectors (reference) ---------------------------------------


class TestConnectorsReference(BatchFixture):
    def test_connector_reference_connects_and_syncs_nothing(self):
        """Connectors (stub): definitions as data plus verbatim sync
        reports; connected_here/synced_here False, nothing ingested,
        and the core's open CSV/JSON ingest is unchanged."""
        conn = self.ext.register_connector_reference("warehouse x",
                                                     "warehouse", ANALYST)
        self.assertTrue(conn["reference_stub"])
        self.assertFalse(conn["connected_here"])
        self.assertFalse(conn["synced_here"])
        sync = self.ext.record_connector_sync_reference(
            conn["id"], 42, ANALYST, outcome="reported complete")
        self.assertFalse(sync["synced_here"])
        self.assertFalse(sync["ingested_here"])
        self.assertEqual(sync["outcome"], "reported complete")
        self.assertEqual(len(self.store.list()), 1)
        view = self.ext.connector_view(conn["id"], VIEWER)
        self.assertEqual(view["reported_rows_total"], 42)
        # Core open-format ingest still works exactly as before.
        extra = self.store.ingest_csv("more", "a,b\n1,2\n", ADMIN)
        self.assertEqual(extra["row_count"], 1)


# -- Predictive ML (reference) ---------------------------------------------------------


class TestPredictiveMLReference(BatchFixture):
    def test_model_requests_and_opaque_results_predict_nothing(self):
        """Predictive ML (stub): model definitions as data plus
        prediction-request records whose results are opaque refs;
        predicted_here/inference_here False and there is no train
        or predict method on the surface. The core's descriptive
        statistics are not relabeled as ML."""
        model = self.ext.register_model_reference(
            "demand model", "forecasting", ANALYST, dataset_id=self.ds)
        self.assertTrue(model["reference_stub"])
        self.assertFalse(model["trained_here"])
        self.assertFalse(model["predicted_here"])
        self.assertFalse(model["inference_here"])
        self.assertFalse(hasattr(self.ext, "predict"))
        self.assertFalse(hasattr(self.ext, "train_model"))
        request = self.ext.record_prediction_request(
            model["id"], ANALYST, dataset_id=self.ds)
        self.assertFalse(request["predicted_here"])
        result = self.ext.record_prediction_result_reference(
            request["id"], "pred-result-7", ANALYST)
        self.assertEqual(result["result_ref"], "pred-result-7")
        self.assertFalse(result["inference_here"])
        view = self.ext.model_view(model["id"], VIEWER)
        self.assertEqual(view["request_count"], 1)
        self.assertEqual(view["result_count"], 1)

    def test_prediction_value_kwarg_rejected(self):
        model = self.ext.register_model_reference("m", "regression", ANALYST)
        request = self.ext.record_prediction_request(model["id"], ANALYST)
        with self.assertRaises(TypeError):
            self.ext.record_prediction_result_reference(
                request["id"], "r-1", ANALYST, prediction=42.0)


# -- Alerts / monitoring (reference) ------------------------------------------------------


class TestAlertsReference(BatchFixture):
    def test_rule_registry_never_evaluates_or_fires(self):
        """Alerts (stub): rule definitions as data plus reported
        alert records; monitored_here False, the registry never
        evaluates (no evaluate method exists) and fires nothing."""
        rule = self.ext.create_alert_rule(
            "rev watch", self.ds, "revenue", "mean", "gt", 300, ANALYST)
        self.assertTrue(rule["reference_stub"])
        self.assertFalse(rule["monitored_here"])
        self.assertFalse(rule["evaluated_here"])
        self.assertFalse(rule["fired_here"])
        self.assertFalse(hasattr(self.ext, "evaluate_alert_rule"))
        self.assertFalse(hasattr(self.ext, "record_alert_evaluation"))
        alert = self.ext.record_reported_alert(rule["id"], "triggered",
                                               ANALYST, note="pager report")
        self.assertEqual(alert["reported_status"], "triggered")
        self.assertFalse(alert["fired_here"])
        self.ext.record_reported_alert(rule["id"], "cleared", ANALYST)
        view = self.ext.alert_rule_view(rule["id"], VIEWER)
        self.assertEqual(view["reported_alert_count"], 2)
        self.assertEqual(view["alerts_by_status"],
                         {"triggered": 1, "cleared": 1})
        self.assertEqual(view["last_reported_status"], "cleared")
        self.assertNotIn("reported_alert_count", rule)

    def test_bad_reported_status_rejected(self):
        rule = self.ext.create_alert_rule(
            "r", self.ds, "revenue", "mean", "gt", 300, ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.record_reported_alert(rule["id"], "exploded", ANALYST)


# -- Cross-cutting: RBAC + audit -------------------------------------------------


class TestRbacAndAudit(BatchFixture):
    def test_viewer_mutation_denied_and_audited(self):
        """RBAC: viewer holds query/export only; a denied extension
        mutation is recorded on the core audit log as :denied (the
        FedRAMP-Low-side audit mapping of this tier)."""
        with self.assertRaises(PermissionDenied):
            self.ext.create_workspace("nope", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_create_workspace:denied", actions)

    def test_successful_mutations_audited_with_ext_prefix(self):
        self.ext.create_workspace("pod", ANALYST)
        self.ext.register_stream_reference("s", "src-1", ANALYST)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_create_workspace", actions)
        self.assertIn("ext_register_stream_reference", actions)


if __name__ == "__main__":
    unittest.main()
