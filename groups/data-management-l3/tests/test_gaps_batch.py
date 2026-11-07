"""Final GAPS batch tests — Group 28, Data Management L3-adjacent.

Pins the extension surface in ``src/datamgmt/extensions.py``
(``DataMgmtExtensions``, wrapping the core ``DataMgmtStore``): one
test class per open GAPS.md entry for this group (see ``../BATCH.md``
for the per-entry disposition, the long-tail enumeration, and the
retention re-judgment grounds), plus cross-cutting pins —
``ext_``-prefixed actions and ``:denied`` denials on the core audit
log, stub/transport labels on every reference record,
derived-never-stored values (storage views, capital totals, lineage
views), opaque-reference-only record shapes, and the batch's fresh
negative control: the case-decision separation-of-duties seam
``_check_case_decider_not_opener``.

The family forms follow the Group 12 (L2) batch unit's precedent;
three pins are specific to this tier's core: the ``auditor`` role
holds no permission anywhere on the extension surface (AC-5),
extension mutations are fail-closed when the audit write fails
(AU-5 -- the record and its id roll back), and extension entries
join the core's hash-chained audit log (AU-9).

Fixtures: ``make_store()`` (canonical dataset "Claims Extract" +
source "ehr-feed", created by STEWARD) from ``datamgmt_helpers``;
ADMIN=alice/admin, STEWARD=bob/steward, VIEWER=carol/viewer,
AUDITOR=dana/auditor.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from datamgmt_helpers import (
    ADMIN,
    AUDITOR,
    STEWARD,
    VIEWER,
    fresh_store,
    make_store,
)

from datamgmt.access import User
from datamgmt.audit import AuditLog
from datamgmt.errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from datamgmt.extensions import DataMgmtExtensions


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.dataset, self.source = make_store()
        self.ext = DataMgmtExtensions(self.store)
        self.ds = self.dataset["id"]
        self.src = self.source["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]


class TestStorageEngines(BatchFixture):
    """Entry: Distributed storage engines — built as storage records
    with derived capacity/state views; no engine runs."""

    def test_register_shape_and_ids(self):
        volume = self.ext.register_storage_volume(
            self.ds, "lake-main", "data_lake", STEWARD,
            capacity_units=500, replica_count=3)
        self.assertEqual(volume["id"], "stg-1")
        self.assertEqual(volume["state"], "registered")
        self.assertEqual(volume["engine_kind"], "data_lake")
        self.assertEqual(volume["created_by"], "bob")
        self.assertEqual(
            set(volume.keys()),
            {"id", "dataset_id", "name", "engine_kind",
             "capacity_units", "replica_count", "state",
             "created_by", "created_utc"})

    def test_bad_kind_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.register_storage_volume(
                self.ds, "tape-archive", "tape", STEWARD)
        volume = self.ext.register_storage_volume(
            self.ds, "lake-main", "data_lake", STEWARD)
        self.assertEqual(volume["id"], "stg-1")

    def test_unknown_dataset(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_storage_volume(
                "ds-99", "lake-main", "data_lake", STEWARD)

    def test_summary_derived_at_read(self):
        self.ext.register_storage_volume(
            self.ds, "lake-main", "data_lake", STEWARD,
            capacity_units=500, replica_count=2)
        self.ext.register_storage_volume(
            self.ds, "db-main", "database", STEWARD,
            capacity_units=300, replica_count=1)
        self.store.record_ingestion(self.ds, self.src, STEWARD,
                                     record_count=40)
        summary = self.ext.storage_summary(self.ds, ADMIN)
        self.assertEqual(summary["volumes"], 2)
        self.assertEqual(summary["by_engine"],
                         {"data_lake": 1, "database": 1})
        self.assertEqual(summary["total_capacity_units"], 800)
        self.assertEqual(summary["capacity_reported_for"], 2)
        self.assertEqual(summary["total_replicas"], 3)
        self.assertEqual(summary["ingested_records"], 40)
        self.assertEqual(summary["state"], "metadata_only")
        self.assertIs(summary["engine_executed"], False)

    def test_summary_partial_capacity_is_none_not_invented(self):
        self.ext.register_storage_volume(
            self.ds, "lake-main", "warehouse", STEWARD)
        summary = self.ext.storage_summary(self.ds, ADMIN)
        self.assertIsNone(summary["total_capacity_units"])
        self.assertEqual(summary["capacity_reported_for"], 0)

    def test_viewer_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_storage_volume(
                self.ds, "lake-main", "data_lake", VIEWER)
        self.assertIn("ext_storage_register:denied", self.audit_actions())


class TestLinkageAndDeidentification(BatchFixture):
    """Entry: PPRL record-linkage engine & de-identification engines —
    built as reported linkage pairs between opaque refs and method
    declarations; no identifier is held and nothing is transformed."""

    def test_linkage_report_shape(self):
        report = self.ext.record_linkage_report(
            self.ds, "party-ref-a", "party-ref-b",
            "reported_token_match", STEWARD)
        self.assertEqual(report["id"], "lnk-1")
        self.assertIs(report["match_computed_here"], False)
        self.assertEqual(
            set(report.keys()),
            {"id", "dataset_id", "left_ref", "right_ref", "method",
             "ingestion_id", "match_computed_here", "created_by",
             "created_utc"})

    def test_same_ref_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.record_linkage_report(
                self.ds, "party-ref-a", "party-ref-a",
                "reported_token_match", STEWARD)
        report = self.ext.record_linkage_report(
            self.ds, "party-ref-a", "party-ref-b",
            "reported_token_match", STEWARD)
        self.assertEqual(report["id"], "lnk-1")

    def test_linkage_ingestion_must_belong_to_dataset(self):
        other = self.store.create_dataset("Other", "desc", STEWARD)
        ingestion = self.store.record_ingestion(
            other["id"], self.src, STEWARD, record_count=1)
        with self.assertRaises(ValidationError):
            self.ext.record_linkage_report(
                self.ds, "party-ref-a", "party-ref-b",
                "reported_token_match", STEWARD,
                ingestion_id=ingestion["id"])

    def test_linkage_summary_derived(self):
        self.ext.record_linkage_report(
            self.ds, "ref-a", "ref-b", "reported_token_match", STEWARD)
        self.ext.record_linkage_report(
            self.ds, "ref-b", "ref-c", "reported_cohort_overlap",
            STEWARD)
        summary = self.ext.linkage_summary(self.ds, ADMIN)
        self.assertEqual(summary["reports"], 2)
        self.assertEqual(summary["distinct_refs"], 3)
        self.assertEqual(
            summary["by_method"],
            {"reported_cohort_overlap": 1, "reported_token_match": 1})
        self.assertIs(summary["match_computed_here"], False)

    def test_deidentification_declaration_transforms_nothing(self):
        declaration = self.ext.declare_deidentification(
            self.ds, "expert_certification", STEWARD,
            basis="certifier-ref-7")
        self.assertEqual(declaration["id"], "dei-1")
        self.assertIs(declaration["applied_here"], False)
        self.assertEqual(declaration["records_transformed"], 0)
        with self.assertRaises(ValidationError):
            self.ext.declare_deidentification(
                self.ds, "magic_scrub", STEWARD)


class TestQueryAndVisualization(BatchFixture):
    """Entry: Query & visualization engines — built as registered
    deterministic derivations over supplied batches (the core
    quality-check shape) plus definition-only visualizations whose
    views derive from stored run records."""

    RECORDS = [
        {"status": "open", "amount": 10},
        {"status": "closed", "amount": 20},
        {"status": "open", "amount": True},
        {"status": "open"},
    ]

    def test_count_by_field_run(self):
        query = self.ext.define_query(
            "by-status", self.ds, "count_by_field", STEWARD,
            field="status")
        self.assertEqual(query["id"], "qry-1")
        self.assertNotIn("result", query)
        run = self.ext.run_query(query["id"], self.RECORDS, STEWARD)
        self.assertEqual(run["id"], "qrs-1")
        self.assertEqual(run["result"],
                         {"counts": {"closed": 1, "open": 3}})
        self.assertEqual(run["records_evaluated"], 4)
        self.assertEqual(run["records_matched"], 4)
        self.assertEqual(run["method"], "deterministic_derivation")

    def test_sum_field_skips_bools_and_missing(self):
        query = self.ext.define_query(
            "amount-total", self.ds, "sum_field", STEWARD,
            field="amount")
        run = self.ext.run_query(query["id"], self.RECORDS, STEWARD)
        self.assertEqual(run["result"], {"sum": 30,
                                         "values_considered": 2,
                                         "values_skipped": 2})

    def test_filter_restricts_evaluation(self):
        query = self.ext.define_query(
            "open-count", self.ds, "count_records", STEWARD,
            field="status", has_filter=True, value_equals="open")
        run = self.ext.run_query(query["id"], self.RECORDS, STEWARD)
        self.assertEqual(run["result"], {"count": 3})
        self.assertEqual(run["records_matched"], 3)

    def test_field_required_for_field_kinds(self):
        with self.assertRaises(ValidationError):
            self.ext.define_query(
                "bad", self.ds, "sum_field", STEWARD)

    def test_viewer_may_not_run_queries(self):
        query = self.ext.define_query(
            "by-status", self.ds, "count_by_field", STEWARD,
            field="status")
        with self.assertRaises(PermissionDenied):
            self.ext.run_query(query["id"], self.RECORDS, VIEWER)
        self.assertIn("ext_query_run:denied", self.audit_actions())

    def test_visualization_view_derives_from_runs(self):
        query = self.ext.define_query(
            "by-status", self.ds, "count_by_field", STEWARD,
            field="status")
        viz = self.ext.define_visualization(
            "status-chart", query["id"], "bar", STEWARD)
        self.assertIs(viz["definition_only"], True)
        view = self.ext.render_visualization(viz["id"], ADMIN)
        self.assertIsNone(view["series"])
        self.assertEqual(view["runs_available"], 0)
        self.assertIs(view["executes_query"], False)
        run = self.ext.run_query(query["id"], self.RECORDS, STEWARD)
        view = self.ext.render_visualization(viz["id"], ADMIN)
        self.assertEqual(view["series"], run["result"])
        self.assertEqual(view["latest_run_id"], run["id"])
        self.assertEqual(view["runs_available"], 1)
        self.assertEqual(view["rendered_from"],
                         "stored_query_run_records")


class TestInspectionAndCapitalPlanning(BatchFixture):
    """Entry: Asset inspection & capital-planning applications —
    built as inspection outcome records and capital plan records
    with totals derived at read."""

    def test_inspection_summary_derived(self):
        self.ext.record_inspection(
            "asset-ref-1", self.ds, "satisfactory", STEWARD,
            finding_count=0)
        self.ext.record_inspection(
            "asset-ref-1", self.ds, "deficient", STEWARD,
            finding_count=3)
        self.ext.record_inspection(
            "asset-ref-2", self.ds, "critical", STEWARD,
            finding_count=2)
        summary = self.ext.inspection_summary(self.ds, ADMIN)
        self.assertEqual(summary["inspections"], 3)
        self.assertEqual(summary["assets_inspected"], 2)
        self.assertEqual(summary["total_findings"], 5)
        self.assertEqual(summary["by_outcome"],
                         {"critical": 1, "deficient": 1,
                          "satisfactory": 1})

    def test_bad_outcome_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.record_inspection(
                "asset-ref-1", self.ds, "shiny", STEWARD)

    def test_capital_totals_derived_never_stored(self):
        plan = self.ext.create_capital_plan(
            "Bridge program", STEWARD, horizon_years=5)
        self.ext.add_capital_item(plan["id"], "Deck renewal", 10000,
                                  STEWARD, year_offset=1)
        self.ext.add_capital_item(plan["id"], "Pier repair", 25050,
                                  STEWARD, year_offset=2)
        self.ext.add_capital_item(plan["id"], "Lighting", 5000,
                                  STEWARD, year_offset=2)
        stored = self.ext.get_capital_plan(plan["id"], ADMIN)
        self.assertNotIn("total_cents", stored)
        self.assertNotIn("by_year", stored)
        view = self.ext.capital_plan_view(plan["id"], ADMIN)
        self.assertEqual(view["total_cents"], 40050)
        self.assertEqual(view["by_year"], {1: 10000, 2: 30050})
        self.assertEqual(view["item_count"], 3)

    def test_money_boundary_rejects_float_and_bool_no_id(self):
        plan = self.ext.create_capital_plan(
            "Bridge program", STEWARD, horizon_years=5)
        with self.assertRaises(ValidationError):
            self.ext.add_capital_item(plan["id"], "Deck", 10.5,
                                      STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.add_capital_item(plan["id"], "Deck", True,
                                      STEWARD)
        item = self.ext.add_capital_item(plan["id"], "Deck", 100,
                                         STEWARD)
        self.assertEqual(item["id"], "cit-1")

    def test_year_beyond_horizon_rejected(self):
        plan = self.ext.create_capital_plan(
            "Bridge program", STEWARD, horizon_years=5)
        with self.assertRaises(ValidationError):
            self.ext.add_capital_item(plan["id"], "Deck", 100,
                                      STEWARD, year_offset=6)


class TestCaseManagement(BatchFixture):
    """Entry: Case management depth (vetting / adjudication) — built
    as case records with evidence references and a decision workflow
    under separation of duties."""

    def test_open_case_shape(self):
        case = self.ext.open_case("subject-ref-1", "vetting", VIEWER,
                                  dataset_id=self.ds)
        self.assertEqual(case["id"], "case-1")
        self.assertEqual(case["status"], "open")
        self.assertEqual(case["opened_by"], "carol")
        self.assertIsNone(case["outcome"])
        self.assertEqual(
            set(case.keys()),
            {"id", "subject_ref", "kind", "dataset_id", "status",
             "opened_by", "outcome", "decision_id", "decided_by",
             "decided_utc", "created_by", "created_utc"})

    def test_evidence_and_decision_flow(self):
        case = self.ext.open_case("subject-ref-1", "adjudication",
                                  STEWARD, dataset_id=self.ds)
        evidence = self.ext.record_case_evidence(
            case["id"], "evidence-ref-1", ADMIN)
        self.assertEqual(evidence["id"], "cev-1")
        decided = self.ext.decide_case(case["id"], "favorable", ADMIN,
                                       reason="complete file")
        self.assertEqual(decided["status"], "decided")
        self.assertEqual(decided["outcome"], "favorable")
        self.assertEqual(decided["decision_id"], "cde-1")
        self.assertEqual(decided["decided_by"], "alice")
        decisions = self.ext.list_case_decisions(case["id"], ADMIN)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["outcome"], "favorable")

    def test_evidence_after_decision_rejected(self):
        case = self.ext.open_case("subject-ref-1", "vetting", STEWARD)
        self.ext.decide_case(case["id"], "unfavorable", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_case_evidence(
                case["id"], "evidence-ref-2", ADMIN)

    def test_self_decision_denied_canonical(self):
        case = self.ext.open_case("subject-ref-1", "vetting", STEWARD)
        with self.assertRaises(PermissionDenied):
            self.ext.decide_case(case["id"], "favorable", STEWARD)
        after = self.ext.get_case(case["id"], ADMIN)
        self.assertEqual(after["status"], "open")
        self.assertEqual(self.ext.list_case_decisions(case["id"],
                                                      ADMIN), [])

    def test_viewer_may_not_decide(self):
        case = self.ext.open_case("subject-ref-1", "vetting", STEWARD)
        with self.assertRaises(PermissionDenied):
            self.ext.decide_case(case["id"], "favorable", VIEWER)
        self.assertIn("ext_case_decide:denied", self.audit_actions())


class MutantDataMgmtExtensions(DataMgmtExtensions):
    """Mutant decision path: the case SoD check is skipped."""

    def _check_case_decider_not_opener(self, case, actor):
        """Batch negative control mutant -- no-op: self-decision is
        never checked."""
        return None


class TestCaseNegativeControl(unittest.TestCase):
    """Fresh negative control for the batch: case decisions are
    never self-decided (separation of duties, AC-5 -- the same
    doctrine as the core's ``_check_decider_not_requester``).

    Each leg asserts (1) the canonical expectation from the real
    implementation, (2) the mutant would NOT produce it, and (3)
    treating the mutant's outcome as the expected outcome fails.
    The viewer-opener leg uses a name-identical decider holding
    ``access_decide`` so the SoD seam is the only gate that can
    deny, exactly as the core's negative control isolates its
    guard.
    """

    def _fixture(self, ext_class):
        store = fresh_store()
        dataset = store.create_dataset("Claims Extract", "desc",
                                       STEWARD)
        return store, ext_class(store), dataset["id"]

    def test_name_identical_self_decision(self):
        # Canonical: a decider whose name matches the opener is
        # denied by the seam even when their role may decide.
        store, ext, ds = self._fixture(DataMgmtExtensions)
        case = ext.open_case("subject-ref-1", "vetting", VIEWER,
                             dataset_id=ds)
        with self.assertRaises(PermissionDenied):
            ext.decide_case(case["id"], "favorable",
                            User("carol", "steward"))
        self.assertEqual(ext.get_case(case["id"], ADMIN)["status"],
                         "open")
        self.assertEqual(ext.list_case_decisions(case["id"], ADMIN),
                         [])

        # Mutant: the same self-decision succeeds and mints the
        # decision the real surface must never mint.
        _, mutant, mds = self._fixture(MutantDataMgmtExtensions)
        mcase = mutant.open_case("subject-ref-1", "vetting", VIEWER,
                                 dataset_id=mds)
        decided = mutant.decide_case(
            mcase["id"], "favorable", User("carol", "steward"))
        self.assertEqual(decided["status"], "decided")
        self.assertEqual(
            len(mutant.list_case_decisions(mcase["id"], ADMIN)), 1)

        # Treating the mutant's outcome as the expectation fails.
        with self.assertRaises(AssertionError):
            self.assertEqual(decided["status"], "open")


class TestFieldLevelLineage(BatchFixture):
    """Entry: Field-level / transformation lineage — built as
    declared transformation-step records joined at read with the
    core's ingestion-granularity provenance."""

    def setUp(self):
        super().setUp()
        self.ingestion = self.store.record_ingestion(
            self.ds, self.src, STEWARD, record_count=25)

    def test_step_shape(self):
        step = self.ext.record_transformation_step(
            self.ds, self.ingestion["id"], "mask", "patient_id",
            STEWARD)
        self.assertEqual(step["id"], "stp-1")
        self.assertIs(step["executed_here"], False)

    def test_step_ingestion_must_belong_to_dataset(self):
        other = self.store.create_dataset("Other", "desc", STEWARD)
        foreign = self.store.record_ingestion(
            other["id"], self.src, STEWARD, record_count=1)
        with self.assertRaises(ValidationError):
            self.ext.record_transformation_step(
                self.ds, foreign["id"], "mask", "patient_id", STEWARD)

    def test_field_lineage_derived(self):
        self.ext.record_transformation_step(
            self.ds, self.ingestion["id"], "rename", "patient_id",
            STEWARD, source_field="pat_id")
        self.ext.record_transformation_step(
            self.ds, self.ingestion["id"], "mask", "patient_id",
            STEWARD)
        self.ext.record_transformation_step(
            self.ds, self.ingestion["id"], "derive", "amount",
            STEWARD)
        view = self.ext.field_lineage(self.ds, "patient_id", ADMIN)
        self.assertEqual(view["step_count"], 2)
        self.assertEqual(view["step_kinds"], ["mask", "rename"])
        self.assertEqual(view["ingestions_referenced"],
                         [self.ingestion["id"]])
        self.assertEqual(view["total_records_ingested"], 25)
        self.assertEqual(view["granularity"],
                         "field_level_declared_steps")
        self.assertEqual(view["core_provenance_granularity"],
                         "ingestion")


class TestRetentionDisposition(BatchFixture):
    """Entry: Retention disposition execution — RE-JUDGED to a
    labeled reference implementation (grounds in ../BATCH.md):
    disposition decision records with eligibility derived from the
    core schedules, plus execution reference records that execute
    nothing. The dataset is never deleted or archived."""

    def _later(self, days):
        created = datetime.fromisoformat(
            self.dataset["created_utc"].replace("Z", "+00:00"))
        return (created + timedelta(days=days)).isoformat()

    def test_decision_requires_core_policy(self):
        with self.assertRaises(ValidationError):
            self.ext.record_disposition_decision(
                self.ds, "approve", STEWARD)

    def test_eligible_decision_and_execution_reference(self):
        self.store.set_retention_policy(self.ds, 30, "delete",
                                        STEWARD)
        decision = self.ext.record_disposition_decision(
            self.ds, "approve", STEWARD, now=self._later(40))
        self.assertEqual(decision["id"], "ddc-1")
        self.assertIs(decision["eligible"], True)
        self.assertEqual(decision["age_days"], 40)
        self.assertEqual(decision["disposition"], "delete")
        self.assertIs(decision["reference_stub"], True)
        self.assertIs(decision["disposition_executed"], False)
        # Nothing was executed: the dataset and its policy remain.
        self.assertEqual(
            self.store.get_dataset(self.ds, ADMIN)["id"], self.ds)
        self.assertIsNotNone(
            self.store.retention_policy_for(self.ds, ADMIN))
        reference = self.ext.record_disposition_execution_reference(
            decision["id"], STEWARD, target_ref="archive-ref-1")
        self.assertEqual(reference["id"], "dex-1")
        self.assertIs(reference["executed"], False)
        self.assertIsNone(reference["executed_by"])
        self.assertIs(reference["reference_stub"], True)
        self.assertEqual(reference["status"],
                         "recorded_reference_only")

    def test_legal_hold_never_eligible(self):
        other = self.store.create_dataset("Held", "desc", STEWARD)
        self.store.set_retention_policy(
            other["id"], 30, "archive", STEWARD, legal_hold=True)
        created = datetime.fromisoformat(
            other["created_utc"].replace("Z", "+00:00"))
        later = (created + timedelta(days=40)).isoformat()
        decision = self.ext.record_disposition_decision(
            other["id"], "approve", STEWARD, now=later)
        self.assertIs(decision["eligible"], False)
        self.assertIs(decision["legal_hold"], True)

    def test_execution_reference_requires_approval(self):
        self.store.set_retention_policy(self.ds, 30, "review",
                                        STEWARD)
        decision = self.ext.record_disposition_decision(
            self.ds, "defer", STEWARD, now=self._later(40))
        with self.assertRaises(ValidationError):
            self.ext.record_disposition_execution_reference(
                decision["id"], STEWARD)

    def test_viewer_may_not_decide_disposition(self):
        self.store.set_retention_policy(self.ds, 30, "delete",
                                        STEWARD)
        with self.assertRaises(PermissionDenied):
            self.ext.record_disposition_decision(
                self.ds, "approve", VIEWER, now=self._later(40))
        self.assertIn("ext_disposition_decision:denied",
                      self.audit_actions())


class TestStubEngineLabels(BatchFixture):
    """Stub-engine entries: every record is a labeled reference
    implementation (``reference_stub: True``; transfers carry
    ``reference_transport: True``) and nothing executes."""

    def test_integration_runtime_connector(self):
        connector = self.ext.register_connector(
            "ehr-connector", "ehr-system-ref", STEWARD,
            direction="inbound")
        self.assertIs(connector["reference_stub"], True)
        self.assertEqual(connector["status"],
                         "recorded_reference_only")
        run = self.ext.record_connector_run(
            connector["id"], "reported_success", STEWARD,
            records_reported=12)
        self.assertIs(run["reference_stub"], True)
        self.assertIs(run["executed_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.record_connector_run(
                "con-99", "reported_success", STEWARD)

    def test_search_indexing(self):
        index = self.ext.define_search_index(
            "catalog-index", STEWARD, dataset_id=self.ds)
        self.assertIs(index["reference_stub"], True)
        snapshot = self.ext.record_index_snapshot(
            index["id"], 4200, STEWARD)
        self.assertIs(snapshot["reference_stub"], True)
        self.assertIs(snapshot["indexed_here"], False)
        # The core's metadata search is untouched and still the
        # only search that runs.
        self.assertEqual(
            self.store.search("claims", ADMIN)["datasets"][0]["id"],
            self.ds)

    def test_content_processing(self):
        job = self.ext.register_processing_job(
            "ocr", self.ds, STEWARD)
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["outputs_held"], False)
        output = self.ext.record_processing_output(
            job["id"], "output-ref-1", STEWARD)
        self.assertIs(output["reference_stub"], True)
        self.assertIs(output["content_held"], False)
        with self.assertRaises(NotFoundError):
            self.ext.record_processing_output(
                "prc-99", "output-ref-2", STEWARD)

    def test_workflow_definitions_never_execute(self):
        workflow = self.ext.define_workflow(
            "intake-flow", STEWARD, steps=["collect", "review"])
        self.assertIs(workflow["reference_stub"], True)
        self.assertIs(workflow["executed"], False)
        interview = self.ext.define_guided_interview(
            "intake-interview", STEWARD, workflow_id=workflow["id"],
            questions=["What changed?"])
        self.assertIs(interview["reference_stub"], True)
        with self.assertRaises(ValidationError):
            self.ext.define_workflow("bad", STEWARD, steps=[""])
        with self.assertRaises(NotFoundError):
            self.ext.define_guided_interview(
                "orphan", STEWARD, workflow_id="wfl-99")

    def test_hosting(self):
        hosting = self.ext.record_hosting(
            "private_cloud", "gov-region-ref", STEWARD)
        self.assertIs(hosting["reference_stub"], True)
        self.assertIs(hosting["hosted_here"], False)

    def test_kubernetes_clusters(self):
        cluster = self.ext.register_cluster(
            "palette-cluster", STEWARD, blueprint_ref="bp-ref-1")
        self.assertIs(cluster["reference_stub"], True)
        self.assertIs(cluster["provisioned_here"], False)
        event = self.ext.record_cluster_lifecycle(
            cluster["id"], "upgrade_reported", STEWARD)
        self.assertIs(event["reference_stub"], True)
        self.assertIs(event["performed_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.record_cluster_lifecycle(
                "clu-99", "upgrade_reported", STEWARD)

    def test_ai_ml_models(self):
        model = self.ext.register_model(
            "grid-analytics", STEWARD, dataset_id=self.ds,
            technique="classification")
        self.assertIs(model["reference_stub"], True)
        self.assertEqual(model["method"],
                         "recorded_declaration_only")
        self.assertIs(model["trained_here"], False)
        self.assertIs(model["inference_here"], False)
        step = self.ext.record_orchestration(
            model["id"], "nightly bundle run (reported)", STEWARD)
        self.assertIs(step["reference_stub"], True)
        self.assertIs(step["executed_here"], False)


class TestFileTransfer(BatchFixture):
    """Entry: Managed file transfer transport — ingestion-shaped
    records carrying ``reference_transport: True``; no file moves."""

    def test_transfer_record_labels(self):
        transfer = self.ext.record_file_transfer(
            self.ds, self.src, STEWARD, record_count=120,
            checksum="abc123", protocol="sftp")
        self.assertEqual(transfer["id"], "trf-1")
        self.assertIs(transfer["reference_transport"], True)
        self.assertIs(transfer["moved_here"], False)
        self.assertEqual(transfer["status"],
                         "recorded_reference_only")

    def test_unknown_source_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_file_transfer(
                self.ds, "src-99", STEWARD)

    def test_bad_protocol_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.record_file_transfer(
                self.ds, self.src, STEWARD, protocol="ftp-plain")


class TestCrossCutting(BatchFixture):
    """Cross-cutting pins for the whole extension surface."""

    def test_ext_actions_recorded_on_core_audit(self):
        self.ext.register_storage_volume(
            self.ds, "lake-main", "data_lake", STEWARD)
        self.ext.record_linkage_report(
            self.ds, "ref-a", "ref-b", "reported_token_match",
            STEWARD)
        actions = self.audit_actions()
        self.assertIn("ext_storage_register", actions)
        self.assertIn("ext_linkage_record", actions)

    def test_denied_attempt_audited_and_no_state_change(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_capital_plan("Nope", VIEWER)
        self.assertIn("ext_capital_plan_create:denied",
                      self.audit_actions())
        self.assertEqual(self.ext.list_capital_plans(ADMIN), [])

    def test_unknown_extension_record(self):
        with self.assertRaises(NotFoundError):
            self.ext.get_storage_volume("stg-99", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.get_case("case-99", ADMIN)

    def test_ext_entries_join_the_hash_chain(self):
        """AU-9 at this tier: extension mutations are ordinary
        entries on the core's hash-chained audit log -- they carry
        chain fields and the chain verifies over them."""
        self.ext.register_storage_volume(
            self.ds, "lake-main", "data_lake", STEWARD)
        entries = [e for e in self.store.audit.entries()
                   if e["action"].startswith("ext_")]
        self.assertTrue(entries)
        for entry in entries:
            self.assertIn("seq", entry)
            self.assertIn("prev_hash", entry)
            self.assertIn("hash", entry)
        self.assertEqual(self.store.audit.verify_chain(), (True, None))


class TestAuditorRoleSurface(BatchFixture):
    """AC-5 at this tier: the auditor role holds ``audit_read`` and
    nothing else, so it holds no permission anywhere on the
    extension surface -- every extension read/write maps onto an
    operational core action -- exactly as at the core store layer.
    Its denials are audited like any other."""

    def test_auditor_denied_extension_write(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_storage_volume(
                self.ds, "lake-main", "data_lake", AUDITOR)
        self.assertIn("ext_storage_register:denied",
                      self.audit_actions())
        self.assertEqual(self.ext.list_storage_volumes(self.ds, ADMIN),
                         [])

    def test_auditor_denied_extension_reads(self):
        volume = self.ext.register_storage_volume(
            self.ds, "lake-main", "data_lake", STEWARD)
        with self.assertRaises(PermissionDenied):
            self.ext.get_storage_volume(volume["id"], AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.storage_summary(self.ds, AUDITOR)
        self.assertIn("ext_storage_read:denied", self.audit_actions())

    def test_auditor_denied_case_decision(self):
        case = self.ext.open_case("subject-ref-1", "vetting", STEWARD)
        with self.assertRaises(PermissionDenied):
            self.ext.decide_case(case["id"], "favorable", AUDITOR)
        self.assertIn("ext_case_decide:denied", self.audit_actions())


class TestFailClosedExtensions(unittest.TestCase):
    """AU-5 at this tier: an extension mutation whose audit write
    fails does not proceed -- the record is absent and its id is
    not consumed, mirroring the core store's ``_atomic`` rollback.
    The broken log is produced exactly as in ``test_audit_failure``:
    the JSONL file is replaced by a directory so the append raises.
    """

    def test_failed_audit_write_rolls_back_record_and_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store, dataset, _source = make_store(audit=audit)
            ext = DataMgmtExtensions(store)
            ds = dataset["id"]
            # Break the log: the append now raises OSError.
            os.remove(path)
            os.mkdir(path)
            with self.assertRaises(AuditWriteError):
                ext.register_storage_volume(
                    ds, "lake-main", "data_lake", STEWARD)
            # No record exists (read over the in-memory surface;
            # the broken file only blocks writes).
            self.assertEqual(ext.list_storage_volumes(ds, ADMIN), [])
            with self.assertRaises(NotFoundError):
                ext.get_storage_volume("stg-1", ADMIN)
            # Repair the log; the retried mutation takes the id the
            # failed attempt rolled back, and the chain verifies.
            os.rmdir(path)
            volume = ext.register_storage_volume(
                ds, "lake-main", "data_lake", STEWARD)
            self.assertEqual(volume["id"], "stg-1")
            self.assertEqual(audit.verify_chain(), (True, None))


if __name__ == "__main__":
    unittest.main()
