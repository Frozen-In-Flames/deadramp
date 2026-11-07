"""Final GAPS batch tests — Research L2 remainder additions.

Pins the addition surface in ``src/research/addition.py`` per
GAPS.md section "Remainder Addition — Research L2 (+5 forks)"
(inventory idx 580–588; see ``../BATCH-ADDITION.md`` for the
per-entry disposition) and the founding discipline: the commons
is a registry of dataset records and counts, so every addition
shape is pinned to its exact key set, an unexpected keyword
argument raises ``TypeError`` (no parameter can accept subject
data, a diagnosis, an analysis result text, a survey response
payload, or a signature value), and a recursive scan finds no
subject-data-, payload-, diagnosis-, or score-shaped key on any
addition record, view, or summary.

The addition's fresh negative control lives here:
``TestAgreementDerivationNegativeControl`` mutates the addition's
single agreement-state derivation seam
(``_current_agreement_label``) to read the EARLIEST recorded
state instead of the latest, and pins that the canonical
expectations reject the mutant's outcome.
"""

import copy
import unittest

from research.addition import ResearchAdditions
from research.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

from research_helpers import (
    MEMBER,
    OUTSIDER,
    VIEWER,
    make_commons,
    make_dataset,
    make_store,
    make_workspace,
)

ORG_HOLDER = "ORG-100"

FORBIDDEN_KEY_FRAGMENTS = (
    "subject", "patient", "participant", "ssn", "email", "phone",
    "genom", "score", "rank", "payload", "content", "signature",
    "identifier", "diagnosis", "respondent",
)


def make_additions():
    """Fresh store + canonical commons + the addition surface."""
    store, commons, _org = make_store()
    return ResearchAdditions(store), store, commons


def _scan_keys(value, path="root"):
    """Yield (path, key) for every dict key in a nested structure."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, key
            yield from _scan_keys(item, path + "." + str(key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _scan_keys(item, "%s[%d]" % (path, index))


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.add, self.store, self.commons = make_additions()
        self.cid = self.commons["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]

    def _pipeline(self):
        dataset = make_dataset(self.store, self.commons)
        workspace = make_workspace(self.store, self.commons)
        pipeline = self.add.define_analysis_pipeline(
            MEMBER, self.cid, dataset["id"], "PIPE-RNASEQ", "rna-seq",
            ["step:align", "step:quantify"], workspace_id=workspace["id"])
        return dataset, workspace, pipeline


class TestBioinformaticsPipelines(AdditionFixture):
    """Idx 581 — bioinformatics analysis pipeline engines (built)."""

    def test_definition_shape_and_derived_step_count(self):
        _dataset, _workspace, pipeline = self._pipeline()
        self.assertEqual(pipeline["id"], "bpd-1")
        self.assertIs(pipeline["executed_here"], False)
        self.assertIs(pipeline["data_held_here"], False)
        self.assertEqual(
            set(pipeline.keys()),
            {"id", "commons_id", "dataset_id", "workspace_id",
             "pipeline_ref", "engine_label", "step_refs",
             "executed_here", "data_held_here", "created_by",
             "created_utc"})
        view = self.add.pipeline_view(MEMBER, pipeline["id"])
        self.assertEqual(view["step_count"], 2)
        self.assertIs(view["derived"], True)
        stored = self.add.get_analysis_pipeline(MEMBER, pipeline["id"])
        self.assertNotIn("step_count", stored)

    def test_definition_rejects_foreign_dataset_and_duplicates(self):
        dataset, _workspace, _pipeline = self._pipeline()
        with self.assertRaises(ValidationError):
            self.add.define_analysis_pipeline(
                MEMBER, self.cid, dataset["id"], "PIPE-RNASEQ",
                "atac-seq", ["step:peak-call"])
        other_commons = make_commons(self.store, name="other-commons")
        foreign = make_dataset(self.store, other_commons)
        with self.assertRaises(ValidationError):
            self.add.define_analysis_pipeline(
                MEMBER, self.cid, foreign["id"], "PIPE-X", "chip-seq",
                ["step:align"])
        # The failed definitions consumed no id.
        second = self.add.define_analysis_pipeline(
            MEMBER, self.cid, dataset["id"], "PIPE-ATAC", "atac-seq",
            ["step:peak-call"])
        self.assertEqual(second["id"], "bpd-2")

    def test_run_request_and_verbatim_outcome(self):
        _dataset, _workspace, pipeline = self._pipeline()
        request = self.add.request_pipeline_run(
            MEMBER, pipeline["id"], "RUN-REQ-1", "Nightly cohort refresh")
        self.assertEqual(request["id"], "bpr-1")
        self.assertIs(request["executed_here"], False)
        self.assertEqual(
            set(request.keys()),
            {"id", "commons_id", "pipeline_id", "request_ref", "purpose",
             "executed_here", "created_by", "created_utc"})
        outcome = self.add.record_pipeline_run_outcome(
            MEMBER, request["id"], "reported_completed", 4800,
            "pipeline engine run report")
        self.assertEqual(outcome["id"], "bpo-1")
        self.assertEqual(outcome["records_reported"], 4800)
        self.assertIs(outcome["executed_here"], False)
        with self.assertRaises(ValidationError):
            self.add.record_pipeline_run_outcome(
                MEMBER, request["id"], "completed", 10, "bad label")
        with self.assertRaises(ValidationError):
            self.add.record_pipeline_run_outcome(
                MEMBER, request["id"], "reported_failed", -1, "bad count")
        # The rejected outcomes consumed no id.
        second = self.add.record_pipeline_run_outcome(
            MEMBER, request["id"], "reported_partial", 12,
            "pipeline engine run report")
        self.assertEqual(second["id"], "bpo-2")

    def test_outcome_leaves_core_dataset_byte_identical(self):
        dataset, _workspace, pipeline = self._pipeline()
        before = copy.deepcopy(self.store._datasets[dataset["id"]])
        request = self.add.request_pipeline_run(
            MEMBER, pipeline["id"], "RUN-REQ-1", "Refresh")
        self.add.record_pipeline_run_outcome(
            MEMBER, request["id"], "reported_completed", 10, "report")
        self.assertEqual(self.store._datasets[dataset["id"]], before)

    def test_pipeline_summary_counts(self):
        _dataset, _workspace, pipeline = self._pipeline()
        request = self.add.request_pipeline_run(
            MEMBER, pipeline["id"], "RUN-REQ-1", "Refresh")
        self.add.record_pipeline_run_outcome(
            MEMBER, request["id"], "reported_completed", 100, "report")
        self.add.record_pipeline_run_outcome(
            MEMBER, request["id"], "reported_failed", 0, "report")
        summary = self.add.pipeline_summary(MEMBER, self.cid)
        self.assertEqual(summary["pipelines"], 1)
        self.assertEqual(summary["run_requests"], 1)
        self.assertEqual(summary["run_outcomes"], 2)
        self.assertEqual(summary["outcomes_by_label"],
                         {"reported_completed": 1, "reported_failed": 1})
        self.assertEqual(summary["records_reported_total"], 100)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertIs(summary["executed_here"], False)


class TestElasticAllocations(AdditionFixture):
    """Idx 584 — elastic storage & compute allocation engine (built)."""

    def _request(self):
        return self.add.request_allocation(
            MEMBER, self.cid, "ALLOC-1", "compute-units", 250,
            "Variant calling burst")

    def test_request_shape(self):
        request = self._request()
        self.assertEqual(request["id"], "alr-1")
        self.assertIs(request["allocated_here"], False)
        self.assertEqual(
            set(request.keys()),
            {"id", "commons_id", "workspace_id", "allocation_ref",
             "resource_label", "units_requested", "purpose",
             "allocated_here", "created_by", "created_utc"})

    def test_amount_validation_rejects_zero_float_bool_negative(self):
        for bad in (0, -5, 2.5, True, "250"):
            with self.assertRaises(ValidationError):
                self.add.request_allocation(
                    MEMBER, self.cid, "ALLOC-BAD", "storage-units", bad,
                    "purpose")
        request = self._request()
        self.assertEqual(request["id"], "alr-1")

    def test_outcomes_and_summary_totals_are_recorded_sums(self):
        request = self._request()
        outcome = self.add.record_allocation_outcome(
            MEMBER, request["id"], "reported_partial", 200,
            "allocation service report")
        self.assertEqual(outcome["id"], "alo-1")
        self.assertIs(outcome["allocated_here"], False)
        self.assertEqual(
            set(outcome.keys()),
            {"id", "commons_id", "allocation_request_id", "outcome_label",
             "units_reported", "source_label", "allocated_here",
             "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            self.add.record_allocation_outcome(
                MEMBER, request["id"], "granted", 200, "bad label")
        summary = self.add.allocation_summary(MEMBER, self.cid)
        self.assertEqual(summary["requests"], 1)
        self.assertEqual(summary["outcomes"], 1)
        self.assertEqual(summary["units_requested_total"], 250)
        self.assertEqual(summary["units_reported_total"], 200)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertIs(summary["allocated_here"], False)


class TestAiAnalytics(AdditionFixture):
    """Idx 586 — AI analytics engine over LLMs (built)."""

    def _request(self):
        dataset = make_dataset(self.store, self.commons)
        return dataset, self.add.request_analysis(
            MEMBER, self.cid, "AN-1", "classify-verbatims", "INPUT-REF-1",
            dataset_id=dataset["id"])

    def test_request_shape(self):
        _dataset, request = self._request()
        self.assertEqual(request["id"], "anr-1")
        self.assertIs(request["inference_here"], False)
        self.assertEqual(
            set(request.keys()),
            {"id", "commons_id", "dataset_id", "request_ref", "task_label",
             "input_ref", "inference_here", "created_by", "created_utc"})

    def test_result_is_opaque_ref_only_no_text_field(self):
        _dataset, request = self._request()
        result = self.add.record_analysis_result(
            MEMBER, request["id"], "RESULT-REF-1", "analytics engine report")
        self.assertEqual(result["id"], "anx-1")
        self.assertIs(result["inference_here"], False)
        self.assertEqual(
            set(result.keys()),
            {"id", "commons_id", "analysis_request_id", "result_ref",
             "source_label", "inference_here", "created_by", "created_utc"})
        with self.assertRaises(TypeError):
            self.add.record_analysis_result(
                MEMBER, request["id"], "RESULT-REF-2", "report",
                result_text="the classified verbatims")

    def test_result_leaves_core_dataset_byte_identical(self):
        dataset, request = self._request()
        before = copy.deepcopy(self.store._datasets[dataset["id"]])
        self.add.record_analysis_result(
            MEMBER, request["id"], "RESULT-REF-1", "report")
        self.assertEqual(self.store._datasets[dataset["id"]], before)
        summary = self.add.analysis_summary(MEMBER, self.cid)
        self.assertEqual(summary["requests"], 1)
        self.assertEqual(summary["results"], 1)
        self.assertIs(summary["inference_here"], False)


class TestTechTransfer(AdditionFixture):
    """Idx 587 — technology transfer & IP management suite (built)."""

    def _disclosure(self):
        return self.add.record_disclosure(
            MEMBER, self.cid, "DISC-1", "Sample multiplexing method",
            ORG_HOLDER)

    def _agreement(self):
        disclosure = self._disclosure()
        return disclosure, self.add.record_agreement(
            MEMBER, self.cid, "AGR-1", "COUNTERPARTY-REF-1",
            "terms:master-license-v3", disclosure_id=disclosure["id"])

    def test_disclosure_and_agreement_shapes(self):
        disclosure, agreement = self._agreement()
        self.assertEqual(disclosure["id"], "dsc-1")
        self.assertIs(disclosure["executed_here"], False)
        self.assertEqual(
            set(disclosure.keys()),
            {"id", "commons_id", "disclosure_ref", "title_label",
             "holder_ref", "executed_here", "created_by", "created_utc"})
        self.assertEqual(agreement["id"], "agr-1")
        self.assertIs(agreement["executed_here"], False)
        self.assertEqual(
            set(agreement.keys()),
            {"id", "commons_id", "disclosure_id", "agreement_ref",
             "counterparty_ref", "terms_label", "executed_here",
             "created_by", "created_utc"})
        # The stored agreement carries no state key: current state
        # is derived at read, never stored.
        self.assertNotIn("state", agreement)
        self.assertNotIn("current_state", agreement)

    def test_current_state_derived_from_latest(self):
        _disclosure, agreement = self._agreement()
        view = self.add.agreement_view(MEMBER, agreement["id"])
        self.assertIsNone(view["current_state"])
        self.assertEqual(view["state_record_count"], 0)
        first = self.add.record_agreement_state(
            MEMBER, agreement["id"], "reported_proposed", "tto report")
        self.assertEqual(first["id"], "ags-1")
        self.assertIs(first["executed_here"], False)
        self.assertEqual(
            set(first.keys()),
            {"id", "commons_id", "agreement_id", "state_label",
             "source_label", "executed_here", "created_by", "created_utc"})
        self.add.record_agreement_state(
            MEMBER, agreement["id"], "reported_negotiated", "tto report")
        self.add.record_agreement_state(
            MEMBER, agreement["id"], "reported_executed", "tto report")
        view = self.add.agreement_view(MEMBER, agreement["id"])
        self.assertEqual(view["current_state"], "reported_executed")
        self.assertEqual(view["state_record_count"], 3)
        self.assertIs(view["derived"], True)
        stored = self.add.get_agreement(MEMBER, agreement["id"])
        self.assertNotIn("current_state", stored)

    def test_bad_state_label_rejected_whole(self):
        _disclosure, agreement = self._agreement()
        with self.assertRaises(ValidationError):
            self.add.record_agreement_state(
                MEMBER, agreement["id"], "executed", "unreported label")
        state = self.add.record_agreement_state(
            MEMBER, agreement["id"], "reported_proposed", "tto report")
        self.assertEqual(state["id"], "ags-1")

    def test_summary_recounts_by_derived_current_state(self):
        _disclosure, agreement = self._agreement()
        self.add.record_agreement_state(
            MEMBER, agreement["id"], "reported_proposed", "tto report")
        self.add.record_agreement_state(
            MEMBER, agreement["id"], "reported_lapsed", "tto report")
        summary = self.add.tech_transfer_summary(MEMBER, self.cid)
        self.assertEqual(summary["disclosures"], 1)
        self.assertEqual(summary["agreements"], 1)
        self.assertEqual(summary["agreement_states"], 2)
        self.assertEqual(summary["agreements_by_current_state"],
                         {"reported_lapsed": 1})
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertIs(summary["executed_here"], False)


class TestInteractiveEnvironments(AdditionFixture):
    """Idx 580 — interactive analysis environment (reference)."""

    def test_definition_is_labeled_reference(self):
        workspace = make_workspace(self.store, self.commons)
        environment = self.add.record_environment(
            MEMBER, self.cid, "ENV-TERRA-1", ["tool:jupyterlab", "tool:rstudio"],
            workspace_id=workspace["id"])
        self.assertEqual(environment["id"], "env-1")
        self.assertIs(environment["reference_stub"], True)
        self.assertEqual(environment["state"], "recorded_reference_only")
        self.assertIs(environment["provisioned_here"], False)
        self.assertIs(environment["executed_here"], False)
        self.assertEqual(
            set(environment.keys()),
            {"id", "commons_id", "workspace_id", "environment_ref",
             "tool_refs", "reference_stub", "state", "provisioned_here",
             "executed_here", "created_by", "created_utc"})
        view = self.add.environment_view(MEMBER, environment["id"])
        self.assertEqual(view["tool_count"], 2)
        stored = self.add.get_environment(MEMBER, environment["id"])
        self.assertNotIn("tool_count", stored)

    def test_session_outcomes_are_reported_only(self):
        environment = self.add.record_environment(
            MEMBER, self.cid, "ENV-TERRA-1", ["tool:jupyterlab"])
        session = self.add.record_environment_session(
            MEMBER, environment["id"], "reported_completed",
            "environment session report")
        self.assertEqual(session["id"], "esn-1")
        self.assertIs(session["reference_stub"], True)
        self.assertIs(session["provisioned_here"], False)
        self.assertIs(session["executed_here"], False)
        with self.assertRaises(ValidationError):
            self.add.record_environment_session(
                MEMBER, environment["id"], "completed", "bad label")


class TestDiagnosticMonitoring(AdditionFixture):
    """Idx 582 — diagnostic monitoring & BioBank tracking (reference)."""

    def test_sample_shape_opaque_ref_only(self):
        sample = self.add.record_sample(
            MEMBER, self.cid, "SMP-EXT-0001", "variant-surveillance-panel")
        self.assertEqual(sample["id"], "smp-1")
        self.assertIs(sample["reference_stub"], True)
        self.assertEqual(sample["state"], "recorded_reference_only")
        self.assertIs(sample["monitored_here"], False)
        self.assertEqual(
            set(sample.keys()),
            {"id", "commons_id", "sample_ref", "panel_label",
             "reference_stub", "state", "monitored_here", "created_by",
             "created_utc"})

    def test_no_subject_or_diagnosis_field_can_be_supplied(self):
        with self.assertRaises(TypeError):
            self.add.record_sample(
                MEMBER, self.cid, "SMP-EXT-0002", "panel",
                diagnosis="positive")
        with self.assertRaises(TypeError):
            self.add.record_sample(
                MEMBER, self.cid, "SMP-EXT-0002", "panel",
                subject_ref="PERSON-1")
        sample = self.add.record_sample(
            MEMBER, self.cid, "SMP-EXT-0002", "panel")
        self.assertEqual(sample["id"], "smp-1")

    def test_outcomes_verbatim_and_summary(self):
        sample = self.add.record_sample(
            MEMBER, self.cid, "SMP-EXT-0001", "variant-surveillance-panel")
        outcome = self.add.record_monitor_outcome(
            MEMBER, sample["id"], "reported_detected",
            "diagnostic platform report")
        self.assertEqual(outcome["id"], "mon-1")
        self.assertIs(outcome["monitored_here"], False)
        self.assertIs(outcome["reference_stub"], True)
        self.assertEqual(
            set(outcome.keys()),
            {"id", "commons_id", "sample_id", "outcome_label",
             "source_label", "reference_stub", "state", "monitored_here",
             "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            self.add.record_monitor_outcome(
                MEMBER, sample["id"], "detected", "bad label")
        summary = self.add.monitoring_summary(MEMBER, self.cid)
        self.assertEqual(summary["samples"], 1)
        self.assertEqual(summary["outcomes"], 1)
        self.assertEqual(summary["outcomes_by_label"],
                         {"reported_detected": 1})
        self.assertIs(summary["monitored_here"], False)


class TestKnowledgeGraph(AdditionFixture):
    """Idx 583 — knowledge-graph storage & library engine (reference)."""

    def _nodes(self):
        first = self.add.record_graph_node(
            MEMBER, self.cid, "NODE-DATASET-1", "dataset node", "DS-REF-1")
        second = self.add.record_graph_node(
            MEMBER, self.cid, "NODE-STUDY-1", "study node", "STUDY-REF-1")
        return first, second

    def test_node_shape_is_metadata_reference(self):
        node, _second = self._nodes()
        self.assertEqual(node["id"], "gnd-1")
        self.assertIs(node["reference_stub"], True)
        self.assertIs(node["data_held_here"], False)
        self.assertIs(node["traversed_here"], False)
        self.assertEqual(
            set(node.keys()),
            {"id", "commons_id", "node_ref", "node_label", "resource_ref",
             "reference_stub", "state", "data_held_here",
             "traversed_here", "created_by", "created_utc"})

    def test_edge_requires_recorded_endpoints(self):
        self._nodes()
        edge = self.add.record_graph_edge(
            MEMBER, self.cid, "EDGE-1", "NODE-DATASET-1", "NODE-STUDY-1",
            "derived_from")
        self.assertEqual(edge["id"], "ged-1")
        self.assertIs(edge["traversed_here"], False)
        self.assertEqual(
            set(edge.keys()),
            {"id", "commons_id", "edge_ref", "from_node_ref",
             "to_node_ref", "relation_label", "reference_stub", "state",
             "data_held_here", "traversed_here", "created_by",
             "created_utc"})
        with self.assertRaises(ValidationError):
            self.add.record_graph_edge(
                MEMBER, self.cid, "EDGE-2", "NODE-DATASET-1",
                "NODE-MISSING", "derived_from")
        summary = self.add.graph_summary(MEMBER, self.cid)
        self.assertEqual(summary["nodes"], 2)
        self.assertEqual(summary["edges"], 1)
        self.assertIs(summary["traversed_here"], False)


class TestSurveyPlatform(AdditionFixture):
    """Idx 585 — multi-modal survey research platform (reference)."""

    def test_definition_and_reported_counts(self):
        survey = self.add.record_survey(
            MEMBER, self.cid, "SURVEY-1",
            ["channel:digital", "channel:paper"])
        self.assertEqual(survey["id"], "srv-1")
        self.assertIs(survey["reference_stub"], True)
        self.assertIs(survey["collected_here"], False)
        self.assertEqual(
            set(survey.keys()),
            {"id", "commons_id", "survey_ref", "channel_refs",
             "reference_stub", "state", "collected_here", "created_by",
             "created_utc"})
        view = self.add.survey_view(MEMBER, survey["id"])
        self.assertEqual(view["channel_count"], 2)
        report = self.add.record_survey_responses(
            MEMBER, survey["id"], 1320, "survey platform report")
        self.assertEqual(report["id"], "srr-1")
        self.assertEqual(report["responses_reported"], 1320)
        self.assertIs(report["collected_here"], False)
        with self.assertRaises(TypeError):
            self.add.record_survey_responses(
                MEMBER, survey["id"], 5, "report",
                responses_payload="raw answers")
        summary = self.add.survey_summary(MEMBER, self.cid)
        self.assertEqual(summary["surveys"], 1)
        self.assertEqual(summary["responses_reported_total"], 1320)
        self.assertIs(summary["collected_here"], False)


class TestDocumentWorkflows(AdditionFixture):
    """Idx 588 — document generation, e-signature, integrations (reference)."""

    def test_docgen_request_holds_output_as_opaque_ref(self):
        request = self.add.request_document_generation(
            MEMBER, self.cid, "DOCGEN-1", "template:license-pdf",
            "OUTPUT-REF-1")
        self.assertEqual(request["id"], "dgr-1")
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["generated_here"], False)
        self.assertEqual(
            set(request.keys()),
            {"id", "commons_id", "request_ref", "template_ref",
             "output_ref", "reference_stub", "state", "generated_here",
             "created_by", "created_utc"})

    def test_signing_request_has_no_signature_value_field(self):
        request = self.add.request_signing(
            MEMBER, self.cid, "SIGN-1", "OUTPUT-REF-1", "SIGNER-REF-1")
        self.assertEqual(request["id"], "sgr-1")
        self.assertIs(request["signed_here"], False)
        self.assertIs(request["reference_stub"], True)
        self.assertEqual(
            set(request.keys()),
            {"id", "commons_id", "request_ref", "document_ref",
             "signer_ref", "reference_stub", "state", "signed_here",
             "created_by", "created_utc"})
        with self.assertRaises(TypeError):
            self.add.request_signing(
                MEMBER, self.cid, "SIGN-2", "OUTPUT-REF-1", "SIGNER-REF-1",
                signature_value="base64-of-a-signature")

    def test_integration_reference_and_summary(self):
        reference = self.add.record_integration_reference(
            MEMBER, self.cid, "iedison-api", "iEdison API push component")
        self.assertEqual(reference["id"], "igr-1")
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["connected_here"], False)
        self.add.request_document_generation(
            MEMBER, self.cid, "DOCGEN-1", "template:license-pdf",
            "OUTPUT-REF-1")
        self.add.request_signing(
            MEMBER, self.cid, "SIGN-1", "OUTPUT-REF-1", "SIGNER-REF-1")
        summary = self.add.document_workflow_summary(MEMBER, self.cid)
        self.assertEqual(summary["docgen_requests"], 1)
        self.assertEqual(summary["signing_requests"], 1)
        self.assertEqual(summary["integration_references"], 1)
        self.assertIs(summary["generated_here"], False)
        self.assertIs(summary["signed_here"], False)
        self.assertIs(summary["connected_here"], False)


class TestAdditionDiscipline(AdditionFixture):
    """Cross-cutting: boundaries, audit, and the forbidden-key scan."""

    def test_outsider_and_viewer_writes_denied_and_audited(self):
        # The outsider is denied by the core store's commons
        # membership boundary; the viewer is denied by the RBAC
        # guard, which records the denied attempt on the audit log.
        with self.assertRaises(PermissionDenied):
            self.add.record_sample(OUTSIDER, self.cid, "SMP-X", "panel")
        with self.assertRaises(PermissionDenied):
            self.add.record_survey(VIEWER, self.cid, "SURVEY-X",
                                   ["channel:digital"])
        self.assertIn("add_survey_record:denied", self.audit_actions())

    def test_missing_record_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.add.get_analysis_pipeline(MEMBER, "bpd-99")
        with self.assertRaises(NotFoundError):
            self.add.get_agreement(MEMBER, "agr-99")

    def test_forbidden_key_scan_over_populated_surface(self):
        dataset, workspace, pipeline = self._pipeline()
        request = self.add.request_pipeline_run(
            MEMBER, pipeline["id"], "RUN-REQ-1", "Refresh")
        outcome = self.add.record_pipeline_run_outcome(
            MEMBER, request["id"], "reported_completed", 5, "report")
        alloc = self.add.request_allocation(
            MEMBER, self.cid, "ALLOC-1", "storage-units", 10, "Archive")
        alloc_outcome = self.add.record_allocation_outcome(
            MEMBER, alloc["id"], "reported_granted", 10, "report")
        analysis = self.add.request_analysis(
            MEMBER, self.cid, "AN-1", "summarize", "INPUT-REF-1")
        result = self.add.record_analysis_result(
            MEMBER, analysis["id"], "RESULT-REF-1", "report")
        disclosure = self.add.record_disclosure(
            MEMBER, self.cid, "DISC-1", "Method", ORG_HOLDER)
        agreement = self.add.record_agreement(
            MEMBER, self.cid, "AGR-1", "CP-REF-1", "terms:x",
            disclosure_id=disclosure["id"])
        state = self.add.record_agreement_state(
            MEMBER, agreement["id"], "reported_proposed", "report")
        environment = self.add.record_environment(
            MEMBER, self.cid, "ENV-1", ["tool:jupyterlab"])
        session = self.add.record_environment_session(
            MEMBER, environment["id"], "reported_completed", "report")
        sample = self.add.record_sample(
            MEMBER, self.cid, "SMP-1", "panel")
        monitor = self.add.record_monitor_outcome(
            MEMBER, sample["id"], "reported_inconclusive", "report")
        node = self.add.record_graph_node(
            MEMBER, self.cid, "NODE-1", "node", "RES-REF-1")
        self.add.record_graph_node(
            MEMBER, self.cid, "NODE-2", "node", "RES-REF-2")
        edge = self.add.record_graph_edge(
            MEMBER, self.cid, "EDGE-1", "NODE-1", "NODE-2", "related_to")
        survey = self.add.record_survey(
            MEMBER, self.cid, "SURVEY-1", ["channel:digital"])
        responses = self.add.record_survey_responses(
            MEMBER, survey["id"], 7, "report")
        docgen = self.add.request_document_generation(
            MEMBER, self.cid, "DOCGEN-1", "template:t", "OUT-REF-1")
        signing = self.add.request_signing(
            MEMBER, self.cid, "SIGN-1", "OUT-REF-1", "SIGNER-REF-1")
        integration = self.add.record_integration_reference(
            MEMBER, self.cid, "iedison-api", "iEdison API push")
        surface = [
            pipeline, request, outcome, alloc, alloc_outcome, analysis,
            result, disclosure, agreement, state,
            self.add.agreement_view(MEMBER, agreement["id"]),
            environment, session, sample, monitor, node, edge, survey,
            responses, docgen, signing, integration,
            self.add.pipeline_summary(MEMBER, self.cid),
            self.add.allocation_summary(MEMBER, self.cid),
            self.add.analysis_summary(MEMBER, self.cid),
            self.add.tech_transfer_summary(MEMBER, self.cid),
            self.add.monitoring_summary(MEMBER, self.cid),
            self.add.graph_summary(MEMBER, self.cid),
            self.add.survey_summary(MEMBER, self.cid),
            self.add.document_workflow_summary(MEMBER, self.cid),
        ]
        offenders = []
        for item in surface:
            for path, key in _scan_keys(item):
                for fragment in FORBIDDEN_KEY_FRAGMENTS:
                    if fragment in key:
                        offenders.append((path, key))
        self.assertEqual(offenders, [])


class _EarliestAgreementState(ResearchAdditions):
    """Mutant: the agreement derivation reads the EARLIEST state."""

    @staticmethod
    def _current_agreement_label(states):
        if not states:
            return None
        return states[0]["state_label"]


class TestAgreementDerivationNegativeControl(AdditionFixture):
    """The addition's fresh negative control.

    Canonical invariant: an agreement's current state is its
    LATEST recorded reported-* label, derived at read by the
    single seam ``ResearchAdditions._current_agreement_label`` and
    never stored. The mutant subclass reads the earliest label
    instead; the canonical expectations must reject its outcome.
    """

    def _three_states(self, additions):
        disclosure = additions.record_disclosure(
            MEMBER, self.cid, "DISC-1", "Sample multiplexing method",
            ORG_HOLDER)
        agreement = additions.record_agreement(
            MEMBER, self.cid, "AGR-1", "COUNTERPARTY-REF-1",
            "terms:master-license-v3", disclosure_id=disclosure["id"])
        additions.record_agreement_state(
            MEMBER, agreement["id"], "reported_proposed", "tto report")
        additions.record_agreement_state(
            MEMBER, agreement["id"], "reported_negotiated", "tto report")
        additions.record_agreement_state(
            MEMBER, agreement["id"], "reported_executed", "tto report")
        return agreement

    def test_canonical_reads_latest_state(self):
        agreement = self._three_states(self.add)
        view = self.add.agreement_view(MEMBER, agreement["id"])
        self.assertEqual(view["current_state"], "reported_executed")

    def test_mutant_reads_earliest_state(self):
        mutant = _EarliestAgreementState(self.store)
        agreement = self._three_states(mutant)
        view = mutant.agreement_view(MEMBER, agreement["id"])
        self.assertEqual(view["current_state"], "reported_proposed")

    def test_canonical_expectation_rejects_mutant(self):
        mutant = _EarliestAgreementState(self.store)
        agreement = self._three_states(mutant)
        view = mutant.agreement_view(MEMBER, agreement["id"])
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_state"], "reported_executed")


if __name__ == "__main__":
    unittest.main()
