"""Final GAPS batch tests for the Data Management untiered set.

Traces to: the 10 open Extended entries of this set's union spec
(``UNION-SPEC.md`` gap list, GAPS.md section "Untiered Set 5 --
Data Management (8 forks, tier null)"), closed by
``datamgmt/extensions.py`` under ``../../gaps-batch/DECISION.md``:
6 built as records/derivations in-substrate, 4 shipped as labeled
reference implementations.

Every test names the entry it pins. Cross-cutting pins: tier null
binds the whole extension surface (a recursive scan finds no
tier-shaped key, no float, and no numeric list -- a vector value --
in any extension record or view); stub records carry
``reference_stub: True`` (transfers ``reference_transport: True``);
denied attempts are audited ``ext_<action>:denied``; failed
operations consume no id.

The fresh negative control is in
:class:`TestAbacMatchNegativeControl`: the ABAC presence-match
seam ``DataMgmtExtensions._attributes_satisfy`` mutated to wave
every subject through must not produce the canonical outcome.
"""

import unittest

from datamgmt.errors import NotFoundError, PermissionDenied, ValidationError
from datamgmt.extensions import DataMgmtExtensions

from datamgmt_helpers import ADMIN, STEWARD, VIEWER, fresh_store, make_store


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.dataset, self.source = make_store()
        self.ext = DataMgmtExtensions(self.store)
        self.ds = self.dataset["id"]
        self.src = self.source["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]


def _walk(value):
    """Yield every (key, value) pair and scalar in a record/view."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


class TestVectorCollections(BatchFixture):
    """Entry: Vector database & embedding index engine (built).

    Definitions plus reported job counts; no vector value exists
    in any shape and no embedding is computed here.
    """

    def test_collection_definition_shape_and_labels(self):
        coll = self.ext.define_vector_collection(
            "docs-vectors", STEWARD, dataset_id=self.ds,
            dimension=1536, metric="cosine")
        self.assertEqual(coll["id"], "vcol-1")
        self.assertEqual(
            set(coll.keys()),
            {"id", "name", "dataset_id", "dimension_reported", "metric",
             "definition_only", "embeddings_computed_here",
             "created_by", "created_utc"})
        self.assertIs(coll["definition_only"], True)
        self.assertIs(coll["embeddings_computed_here"], False)
        self.assertEqual(coll["dimension_reported"], 1536)

    def test_no_parameter_accepts_a_vector_value(self):
        with self.assertRaises(TypeError):
            self.ext.define_vector_collection(
                "x", STEWARD, dataset_id=self.ds, vector=[0.1, 0.2])
        coll = self.ext.define_vector_collection("x", STEWARD)
        with self.assertRaises(TypeError):
            self.ext.record_embedding_job(
                coll["id"], STEWARD, embedding=[0.1, 0.2])
        with self.assertRaises(TypeError):
            self.ext.record_embedding_job(
                coll["id"], STEWARD, vectors=[[0.1, 0.2]])

    def test_embedding_job_counts_as_reported(self):
        coll = self.ext.define_vector_collection("c", STEWARD)
        job = self.ext.record_embedding_job(
            coll["id"], STEWARD, documents_reported=1200,
            embeddings_reported=1200)
        self.assertEqual(job["id"], "emb-1")
        self.assertEqual(job["documents_reported"], 1200)
        self.assertIs(job["embeddings_computed_here"], False)
        self.assertEqual(job["status"], "recorded_report")

    def test_validation_and_no_id_on_failure(self):
        with self.assertRaises(ValidationError):
            self.ext.define_vector_collection(
                "c", STEWARD, dataset_id=self.ds, dimension=True)
        with self.assertRaises(ValidationError):
            self.ext.define_vector_collection(
                "c", STEWARD, dataset_id=self.ds, dimension=0)
        with self.assertRaises(ValidationError):
            self.ext.define_vector_collection(
                "c", STEWARD, dataset_id=self.ds, metric="manhattan")
        with self.assertRaises(NotFoundError):
            self.ext.define_vector_collection(
                "c", STEWARD, dataset_id="ds-999")
        coll = self.ext.define_vector_collection("c", STEWARD)
        self.assertEqual(coll["id"], "vcol-1")
        with self.assertRaises(ValidationError):
            self.ext.record_embedding_job(
                coll["id"], STEWARD, documents_reported=-1)
        job = self.ext.record_embedding_job(coll["id"], STEWARD)
        self.assertEqual(job["id"], "emb-1")

    def test_viewer_may_not_define(self):
        with self.assertRaises(PermissionDenied):
            self.ext.define_vector_collection("c", VIEWER)
        self.assertIn("ext_vector_collection_define:denied",
                      self.audit_actions())


class TestWarehouses(BatchFixture):
    """Entry: Petabyte-scale warehouse & analytics engine (built).

    Configuration records plus reported run counts; the scale
    label is the platform's own, recorded verbatim; no data held.
    """

    def test_warehouse_shape_and_scale_label_verbatim(self):
        wrh = self.ext.register_warehouse(
            "ocient-main", STEWARD, scale_label="petabyte-scale",
            dataset_id=self.ds)
        self.assertEqual(wrh["id"], "wrh-1")
        self.assertEqual(
            set(wrh.keys()),
            {"id", "name", "dataset_id", "scale_label_reported",
             "data_held_here", "status", "created_by", "created_utc"})
        self.assertEqual(wrh["scale_label_reported"], "petabyte-scale")
        self.assertIs(wrh["data_held_here"], False)

    def test_query_run_counts_as_reported(self):
        wrh = self.ext.register_warehouse("w", STEWARD)
        run = self.ext.record_warehouse_query_run(
            wrh["id"], STEWARD, rows_reported=42)
        self.assertEqual(run["id"], "wqr-1")
        self.assertIs(run["executed_here"], False)
        self.assertIs(run["data_held_here"], False)

    def test_summary_derived_at_read_not_stored(self):
        wrh = self.ext.register_warehouse("w", STEWARD)
        self.ext.record_warehouse_query_run(wrh["id"], STEWARD,
                                            rows_reported=10)
        self.ext.record_warehouse_query_run(wrh["id"], STEWARD,
                                            rows_reported=32)
        stored = self.ext.get_warehouse(wrh["id"], STEWARD)
        self.assertNotIn("rows_reported_total", stored)
        self.assertNotIn("query_runs", stored)
        summary = self.ext.warehouse_summary(wrh["id"], STEWARD)
        self.assertEqual(summary["query_runs"], 2)
        self.assertEqual(summary["rows_reported_total"], 42)
        self.assertIs(summary["derived_at_read"], True)

    def test_unknown_warehouse_and_bad_counts(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_warehouse_query_run("wrh-9", STEWARD)
        wrh = self.ext.register_warehouse("w", STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.record_warehouse_query_run(
                wrh["id"], STEWARD, rows_reported=1.5)


class TestGraphPlatform(BatchFixture):
    """Entry: Enterprise architecture graph platform (built).

    Node/edge records over opaque refs; degrees derived at read.
    """

    def _nodes(self):
        a = self.ext.register_graph_node("app-orders", "application",
                                         STEWARD)
        b = self.ext.register_graph_node("db-orders", "database", STEWARD)
        c = self.ext.register_graph_node("svc-api", "service", STEWARD)
        return a, b, c

    def test_degrees_derived_at_read_not_stored(self):
        a, b, c = self._nodes()
        self.ext.record_graph_edge(a["id"], b["id"], "reads_from", STEWARD)
        self.ext.record_graph_edge(c["id"], a["id"], "calls", STEWARD)
        self.ext.record_graph_edge(c["id"], b["id"], "writes_to", STEWARD)
        stored = self.ext.get_graph_node(a["id"], STEWARD)
        self.assertEqual(
            set(stored.keys()),
            {"id", "node_ref", "kind_label", "dataset_id",
             "created_by", "created_utc"})
        view = self.ext.graph_node_view(a["id"], STEWARD)
        self.assertEqual(view["out_degree"], 1)
        self.assertEqual(view["in_degree"], 1)
        self.assertEqual(view["degree"], 2)
        self.assertIs(view["derived_at_read"], True)
        view_b = self.ext.graph_node_view(b["id"], STEWARD)
        self.assertEqual(view_b["in_degree"], 2)
        self.assertEqual(view_b["out_degree"], 0)

    def test_duplicate_node_ref_rejected_no_id_consumed(self):
        self.ext.register_graph_node("dup", "application", STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.register_graph_node("dup", "database", STEWARD)
        node = self.ext.register_graph_node("other", "database", STEWARD)
        self.assertEqual(node["id"], "gnod-2")

    def test_edge_requires_registered_nodes(self):
        a, _b, _c = self._nodes()
        with self.assertRaises(NotFoundError):
            self.ext.record_graph_edge(a["id"], "gnod-99", "calls",
                                       STEWARD)
        self.assertEqual(self.ext.list_graph_edges(actor=STEWARD), [])


class MutantExtensions(DataMgmtExtensions):
    """The drill mutant: the ABAC seam waves every subject through."""

    @staticmethod
    def _attributes_satisfy(required_attributes, present_attributes):
        return True


class TestAbac(BatchFixture):
    """Entry: Policy enforcement plane & ABAC engine (built).

    Policy definitions held as data; subject attributes recorded
    as names present; decision outcomes derived at read by the
    seam ``_attributes_satisfy``; enforcement not performed.
    """

    def _policy(self, required=("clearance", "need_to_know")):
        return self.ext.define_abac_policy(
            "cui-access", self.ds, list(required), STEWARD)

    def test_policy_definition_shape(self):
        policy = self._policy()
        self.assertEqual(policy["id"], "abac-1")
        self.assertEqual(
            set(policy.keys()),
            {"id", "name", "dataset_id", "required_attributes", "effect",
             "definition_only", "enforced_here",
             "created_by", "created_utc"})
        self.assertIs(policy["definition_only"], True)
        self.assertIs(policy["enforced_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.define_abac_policy("empty", self.ds, [], STEWARD)
        with self.assertRaises(NotFoundError):
            self.ext.define_abac_policy("ghost", "ds-999", ["a"], STEWARD)

    def test_decision_outcome_derived_at_read_not_stored(self):
        policy = self._policy()
        self.ext.record_subject_attributes(
            "subject-7", ["clearance"], STEWARD)
        decision = self.ext.record_abac_decision(
            policy["id"], "subject-7", STEWARD)
        self.assertEqual(decision["id"], "abdec-1")
        self.assertEqual(
            set(decision.keys()),
            {"id", "policy_id", "dataset_id", "subject_ref",
             "enforced_here", "status", "created_by", "created_utc"})
        view = self.ext.abac_decision_view(decision["id"], STEWARD)
        self.assertIs(view["matched"], False)
        self.assertEqual(view["missing_attributes"], ["need_to_know"])
        self.assertEqual(view["present_attributes"], ["clearance"])
        self.assertIs(view["enforced_here"], False)
        self.ext.record_subject_attributes(
            "subject-7", ["need_to_know"], STEWARD)
        view = self.ext.abac_decision_view(decision["id"], STEWARD)
        self.assertIs(view["matched"], True)
        self.assertEqual(view["missing_attributes"], [])

    def test_decision_changes_no_core_access_state(self):
        policy = self._policy()
        before = {
            "dataset": self.store.get_dataset(self.ds),
            "requests": self.store.list_access_requests(actor=ADMIN),
            "grants": self.store.list_grants(actor=ADMIN),
        }
        self.ext.record_subject_attributes(
            "subject-7", ["clearance", "need_to_know"], STEWARD)
        decision = self.ext.record_abac_decision(
            policy["id"], "subject-7", STEWARD)
        self.ext.abac_decision_view(decision["id"], STEWARD)
        after = {
            "dataset": self.store.get_dataset(self.ds),
            "requests": self.store.list_access_requests(actor=ADMIN),
            "grants": self.store.list_grants(actor=ADMIN),
        }
        self.assertEqual(before, after)

    def test_viewer_may_not_record_decision(self):
        policy = self._policy()
        with self.assertRaises(PermissionDenied):
            self.ext.record_abac_decision(policy["id"], "subject-7",
                                          VIEWER)
        self.assertIn("ext_abac_decision_record:denied",
                      self.audit_actions())


class TestAbacMatchNegativeControl(BatchFixture):
    """Fresh negative control: the ABAC presence-match seam.

    Traced claim: **an ABAC decision matches only when every
    attribute name the policy requires is recorded present for
    the subject** (the enforcement-plane entry's derivation; the
    personalization precedent's deterministic presence match).
    Each canonical case asserts (1) the real implementation's
    outcome, (2) the mutant seam (``return True``) would NOT
    produce it, and (3) treating the mutant's outcome as the
    expected outcome fails.
    """

    def _setup_pair(self, ext):
        policy = ext.define_abac_policy(
            "cui-access", self.ds, ["clearance", "need_to_know"],
            STEWARD)
        ext.record_subject_attributes("subject-7", ["clearance"],
                                      STEWARD)
        decision = ext.record_abac_decision(policy["id"], "subject-7",
                                            STEWARD)
        return decision

    def test_unmatched_subject_denied_by_match_canonical(self):
        decision = self._setup_pair(self.ext)
        view = self.ext.abac_decision_view(decision["id"], STEWARD)
        self.assertIs(view["matched"], False)
        mutant = MutantExtensions(self.store)
        mdecision = self._setup_pair(mutant)
        mview = mutant.abac_decision_view(mdecision["id"], STEWARD)
        self.assertIs(mview["matched"], True)
        with self.assertRaises(AssertionError):
            self.assertIs(mview["matched"], False)

    def test_fully_attributed_subject_still_matches(self):
        policy = self.ext.define_abac_policy(
            "cui-access", self.ds, ["clearance"], STEWARD)
        self.ext.record_subject_attributes(
            "subject-9", ["clearance", "extra"], STEWARD)
        decision = self.ext.record_abac_decision(
            policy["id"], "subject-9", STEWARD)
        view = self.ext.abac_decision_view(decision["id"], STEWARD)
        self.assertIs(view["matched"], True)

    def test_no_attributes_recorded_never_matches(self):
        policy = self.ext.define_abac_policy(
            "cui-access", self.ds, ["clearance"], STEWARD)
        decision = self.ext.record_abac_decision(
            policy["id"], "subject-unknown", STEWARD)
        view = self.ext.abac_decision_view(decision["id"], STEWARD)
        self.assertIs(view["matched"], False)
        self.assertEqual(view["present_attributes"], [])


class TestProductions(BatchFixture):
    """Entry: Archive, eDiscovery & FOIA production, incl.
    disposition execution (built, in the DM units' forms).

    Production records with counts as reported; disposition as
    DECISION records with eligibility derived from the core's
    retention state, plus execution reference records --
    ``executed_here`` / ``disposition_executed`` False throughout
    (PLATFORM-LAYER.md decision 4).
    """

    def test_production_record_shape_and_kinds(self):
        prod = self.ext.record_production(
            self.ds, "ediscovery", STEWARD, records_reported=850,
            checksum="sha256:abc")
        self.assertEqual(prod["id"], "prd-1")
        self.assertIs(prod["content_held"], False)
        self.assertIs(prod["executed_here"], False)
        for kind in ("archive", "foia"):
            self.ext.record_production(self.ds, kind, STEWARD)
        self.assertEqual(len(self.ext.list_productions(actor=STEWARD)), 3)
        with self.assertRaises(ValidationError):
            self.ext.record_production(self.ds, "backup", STEWARD)

    def test_viewer_may_not_record_production(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_production(self.ds, "archive", VIEWER)
        self.assertIn("ext_production_record:denied", self.audit_actions())

    def _policy(self, legal_hold=False, days=30):
        return self.store.set_retention_policy(
            self.ds, days, "archive", STEWARD, legal_hold=legal_hold)

    def test_disposition_requires_core_policy(self):
        with self.assertRaises(ValidationError):
            self.ext.record_disposition_decision(
                self.ds, "approve", STEWARD)

    def test_disposition_eligibility_derived_from_core(self):
        self._policy()
        record = self.ext.record_disposition_decision(
            self.ds, "approve", STEWARD, now=self.dataset["created_utc"])
        self.assertIs(record["eligible"], False)
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["disposition_executed"], False)
        due = self.ext.record_disposition_decision(
            self.ds, "approve", STEWARD, now="2999-01-01T00:00:00+00:00")
        self.assertIs(due["eligible"], True)
        self.assertGreater(due["age_days"], 30)

    def test_disposition_legal_hold_never_eligible(self):
        self._policy(legal_hold=True)
        record = self.ext.record_disposition_decision(
            self.ds, "approve", STEWARD, now="2999-01-01T00:00:00+00:00")
        self.assertIs(record["eligible"], False)
        self.assertIs(record["legal_hold"], True)

    def test_execution_reference_requires_approval_and_executes_nothing(self):
        self._policy()
        rejected = self.ext.record_disposition_decision(
            self.ds, "reject", STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.record_disposition_execution_reference(
                rejected["id"], STEWARD)
        approved = self.ext.record_disposition_decision(
            self.ds, "approve", STEWARD, now="2999-01-01T00:00:00+00:00")
        ref = self.ext.record_disposition_execution_reference(
            approved["id"], STEWARD, target_ref="nara-transfer-1")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["executed"], False)
        # The dataset and its policy are still present and untouched.
        self.assertEqual(self.store.get_dataset(self.ds)["id"], self.ds)
        self.assertIsNotNone(self.store.retention_policy_for(self.ds))


class TestQueryVisualization(BatchFixture):
    """Entry: Query & visualization engines (built).

    Definitions in text-free structure (no parameter can accept
    query text -- pinned by TypeError), runs as reported counts,
    visualization views derived from stored run reports.
    """

    def test_query_definition_is_text_free_structure(self):
        query = self.ext.define_query(
            "by-status", self.ds, "count_by_field", STEWARD,
            field="status")
        self.assertEqual(query["id"], "qry-1")
        self.assertIs(query["definition_only"], True)
        self.assertIs(query["executed_here"], False)
        with self.assertRaises(TypeError):
            self.ext.define_query(
                "q", self.ds, "count_records", STEWARD,
                query_text="select * from datasets")
        with self.assertRaises(TypeError):
            self.ext.define_query(
                "q", self.ds, "count_records", STEWARD,
                sql="select 1")
        with self.assertRaises(ValidationError):
            self.ext.define_query("q", self.ds, "count_by_field",
                                  STEWARD)

    def test_query_run_is_a_report_not_an_execution(self):
        query = self.ext.define_query(
            "total", self.ds, "count_records", STEWARD)
        run = self.ext.record_query_run(
            query["id"], STEWARD, records_scanned_reported=5000,
            records_matched_reported=120)
        self.assertEqual(run["id"], "qrs-1")
        self.assertIs(run["executed_here"], False)
        with self.assertRaises(TypeError):
            self.ext.record_query_run(query["id"], STEWARD,
                                      records=[{"a": 1}])

    def test_visualization_view_derived_from_run_reports(self):
        query = self.ext.define_query(
            "total", self.ds, "count_records", STEWARD)
        viz = self.ext.define_visualization(
            "totals-chart", query["id"], "bar", STEWARD)
        self.assertIs(viz["rendered_here"], False)
        view = self.ext.visualization_view(viz["id"], STEWARD)
        self.assertIsNone(view["series"])
        self.assertIs(view["rendered_here"], False)
        self.assertIs(view["executes_query"], False)
        self.ext.record_query_run(query["id"], STEWARD,
                                  records_scanned_reported=10,
                                  records_matched_reported=4)
        view = self.ext.visualization_view(viz["id"], STEWARD)
        self.assertEqual(
            view["series"],
            {"records_scanned_reported": 10,
             "records_matched_reported": 4})
        self.assertEqual(view["runs_available"], 1)


class TestModelStubs(BatchFixture):
    """Entry: AI/ML engines (reference stub).

    Six claimants in this set; the build computes nothing
    learned. Records carry ``reference_stub: True``; run outcomes
    are reported verbatim and outputs are opaque refs.
    """

    def test_model_record_is_a_labeled_declaration(self):
        model = self.ext.register_model(
            "orchestrator", STEWARD, dataset_id=self.ds,
            technique="reported_technique")
        self.assertEqual(model["id"], "mdl-1")
        self.assertIs(model["reference_stub"], True)
        self.assertIs(model["trained_here"], False)
        self.assertIs(model["inference_here"], False)
        self.assertEqual(model["method"], "recorded_declaration_only")

    def test_model_run_outcome_verbatim_output_opaque_ref(self):
        model = self.ext.register_model("m", STEWARD)
        run = self.ext.record_model_run(
            model["id"], "reported_completed", STEWARD,
            output_ref="ext-output-123")
        self.assertEqual(run["outcome"], "reported_completed")
        self.assertEqual(run["output_ref"], "ext-output-123")
        self.assertIs(run["reference_stub"], True)
        self.assertIs(run["inference_here"], False)
        self.assertEqual(
            set(run.keys()),
            {"id", "model_id", "outcome", "output_ref",
             "reference_stub", "inference_here",
             "created_by", "created_utc"})


class TestProcessingStubs(BatchFixture):
    """Entry: Document processing engines (reference stub).

    OCR / classification / deduplication as job and output
    records; no extracted text exists in any shape.
    """

    def test_processing_kinds_include_deduplication(self):
        for kind in ("ocr", "classification", "deduplication"):
            job = self.ext.register_processing_job(kind, self.ds,
                                                   STEWARD)
            self.assertIs(job["reference_stub"], True)
            self.assertIs(job["processed_here"], False)
            self.assertIs(job["outputs_held"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_processing_job("transcription", self.ds,
                                             STEWARD)

    def test_output_record_holds_ref_and_count_only(self):
        job = self.ext.register_processing_job("ocr", self.ds, STEWARD)
        out = self.ext.record_processing_output(
            job["id"], "ext-doc-9", STEWARD, records_reported=17)
        self.assertEqual(
            set(out.keys()),
            {"id", "job_id", "output_ref", "records_reported",
             "reference_stub", "content_held", "processed_here",
             "created_by", "created_utc"})
        self.assertIs(out["content_held"], False)
        with self.assertRaises(TypeError):
            self.ext.record_processing_output(
                job["id"], "ext-doc-9", STEWARD,
                extracted_text="the document says...")


class TestFileTransferStubs(BatchFixture):
    """Entry: Managed file transfer transport (reference stub)."""

    def test_transfer_record_is_transport_labeled(self):
        trf = self.ext.record_file_transfer(
            self.ds, self.src, STEWARD, record_count=25,
            checksum="sha256:def", protocol="sftp")
        self.assertEqual(trf["id"], "trf-1")
        self.assertIs(trf["reference_transport"], True)
        self.assertIs(trf["moved_here"], False)
        self.assertIs(trf["transferred_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_file_transfer(
                self.ds, self.src, STEWARD, protocol="carrier_pigeon")
        with self.assertRaises(NotFoundError):
            self.ext.record_file_transfer(self.ds, "src-999", STEWARD)


class TestSearchIndexStubs(BatchFixture):
    """Entry: Search indexing engine (reference stub).

    Definitions and reported snapshots only; the core's literal
    metadata search is pinned unchanged.
    """

    def test_index_definition_and_snapshot_labels(self):
        idx = self.ext.define_search_index("meta-index", STEWARD,
                                           dataset_id=self.ds)
        self.assertIs(idx["reference_stub"], True)
        self.assertIs(idx["index_built_here"], False)
        snap = self.ext.record_index_snapshot(idx["id"], 4200, STEWARD)
        self.assertIs(snap["reference_stub"], True)
        self.assertIs(snap["indexed_here"], False)
        self.assertIs(snap["index_built_here"], False)
        self.assertEqual(snap["documents_reported"], 4200)

    def test_core_literal_search_unchanged(self):
        before = self.store.search("claims", actor=STEWARD)
        idx = self.ext.define_search_index("meta-index", STEWARD,
                                           dataset_id=self.ds)
        self.ext.record_index_snapshot(idx["id"], 10, STEWARD)
        after = self.store.search("claims", actor=STEWARD)
        self.assertEqual(before, after)
        self.assertEqual(len(after["datasets"]), 1)


class TestTierNullAndShapeScan(BatchFixture):
    """Cross-cutting: tier null and shape discipline.

    Every extension record and derived view is scanned
    recursively: no key may name a tier, a baseline, or an
    equivalence; no value may be a float; no list may hold
    numbers (a vector value is a list of numbers -- none exists).
    """

    FORBIDDEN_KEY_PARTS = ("tier", "cmmc", "baseline", "equivalence",
                           "impact_level")

    def _everything(self):
        ext = self.ext
        coll = ext.define_vector_collection(
            "c", STEWARD, dataset_id=self.ds, dimension=8,
            metric="cosine")
        job = ext.record_embedding_job(coll["id"], STEWARD,
                                       documents_reported=3,
                                       embeddings_reported=3)
        wrh = ext.register_warehouse("w", STEWARD,
                                     scale_label="petabyte-scale",
                                     dataset_id=self.ds)
        run = ext.record_warehouse_query_run(wrh["id"], STEWARD,
                                             rows_reported=5)
        summary = ext.warehouse_summary(wrh["id"], STEWARD)
        n1 = ext.register_graph_node("n1", "application", STEWARD)
        n2 = ext.register_graph_node("n2", "database", STEWARD)
        edge = ext.record_graph_edge(n1["id"], n2["id"], "uses",
                                     STEWARD)
        node_view = ext.graph_node_view(n1["id"], STEWARD)
        policy = ext.define_abac_policy("p", self.ds, ["clearance"],
                                        STEWARD)
        attrs = ext.record_subject_attributes("s1", ["clearance"],
                                              STEWARD)
        decision = ext.record_abac_decision(policy["id"], "s1",
                                            STEWARD)
        decision_view = ext.abac_decision_view(decision["id"], STEWARD)
        prod = ext.record_production(self.ds, "foia", STEWARD,
                                     records_reported=2)
        query = ext.define_query("q", self.ds, "count_records",
                                 STEWARD)
        qrun = ext.record_query_run(query["id"], STEWARD,
                                    records_scanned_reported=9,
                                    records_matched_reported=9)
        viz = ext.define_visualization("v", query["id"], "table",
                                       STEWARD)
        viz_view = ext.visualization_view(viz["id"], STEWARD)
        model = ext.register_model("m", STEWARD, dataset_id=self.ds)
        mrun = ext.record_model_run(model["id"], "reported_ok",
                                    STEWARD, output_ref="o-1")
        pjob = ext.register_processing_job("deduplication", self.ds,
                                           STEWARD)
        pout = ext.record_processing_output(pjob["id"], "o-2",
                                            STEWARD,
                                            records_reported=1)
        trf = ext.record_file_transfer(self.ds, self.src, STEWARD,
                                       record_count=1)
        idx = ext.define_search_index("i", STEWARD, dataset_id=self.ds)
        snap = ext.record_index_snapshot(idx["id"], 1, STEWARD)
        return [coll, job, wrh, run, summary, n1, n2, edge, node_view,
                policy, attrs, decision, decision_view, prod, query,
                qrun, viz, viz_view, model, mrun, pjob, pout, trf,
                idx, snap]

    def test_no_tier_shaped_key_no_float_no_numeric_list(self):
        for record in self._everything():
            for key, value in _walk(record):
                lowered = key.lower()
                for part in self.FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(
                        part, lowered,
                        "tier-shaped key %r in %r" % (key, record))
                self.assertNotIsInstance(
                    value, float,
                    "float value at %r in %r" % (key, record))
                if isinstance(value, list):
                    for item in value:
                        self.assertNotIsInstance(
                            item, (int, float),
                            "numeric list (vector-shaped) at %r in %r"
                            % (key, record))

    def test_stub_records_carry_their_labels(self):
        records = self._everything()
        by_id = {r["id"]: r for r in records if "id" in r}
        for stub_id in ("mdl-1", "mrun-1", "prc-1", "pro-1", "idx-1",
                        "isn-1"):
            self.assertIs(by_id[stub_id]["reference_stub"], True)
        self.assertIs(by_id["trf-1"]["reference_transport"], True)

    def test_extension_surface_is_audited(self):
        self.ext.define_vector_collection("c", STEWARD)
        actions = self.audit_actions()
        self.assertIn("ext_vector_collection_define", actions)


class TestBareStoreFixture(unittest.TestCase):
    """The extension surface works over a bare core store too."""

    def test_bare_store(self):
        store = fresh_store()
        ext = DataMgmtExtensions(store)
        dataset = store.create_dataset("D", "desc", STEWARD)
        coll = ext.define_vector_collection("c", STEWARD,
                                            dataset_id=dataset["id"])
        self.assertEqual(coll["dataset_id"], dataset["id"])
        with self.assertRaises(NotFoundError):
            ext.define_vector_collection("c2", STEWARD,
                                         dataset_id="ds-999")


if __name__ == "__main__":
    unittest.main()
