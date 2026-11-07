"""Final GAPS batch tests — Singleton 53, Research L2.

Pins the extension surface in ``src/research/extensions.py`` per
GAPS.md section entry (inventory idx 521–530; see ``../BATCH.md``
for the per-entry disposition) and the founding discipline: the
commons is a registry of dataset records and counts, so every
extension shape is pinned to its exact key set, an unexpected
keyword argument raises ``TypeError`` (no parameter can accept
subject data, a dataset payload, or query text), and a recursive
scan finds no subject-data-, payload-, or score-shaped key on any
extension record, view, or summary.

The batch's fresh negative control lives here:
``TestDeliveryDerivationNegativeControl`` mutates the extension's
single delivery-state derivation seam (``_current_delivery_label``)
to read the EARLIEST recorded state instead of the latest, and
pins that the canonical expectations reject the mutant's outcome.
"""

import copy
import unittest

from research.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from research.extensions import ResearchExtensions

from research_helpers import (
    ADMIN,
    AFTER_EXPIRY,
    BEFORE_T0,
    INSIDE_WINDOW,
    MEMBER,
    ORG_REF,
    OUTSIDER,
    STAFF,
    T0,
    VIEWER,
    make_dataset,
    make_grant,
    make_store,
    make_workspace,
)

FORBIDDEN_KEY_FRAGMENTS = (
    "subject", "patient", "participant", "ssn", "email", "phone",
    "genom", "score", "rank", "payload", "content", "signature",
    "identifier",
)


def make_extensions():
    """Fresh store + canonical commons + the extension surface."""
    store, commons, _org = make_store()
    return ResearchExtensions(store), store, commons


def _scan_keys(value, path="root"):
    """Yield (path, key) for every dict key in a nested structure."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, key
            yield from _scan_keys(item, path + "." + str(key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _scan_keys(item, "%s[%d]" % (path, index))


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.commons = make_extensions()
        self.cid = self.commons["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]


class TestRuntimeConfigs(BatchFixture):
    """Idx 521 — data commons runtime engine (built)."""

    def test_record_shape_and_derived_count(self):
        config = self.ext.record_runtime_config(
            MEMBER, self.cid, "CFG-1", "standard-profile",
            ["param:region", "param:replicas"])
        self.assertEqual(config["id"], "rt-1")
        self.assertIs(config["runtime_started_here"], False)
        self.assertEqual(
            set(config.keys()),
            {"id", "commons_id", "config_ref", "profile_label",
             "parameter_refs", "runtime_started_here", "created_by",
             "created_utc"})
        view = self.ext.runtime_config_view(MEMBER, config["id"])
        self.assertEqual(view["parameter_count"], 2)
        self.assertIs(view["derived"], True)
        stored = self.ext.get_runtime_config(MEMBER, config["id"])
        self.assertNotIn("parameter_count", stored)

    def test_duplicate_ref_and_bad_refs_rejected(self):
        self.ext.record_runtime_config(
            MEMBER, self.cid, "CFG-1", "p", ["param:a"])
        with self.assertRaises(ValidationError):
            self.ext.record_runtime_config(
                MEMBER, self.cid, "CFG-1", "p", ["param:b"])
        with self.assertRaises(ValidationError):
            self.ext.record_runtime_config(
                MEMBER, self.cid, "CFG-2", "p", [])
        with self.assertRaises(ValidationError):
            self.ext.record_runtime_config(
                MEMBER, self.cid, "CFG-2", "p", ["param:a", "param:a"])
        config = self.ext.record_runtime_config(
            MEMBER, self.cid, "CFG-2", "p", ["param:b"])
        self.assertEqual(config["id"], "rt-2")

    def test_outsider_and_viewer_boundaries(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_runtime_config(
                OUTSIDER, self.cid, "CFG-9", "p", ["param:a"])
        with self.assertRaises(PermissionDenied):
            self.ext.record_runtime_config(
                VIEWER, self.cid, "CFG-9", "p", ["param:a"])
        self.assertIn("ext_runtime_config_record:denied",
                      self.audit_actions())


class TestIngestion(BatchFixture):
    """Idx 522 — data ingestion / ETL engine (built)."""

    def _pipeline(self):
        dataset = make_dataset(self.store, self.commons)
        pipeline = self.ext.define_pipeline(
            MEMBER, self.cid, dataset["id"], "PIPE-1", "SRC-ARCHIVE",
            ["step:extract", "step:load"])
        return dataset, pipeline

    def test_definition_shape(self):
        dataset, pipeline = self._pipeline()
        self.assertEqual(pipeline["id"], "pl-1")
        self.assertIs(pipeline["data_held_here"], False)
        self.assertEqual(
            set(pipeline.keys()),
            {"id", "commons_id", "dataset_id", "pipeline_ref",
             "source_ref", "transform_step_refs", "data_held_here",
             "created_by", "created_utc"})

    def test_run_records_reported_counts_and_moves_nothing(self):
        dataset, pipeline = self._pipeline()
        before = copy.deepcopy(self.store._datasets[dataset["id"]])
        run = self.ext.record_pipeline_run(
            MEMBER, pipeline["id"], "reported_completed", 1200,
            "etl engine nightly report")
        self.assertEqual(run["id"], "run-1")
        self.assertEqual(run["records_reported"], 1200)
        self.assertIs(run["ingested_here"], False)
        self.assertIs(run["data_held_here"], False)
        self.assertEqual(
            set(run.keys()),
            {"id", "commons_id", "pipeline_id", "state_label",
             "records_reported", "source_label", "data_held_here",
             "ingested_here", "created_by", "created_utc"})
        after = self.store._datasets[dataset["id"]]
        self.assertEqual(before, after)

    def test_run_validation_and_summary(self):
        _dataset, pipeline = self._pipeline()
        with self.assertRaises(ValidationError):
            self.ext.record_pipeline_run(
                MEMBER, pipeline["id"], "completed", 5, "report")
        with self.assertRaises(ValidationError):
            self.ext.record_pipeline_run(
                MEMBER, pipeline["id"], "reported_completed", -1, "r")
        with self.assertRaises(ValidationError):
            self.ext.record_pipeline_run(
                MEMBER, pipeline["id"], "reported_completed", 1.5, "r")
        run = self.ext.record_pipeline_run(
            MEMBER, pipeline["id"], "reported_partial", 40, "report")
        self.assertEqual(run["id"], "run-1")
        self.ext.record_pipeline_run(
            MEMBER, pipeline["id"], "reported_completed", 60, "report")
        summary = self.ext.ingestion_summary(MEMBER, self.cid)
        self.assertEqual(summary["pipelines"], 1)
        self.assertEqual(summary["runs"], 2)
        self.assertEqual(summary["runs_by_state"],
                         {"reported_partial": 1, "reported_completed": 1})
        self.assertEqual(summary["records_reported_total"], 100)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertIs(summary["ingested_here"], False)

    def test_dataset_must_be_in_commons(self):
        other = self.store.create_commons(
            STAFF, "other-commons", "Other", "commons", "SPONSOR-2")
        foreign = make_dataset(self.store, other, actor=STAFF)
        # ADMIN reaches both commons, so the mismatch itself is
        # what is rejected (a non-member is denied even earlier,
        # at the core store's membership boundary).
        with self.assertRaises(ValidationError):
            self.ext.define_pipeline(
                ADMIN, self.cid, foreign["id"], "PIPE-X", "SRC", ["s:1"])


class TestHarmonization(BatchFixture):
    """Idx 523 — data harmonization engine (built)."""

    def _mapping(self):
        return self.ext.define_mapping(
            MEMBER, self.cid, "MAP-1", ["src:age_years", "src:sex_code"],
            ["cdm:age", "cdm:sex"])

    def test_definition_shape_and_derived_counts(self):
        mapping = self._mapping()
        self.assertEqual(mapping["id"], "map-1")
        self.assertIs(mapping["harmonized_here"], False)
        self.assertEqual(
            set(mapping.keys()),
            {"id", "commons_id", "mapping_ref", "source_field_refs",
             "target_field_refs", "harmonized_here", "created_by",
             "created_utc"})
        view = self.ext.mapping_view(MEMBER, mapping["id"])
        self.assertEqual(view["source_field_count"], 2)
        self.assertEqual(view["target_field_count"], 2)
        self.assertNotIn("source_field_count",
                         self.ext.get_mapping(MEMBER, mapping["id"]))

    def test_outcomes_verbatim_and_summary(self):
        mapping = self._mapping()
        outcome = self.ext.record_conformance_outcome(
            MEMBER, mapping["id"], "reported_partial", 7,
            "harmonization service report")
        self.assertEqual(outcome["id"], "cfm-1")
        self.assertIs(outcome["harmonized_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_conformance_outcome(
                MEMBER, mapping["id"], "conformant", 1, "report")
        self.ext.record_conformance_outcome(
            MEMBER, mapping["id"], "reported_conformant", 12, "report")
        summary = self.ext.harmonization_summary(MEMBER, self.cid)
        self.assertEqual(summary["mappings"], 1)
        self.assertEqual(summary["outcomes_by_label"],
                         {"reported_partial": 1, "reported_conformant": 1})
        self.assertEqual(summary["fields_reported_total"], 19)
        self.assertIs(summary["harmonized_here"], False)


class TestIndexReferences(BatchFixture):
    """Idx 524 — indexing & metadata catalog engines (reference)."""

    def test_reference_labels(self):
        record = self.ext.record_index_reference(
            MEMBER, self.cid, "IDX-1", "dataset metadata catalog")
        self.assertEqual(record["id"], "idx-1")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["index_built_here"], False)
        self.assertEqual(
            set(record.keys()),
            {"id", "commons_id", "index_ref", "scope_label",
             "reference_stub", "state", "index_built_here",
             "created_by", "created_utc"})

    def test_core_search_unchanged_by_reference(self):
        make_dataset(self.store, self.commons)
        before = self.store.search(MEMBER, "trial")
        self.ext.record_index_reference(
            MEMBER, self.cid, "IDX-1", "dataset metadata catalog")
        after = self.store.search(MEMBER, "trial")
        self.assertEqual(before, after)
        self.assertEqual(len(after["datasets"]), 1)


class TestQueries(BatchFixture):
    """Idx 525 — query & analysis workspace engines (built)."""

    def _query(self):
        workspace = make_workspace(self.store, self.commons)
        query = self.ext.define_query(
            MEMBER, self.cid, workspace["id"], "QRY-1",
            ["field:dataset_name", "field:access_tier"], ["op:filter"])
        return workspace, query

    def test_definition_shape_and_derived_counts(self):
        _workspace, query = self._query()
        self.assertEqual(query["id"], "qry-1")
        self.assertIs(query["executed_here"], False)
        self.assertEqual(
            set(query.keys()),
            {"id", "commons_id", "workspace_id", "query_ref",
             "field_refs", "operator_names", "executed_here",
             "created_by", "created_utc"})
        view = self.ext.query_view(MEMBER, query["id"])
        self.assertEqual(view["field_ref_count"], 2)
        self.assertEqual(view["operator_count"], 1)

    def test_no_query_text_parameter_exists(self):
        workspace = make_workspace(self.store, self.commons)
        with self.assertRaises(TypeError):
            self.ext.define_query(
                MEMBER, self.cid, workspace["id"], "QRY-2",
                ["field:x"], ["op:filter"], query_text="select *")

    def test_result_counts_stored_as_reported(self):
        _workspace, query = self._query()
        result = self.ext.record_query_result(
            MEMBER, query["id"], 42, "analysis workspace report")
        self.assertEqual(result["id"], "qrs-1")
        self.assertEqual(result["result_count_reported"], 42)
        self.assertIs(result["executed_here"], False)
        self.assertIs(result["computed_here"], False)
        results = self.ext.list_query_results(MEMBER, query["id"])
        self.assertEqual(len(results), 1)


class TestCohorts(BatchFixture):
    """Idx 526 — cohort builder / cohort discovery engine (built)."""

    def _cohort(self):
        dataset = make_dataset(self.store, self.commons)
        cohort = self.ext.define_cohort(
            MEMBER, self.cid, dataset["id"], "COH-1",
            ["crit:age_band", "crit:enrollment_window"])
        return dataset, cohort

    def test_definition_shape_has_no_subject_field(self):
        _dataset, cohort = self._cohort()
        self.assertEqual(cohort["id"], "coh-1")
        self.assertIs(cohort["members_computed_here"], False)
        self.assertEqual(
            set(cohort.keys()),
            {"id", "commons_id", "dataset_id", "cohort_ref",
             "criteria_refs", "members_computed_here", "created_by",
             "created_utc"})
        view = self.ext.cohort_view(MEMBER, cohort["id"])
        self.assertEqual(view["criteria_count"], 2)

    def test_no_subject_refs_parameter_exists(self):
        dataset = make_dataset(self.store, self.commons)
        with self.assertRaises(TypeError):
            self.ext.define_cohort(
                MEMBER, self.cid, dataset["id"], "COH-2",
                ["crit:x"], subject_refs=["person-1"])

    def test_membership_counts_stored_as_reported(self):
        _dataset, cohort = self._cohort()
        record = self.ext.record_cohort_membership(
            MEMBER, cohort["id"], 350, "cohort service report")
        self.assertEqual(record["id"], "cmr-1")
        self.assertEqual(record["members_reported"], 350)
        self.assertIs(record["members_computed_here"], False)
        self.ext.record_cohort_membership(
            MEMBER, cohort["id"], 25, "cohort service report")
        summary = self.ext.cohort_summary(MEMBER, self.cid)
        self.assertEqual(summary["cohorts"], 1)
        self.assertEqual(summary["membership_reports"], 2)
        self.assertEqual(summary["members_reported_total"], 375)
        self.assertIs(summary["members_computed_here"], False)


class TestFederation(BatchFixture):
    """Idx 527 — cross-commons federation / data mesh (built)."""

    def _peer(self):
        return self.ext.record_peer_commons(
            MEMBER, self.cid, "PEER-EAST", "East regional commons")

    def test_peer_shape(self):
        peer = self._peer()
        self.assertEqual(peer["id"], "per-1")
        self.assertIs(peer["connected_here"], False)
        self.assertEqual(
            set(peer.keys()),
            {"id", "commons_id", "peer_ref", "peer_label",
             "connected_here", "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            self.ext.record_peer_commons(
                MEMBER, self.cid, "PEER-EAST", "duplicate")

    def test_exchange_request_and_outcome(self):
        peer = self._peer()
        dataset = make_dataset(self.store, self.commons)
        request = self.ext.record_exchange_request(
            MEMBER, peer["id"], dataset["id"], "Federated summary exchange")
        self.assertEqual(request["id"], "exr-1")
        self.assertIs(request["connected_here"], False)
        self.assertIs(request["reference_transport"], True)
        outcome = self.ext.record_exchange_outcome(
            MEMBER, request["id"], "reported_completed", "peer receipt")
        self.assertEqual(outcome["id"], "exo-1")
        self.assertIs(outcome["data_moved_here"], False)
        self.assertIs(outcome["reference_transport"], True)
        with self.assertRaises(ValidationError):
            self.ext.record_exchange_outcome(
                MEMBER, request["id"], "completed", "peer receipt")
        summary = self.ext.federation_summary(MEMBER, self.cid)
        self.assertEqual(summary["peers"], 1)
        self.assertEqual(summary["exchange_requests"], 1)
        self.assertEqual(summary["outcomes_by_label"],
                         {"reported_completed": 1})
        self.assertIs(summary["connected_here"], False)


class TestDeliveries(BatchFixture):
    """Idx 528 — data delivery / transfer engine (built)."""

    def _delivery(self):
        dataset = make_dataset(self.store, self.commons)
        delivery = self.ext.record_delivery(
            MEMBER, self.cid, dataset["id"], ORG_REF)
        return dataset, delivery

    def test_record_shape_has_no_state_key(self):
        _dataset, delivery = self._delivery()
        self.assertEqual(delivery["id"], "dlv-1")
        self.assertIsNone(delivery["grant_id"])
        self.assertIs(delivery["data_moved_here"], False)
        self.assertEqual(
            set(delivery.keys()),
            {"id", "commons_id", "dataset_id", "grant_id",
             "recipient_ref", "data_moved_here", "created_by",
             "created_utc"})
        view = self.ext.delivery_view(MEMBER, delivery["id"])
        self.assertIsNone(view["current_state"])
        self.assertEqual(view["state_record_count"], 0)

    def test_current_state_derived_from_latest(self):
        _dataset, delivery = self._delivery()
        self.ext.record_delivery_state(
            MEMBER, delivery["id"], "reported_prepared")
        state = self.ext.record_delivery_state(
            MEMBER, delivery["id"], "reported_received")
        self.assertEqual(state["id"], "dls-2")
        self.assertEqual(
            set(state.keys()),
            {"id", "commons_id", "delivery_id", "state_label",
             "data_moved_here", "created_by", "created_utc"})
        view = self.ext.delivery_view(MEMBER, delivery["id"])
        self.assertEqual(view["current_state"], "reported_received")
        self.assertEqual(view["state_record_count"], 2)
        stored = self.ext.get_delivery(MEMBER, delivery["id"])
        self.assertNotIn("current_state", stored)
        with self.assertRaises(ValidationError):
            self.ext.record_delivery_state(
                MEMBER, delivery["id"], "received")

    def test_grant_binding_validated(self):
        dataset = make_dataset(self.store, self.commons)
        other_dataset = make_dataset(
            self.store, self.commons, name="other-dataset")
        grant = make_grant(self.store, self.commons, dataset=dataset)
        delivery = self.ext.record_delivery(
            MEMBER, self.cid, dataset["id"], ORG_REF,
            grant_id=grant["id"])
        self.assertEqual(delivery["grant_id"], grant["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_delivery(
                MEMBER, self.cid, other_dataset["id"], ORG_REF,
                grant_id=grant["id"])

    def test_grant_minting_changes_no_delivery(self):
        dataset, delivery = self._delivery()
        self.ext.record_delivery_state(
            MEMBER, delivery["id"], "reported_prepared")
        before_record = self.ext.get_delivery(MEMBER, delivery["id"])
        before_states = self.ext.list_delivery_states(MEMBER, delivery["id"])
        before_view = self.ext.delivery_view(MEMBER, delivery["id"])
        grant = make_grant(self.store, self.commons, dataset=dataset)
        self.assertEqual(grant["dataset_id"], dataset["id"])
        self.assertEqual(self.ext.get_delivery(MEMBER, delivery["id"]),
                         before_record)
        self.assertEqual(
            self.ext.list_delivery_states(MEMBER, delivery["id"]),
            before_states)
        self.assertEqual(self.ext.delivery_view(MEMBER, delivery["id"]),
                         before_view)


class TestEnforcement(BatchFixture):
    """Idx 529 — access enforcement on data delivery (built)."""

    def _delivery_with_grant(self):
        dataset = make_dataset(self.store, self.commons)
        grant = make_grant(self.store, self.commons, dataset=dataset,
                           starts_at=T0)
        delivery = self.ext.record_delivery(
            MEMBER, self.cid, dataset["id"], ORG_REF,
            grant_id=grant["id"])
        return dataset, grant, delivery

    def test_decision_record_confers_nothing(self):
        _dataset, _grant, delivery = self._delivery_with_grant()
        decision = self.ext.record_enforcement_decision(
            MEMBER, delivery["id"], "reported_permitted",
            "delivery gateway log")
        self.assertEqual(decision["id"], "enf-1")
        self.assertIs(decision["conferred_here"], False)
        self.assertIs(decision["enforced_here"], False)
        self.assertEqual(
            set(decision.keys()),
            {"id", "commons_id", "delivery_id", "grant_id",
             "decision_label", "source_label", "conferred_here",
             "enforced_here", "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            self.ext.record_enforcement_decision(
                MEMBER, delivery["id"], "permitted", "gateway log")

    def test_access_view_derives_core_grant_status(self):
        _dataset, _grant, delivery = self._delivery_with_grant()
        early = self.ext.delivery_access_view(
            MEMBER, delivery["id"], now=BEFORE_T0)
        self.assertEqual(early["grant_status"], "scheduled")
        inside = self.ext.delivery_access_view(
            MEMBER, delivery["id"], now=INSIDE_WINDOW)
        self.assertEqual(inside["grant_status"], "active")
        late = self.ext.delivery_access_view(
            MEMBER, delivery["id"], now=AFTER_EXPIRY)
        self.assertEqual(late["grant_status"], "expired")
        self.assertEqual(inside["method"], "core_grant_status_derivation")
        self.assertIs(inside["conferred_here"], False)
        self.assertIs(inside["data_moved_here"], False)

    def test_access_view_without_grant(self):
        dataset = make_dataset(self.store, self.commons)
        delivery = self.ext.record_delivery(
            MEMBER, self.cid, dataset["id"], ORG_REF)
        view = self.ext.delivery_access_view(MEMBER, delivery["id"])
        self.assertIsNone(view["grant_id"])
        self.assertIsNone(view["grant_status"])

    def test_decision_changes_no_grant_and_no_delivery_state(self):
        _dataset, grant, delivery = self._delivery_with_grant()
        self.ext.record_delivery_state(
            MEMBER, delivery["id"], "reported_prepared")
        grant_before = copy.deepcopy(self.store._grants[grant["id"]])
        view_before = self.ext.delivery_view(MEMBER, delivery["id"])
        self.ext.record_enforcement_decision(
            MEMBER, delivery["id"], "reported_refused",
            "delivery gateway log")
        self.assertEqual(self.store._grants[grant["id"]], grant_before)
        self.assertEqual(self.ext.delivery_view(MEMBER, delivery["id"]),
                         view_before)
        summary = self.ext.enforcement_summary(MEMBER, self.cid)
        self.assertEqual(summary["decisions_by_label"],
                         {"reported_refused": 1})
        self.assertIs(summary["conferred_here"], False)


class TestIdentityReferences(BatchFixture):
    """Idx 530 — identity provider / identity management (reference)."""

    def test_reference_labels(self):
        record = self.ext.record_identity_reference(
            MEMBER, self.cid, "IDP-ORG", "Organization identity provider")
        self.assertEqual(record["id"], "idr-1")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["identity_provider"], False)
        self.assertEqual(
            set(record.keys()),
            {"id", "commons_id", "provider_ref", "provider_label",
             "reference_stub", "state", "identity_provider",
             "created_by", "created_utc"})


class TestEngineSummaryAndScan(BatchFixture):
    """Cross-entry: deterministic summary + no-subject-data scan."""

    def _one_of_each(self):
        dataset = make_dataset(self.store, self.commons)
        workspace = make_workspace(self.store, self.commons)
        self.ext.record_runtime_config(
            MEMBER, self.cid, "CFG-1", "p", ["param:a"])
        pipeline = self.ext.define_pipeline(
            MEMBER, self.cid, dataset["id"], "PIPE-1", "SRC", ["s:1"])
        run = self.ext.record_pipeline_run(
            MEMBER, pipeline["id"], "reported_completed", 3, "report")
        mapping = self.ext.define_mapping(
            MEMBER, self.cid, "MAP-1", ["src:a"], ["cdm:a"])
        outcome = self.ext.record_conformance_outcome(
            MEMBER, mapping["id"], "reported_conformant", 2, "report")
        index_ref = self.ext.record_index_reference(
            MEMBER, self.cid, "IDX-1", "catalog")
        query = self.ext.define_query(
            MEMBER, self.cid, workspace["id"], "QRY-1", ["f:a"], ["op:eq"])
        result = self.ext.record_query_result(
            MEMBER, query["id"], 5, "report")
        cohort = self.ext.define_cohort(
            MEMBER, self.cid, dataset["id"], "COH-1", ["crit:a"])
        membership = self.ext.record_cohort_membership(
            MEMBER, cohort["id"], 9, "report")
        peer = self.ext.record_peer_commons(
            MEMBER, self.cid, "PEER-1", "peer")
        request = self.ext.record_exchange_request(
            MEMBER, peer["id"], dataset["id"], "exchange")
        exchange_outcome = self.ext.record_exchange_outcome(
            MEMBER, request["id"], "reported_pending", "receipt")
        delivery = self.ext.record_delivery(
            MEMBER, self.cid, dataset["id"], ORG_REF)
        state = self.ext.record_delivery_state(
            MEMBER, delivery["id"], "reported_prepared")
        decision = self.ext.record_enforcement_decision(
            MEMBER, delivery["id"], "reported_permitted", "gateway log")
        identity_ref = self.ext.record_identity_reference(
            MEMBER, self.cid, "IDP-1", "provider")
        views = [
            self.ext.runtime_config_view(MEMBER, "rt-1"),
            self.ext.mapping_view(MEMBER, mapping["id"]),
            self.ext.query_view(MEMBER, query["id"]),
            self.ext.cohort_view(MEMBER, cohort["id"]),
            self.ext.delivery_view(MEMBER, delivery["id"]),
            self.ext.delivery_access_view(MEMBER, delivery["id"]),
            self.ext.ingestion_summary(MEMBER, self.cid),
            self.ext.harmonization_summary(MEMBER, self.cid),
            self.ext.cohort_summary(MEMBER, self.cid),
            self.ext.federation_summary(MEMBER, self.cid),
            self.ext.enforcement_summary(MEMBER, self.cid),
            self.ext.engine_summary(MEMBER, self.cid),
        ]
        records = [pipeline, run, mapping, outcome, index_ref, query,
                   result, cohort, membership, peer, request,
                   exchange_outcome, delivery, state, decision,
                   identity_ref]
        return records, views

    def test_engine_summary_counts(self):
        self._one_of_each()
        summary = self.ext.engine_summary(MEMBER, self.cid)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["total_records"], 17)
        self.assertEqual(summary["deliveries"], 1)
        self.assertEqual(summary["identity_references"], 1)

    def test_no_subject_data_key_anywhere(self):
        records, views = self._one_of_each()
        for structure in records + views:
            for path, key in _scan_keys(structure):
                for fragment in FORBIDDEN_KEY_FRAGMENTS:
                    self.assertNotIn(
                        fragment, key.lower(),
                        "forbidden key fragment %r in key %r at %s"
                        % (fragment, key, path))

    def test_missing_records_raise_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.get_delivery(MEMBER, "dlv-99")
        with self.assertRaises(NotFoundError):
            self.ext.get_query(ADMIN, "qry-99")


class MutantExtensions(ResearchExtensions):
    """Reads the EARLIEST recorded delivery state as current."""

    @staticmethod
    def _current_delivery_label(states):
        if not states:
            return None
        return states[0]["state_label"]


class TestDeliveryDerivationNegativeControl(BatchFixture):
    """Fresh negative control: delivery current-state derivation.

    Traced claim (data delivery family): a delivery's current
    state is its LATEST recorded state label, derived at read and
    never stored. Three legs: the canonical expectation holds on
    the real implementation, the mutant (earliest label) would
    NOT produce it, and treating the mutant's outcome as the
    expectation fails.
    """

    def _delivery_with_states(self, ext):
        dataset = make_dataset(self.store, self.commons)
        delivery = ext.record_delivery(
            MEMBER, self.cid, dataset["id"], ORG_REF)
        ext.record_delivery_state(
            MEMBER, delivery["id"], "reported_prepared")
        ext.record_delivery_state(
            MEMBER, delivery["id"], "reported_dispatched")
        ext.record_delivery_state(
            MEMBER, delivery["id"], "reported_received")
        return delivery

    def test_canonical_reads_latest_state(self):
        delivery = self._delivery_with_states(self.ext)
        view = self.ext.delivery_view(MEMBER, delivery["id"])
        self.assertEqual(view["current_state"], "reported_received")
        self.assertEqual(view["state_record_count"], 3)

    def test_mutant_reads_earliest_state(self):
        mutant = MutantExtensions(self.store)
        delivery = self._delivery_with_states(mutant)
        view = mutant.delivery_view(MEMBER, delivery["id"])
        self.assertEqual(view["current_state"], "reported_prepared")

    def test_mutant_outcome_as_expectation_fails(self):
        mutant = MutantExtensions(self.store)
        delivery = self._delivery_with_states(mutant)
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant.delivery_view(MEMBER, delivery["id"])["current_state"],
                "reported_received")


if __name__ == "__main__":
    unittest.main()
