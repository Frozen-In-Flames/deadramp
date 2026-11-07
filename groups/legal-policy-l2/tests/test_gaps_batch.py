"""Final GAPS batch tests — Legal & Policy L2 remainder additions.

Pins the extension surface in ``src/legalpol/extensions.py`` per
GAPS.md section "Remainder Addition -- Legal & Policy L2 (+6
forks)" entry (inventory idx 561-570; see ``../BATCH.md`` for the
per-entry disposition), and the founding privacy discipline: no
record shape can hold document content, extracted text, a summary,
a signature value, or query text — every entity shape is pinned to
its exact key set, and an unexpected keyword argument raises
``TypeError``.

The batch's fresh negative control lives here:
``TestHoldDerivationNegativeControl`` mutates the extension's
single hold-derivation seam (``_current_hold_label``) to read the
EARLIEST recorded state instead of the latest, and pins that the
canonical expectations reject the mutant's outcomes — in the hold
view, in disposition eligibility, and in the discovery analytics
active-hold count.
"""

import unittest

from legalpol.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from legalpol.extensions import LegalPolExtensions

from legalpol_helpers import (
    ADMIN,
    DOC_SHA256,
    MEMBER,
    OUTSIDER,
    SHA256_A,
    VIEWER,
    make_store,
    make_workspace,
)

FORBIDDEN_KEY_FRAGMENTS = (
    "signature", "query", "summary", "score", "extracted_text",
    "content_text", "document_content", "raw_content",
)


def make_extensions():
    """Fresh store + canonical agency/workspace + extension surface."""
    store, audit, agency = make_store()
    workspace = make_workspace(store, agency)
    return LegalPolExtensions(store), store, audit, agency, workspace


def make_document(store, agency, workspace, doc_ref="DOC-REF-001",
                  sha256=DOC_SHA256):
    return store.register_document(
        agency["id"], workspace["id"], doc_ref, sha256, 128, MEMBER)


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
        (self.ext, self.store, self.audit, self.agency,
         self.workspace) = make_extensions()
        self.aid = self.agency["id"]
        self.wid = self.workspace["id"]
        self.doc = make_document(self.store, self.agency, self.workspace)
        self.doc2 = make_document(self.store, self.agency, self.workspace,
                                  doc_ref="DOC-REF-002", sha256=SHA256_A)

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def _matter(self, matter_ref="MAT-REF-001", kind="litigation"):
        return self.ext.create_matter(
            MEMBER, self.aid, self.wid, matter_ref, kind)

    def _hold(self, matter=None, hold_ref="HOLD-REF-001"):
        matter = matter or self._matter()
        return self.ext.create_hold(
            MEMBER, self.aid, matter["id"], hold_ref, "CUSTODIAN-REF-1")


class TestMattersAndCollections(BatchFixture):
    """Idx 561 — eDiscovery processing & collection engine (built)."""

    def test_matter_shape_pinned(self):
        matter = self._matter()
        self.assertEqual(matter["id"], "mat-1")
        self.assertEqual(
            set(matter.keys()),
            {"id", "agency_id", "workspace_id", "matter_ref", "kind",
             "label", "content_collected_here", "created_by", "created_utc"})
        self.assertIs(matter["content_collected_here"], False)

    def test_bad_kind_and_duplicate_ref_consume_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.create_matter(MEMBER, self.aid, self.wid, "M-1", "bogus")
        matter = self._matter()
        with self.assertRaises(ValidationError):
            self.ext.create_matter(
                MEMBER, self.aid, self.wid, "MAT-REF-001", "foia")
        second = self.ext.create_matter(
            MEMBER, self.aid, self.wid, "MAT-REF-002", "foia")
        self.assertEqual(second["id"], "mat-2")
        self.assertEqual(matter["id"], "mat-1")

    def test_collection_records_counts_as_reported(self):
        matter = self._matter()
        collection = self.ext.record_collection(
            MEMBER, self.aid, matter["id"], "COL-REF-1", "custodian export",
            42, 10_000)
        self.assertEqual(collection["id"], "col-1")
        self.assertEqual(
            set(collection.keys()),
            {"id", "agency_id", "matter_id", "collection_ref", "source_label",
             "reported_document_count", "reported_byte_count",
             "content_collected_here", "processing_performed_here",
             "created_by", "created_utc"})
        self.assertIs(collection["content_collected_here"], False)
        self.assertIs(collection["processing_performed_here"], False)
        for bad in (-1, 1.5, True, "42"):
            with self.assertRaises(ValidationError):
                self.ext.record_collection(
                    MEMBER, self.aid, matter["id"], "COL-REF-2", "x", bad, 0)

    def test_links_and_processing_runs_derive_view_counts(self):
        matter = self._matter()
        collection = self.ext.record_collection(
            MEMBER, self.aid, matter["id"], "COL-REF-1", "mailbox export",
            2, 256)
        self.ext.link_collection_document(
            MEMBER, self.aid, collection["id"], self.doc["id"])
        self.ext.link_collection_document(
            MEMBER, self.aid, collection["id"], self.doc2["id"])
        with self.assertRaises(ValidationError):
            self.ext.link_collection_document(
                MEMBER, self.aid, collection["id"], self.doc["id"])
        run = self.ext.record_processing_run(
            MEMBER, self.aid, collection["id"], "RUN-1", 2, 0)
        self.assertEqual(
            set(run.keys()),
            {"id", "agency_id", "collection_id", "run_ref",
             "reported_processed_count", "reported_error_count",
             "processing_performed_here", "created_by", "created_utc"})
        self.assertIs(run["processing_performed_here"], False)
        stored = self.ext.get_collection(MEMBER, self.aid, collection["id"])
        self.assertNotIn("linked_document_count", stored)
        view = self.ext.collection_view(MEMBER, self.aid, collection["id"])
        self.assertEqual(view["linked_document_count"], 2)
        self.assertEqual(view["processing_run_count"], 1)

    def test_content_kwargs_raise_type_error(self):
        matter = self._matter()
        with self.assertRaises(TypeError):
            self.ext.record_collection(
                MEMBER, self.aid, matter["id"], "COL-REF-9", "x", 1, 1,
                content=b"raw bytes")
        with self.assertRaises(TypeError):
            self.ext.create_matter(
                MEMBER, self.aid, self.wid, "M-9", "foia", text="body")


class TestLegalHolds(BatchFixture):
    """Idx 564 — legal hold & preservation management (built)."""

    def test_hold_shape_and_state_vocabulary(self):
        hold = self._hold()
        self.assertEqual(
            set(hold.keys()),
            {"id", "agency_id", "matter_id", "hold_ref", "custodian_ref",
             "preserved_here", "created_by", "created_utc"})
        self.assertIs(hold["preserved_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_hold_state(
                MEMBER, self.aid, hold["id"], "sort_of_issued")

    def test_current_state_derived_from_latest(self):
        hold = self._hold()
        view = self.ext.hold_view(MEMBER, self.aid, hold["id"])
        self.assertEqual(view["current_state"], "recorded")
        self.assertIs(view["is_active"], False)
        self.assertEqual(view["state_record_count"], 0)
        self.ext.record_hold_state(
            MEMBER, self.aid, hold["id"], "reported_issued")
        self.ext.record_hold_state(
            MEMBER, self.aid, hold["id"], "reported_acknowledged")
        view = self.ext.hold_view(MEMBER, self.aid, hold["id"])
        self.assertEqual(view["current_state"], "reported_acknowledged")
        self.assertIs(view["is_active"], True)
        self.ext.record_hold_state(
            MEMBER, self.aid, hold["id"], "reported_released")
        view = self.ext.hold_view(MEMBER, self.aid, hold["id"])
        self.assertEqual(view["current_state"], "reported_released")
        self.assertIs(view["is_active"], False)
        self.assertEqual(view["state_record_count"], 3)
        stored = self.ext.get_hold(MEMBER, self.aid, hold["id"])
        self.assertNotIn("current_state", stored)
        self.assertNotIn("is_active", stored)

    def test_coverage_records_and_view(self):
        hold = self._hold()
        coverage = self.ext.add_hold_coverage(
            MEMBER, self.aid, hold["id"], self.doc["id"])
        self.assertEqual(
            set(coverage.keys()),
            {"id", "agency_id", "hold_id", "document_id", "preserved_here",
             "created_by", "created_utc"})
        self.assertIs(coverage["preserved_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.add_hold_coverage(
                MEMBER, self.aid, hold["id"], self.doc["id"])
        view = self.ext.hold_view(MEMBER, self.aid, hold["id"])
        self.assertEqual(view["covered_document_ids"], [self.doc["id"]])
        self.assertEqual(view["covered_document_count"], 1)


class TestReview(BatchFixture):
    """Idx 562 — eDiscovery document review platform (built)."""

    def test_assignment_and_decision_shapes(self):
        matter = self._matter()
        assignment = self.ext.assign_review(
            MEMBER, self.aid, matter["id"], self.doc["id"], "REVIEWER-REF-1")
        self.assertEqual(
            set(assignment.keys()),
            {"id", "agency_id", "matter_id", "document_id", "reviewer_ref",
             "content_reviewed_here", "created_by", "created_utc"})
        self.assertIs(assignment["content_reviewed_here"], False)
        decision = self.ext.record_review_decision(
            MEMBER, self.aid, assignment["id"], "privileged")
        self.assertEqual(
            set(decision.keys()),
            {"id", "agency_id", "assignment_id", "decision_label",
             "content_reviewed_here", "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            self.ext.record_review_decision(
                MEMBER, self.aid, assignment["id"], "looks_fine")

    def test_decision_changes_no_core_document_record(self):
        matter = self._matter()
        before = self.store.get_document(self.aid, self.doc["id"], MEMBER)
        assignment = self.ext.assign_review(
            MEMBER, self.aid, matter["id"], self.doc["id"], "REVIEWER-REF-1")
        self.ext.record_review_decision(
            MEMBER, self.aid, assignment["id"], "responsive")
        self.ext.record_review_decision(
            MEMBER, self.aid, assignment["id"], "needs_follow_up")
        after = self.store.get_document(self.aid, self.doc["id"], MEMBER)
        self.assertEqual(before, after)
        view = self.ext.assignment_view(MEMBER, self.aid, assignment["id"])
        self.assertEqual(view["decision_count"], 2)
        self.assertEqual(view["latest_decision_label"], "needs_follow_up")


class TestProductionDisposition(BatchFixture):
    """Idx 563 — production, disposition & archiving engine (built)."""

    def test_production_record_link_and_view(self):
        matter = self._matter()
        production = self.ext.record_production(
            MEMBER, self.aid, matter["id"], "PROD-REF-1", 2)
        self.assertEqual(
            set(production.keys()),
            {"id", "agency_id", "matter_id", "production_ref",
             "reported_document_count", "production_executed_here",
             "created_by", "created_utc"})
        self.assertIs(production["production_executed_here"], False)
        self.ext.link_production_document(
            MEMBER, self.aid, production["id"], self.doc["id"])
        view = self.ext.production_view(MEMBER, self.aid, production["id"])
        self.assertEqual(view["linked_document_count"], 1)

    def test_disposition_eligible_without_hold(self):
        matter = self._matter()
        view = self.ext.disposition_view(
            MEMBER, self.aid, matter["id"], self.doc["id"])
        self.assertIs(view["under_active_hold"], False)
        self.assertIs(view["eligible_for_disposition"], True)
        self.assertIs(view["executed_here"], False)
        decision = self.ext.record_disposition_decision(
            MEMBER, self.aid, matter["id"], self.doc["id"], "archive_reported")
        self.assertEqual(
            set(decision.keys()),
            {"id", "agency_id", "matter_id", "document_id", "decision_label",
             "executed_here", "created_by", "created_utc"})
        self.assertIs(decision["executed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_disposition_decision(
                MEMBER, self.aid, matter["id"], self.doc["id"], "shredded")

    def test_disposition_blocked_until_hold_released(self):
        matter = self._matter()
        hold = self.ext.create_hold(
            MEMBER, self.aid, matter["id"], "HOLD-REF-1", "CUSTODIAN-REF-1")
        self.ext.add_hold_coverage(MEMBER, self.aid, hold["id"], self.doc["id"])
        self.ext.record_hold_state(
            MEMBER, self.aid, hold["id"], "reported_issued")
        view = self.ext.disposition_view(
            MEMBER, self.aid, matter["id"], self.doc["id"])
        self.assertIs(view["under_active_hold"], True)
        self.assertEqual(view["active_hold_ids"], [hold["id"]])
        self.assertIs(view["eligible_for_disposition"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_disposition_decision(
                MEMBER, self.aid, matter["id"], self.doc["id"],
                "destroy_reported")
        self.ext.record_hold_state(
            MEMBER, self.aid, hold["id"], "reported_released")
        decision = self.ext.record_disposition_decision(
            MEMBER, self.aid, matter["id"], self.doc["id"], "destroy_reported")
        self.assertEqual(decision["id"], "dsp-1")
        view = self.ext.disposition_view(
            MEMBER, self.aid, matter["id"], self.doc["id"])
        self.assertEqual(view["disposition_decision_count"], 1)


class TestAnalysis(BatchFixture):
    """Idx 565 — AI document analysis for discovery (built)."""

    def test_request_and_result_shapes_hold_no_output_text(self):
        matter = self._matter()
        request = self.ext.request_analysis(
            MEMBER, self.aid, matter["id"], self.doc["id"], "summarization",
            "ANR-REF-1")
        self.assertEqual(
            set(request.keys()),
            {"id", "agency_id", "matter_id", "document_id", "analysis_kind",
             "request_ref", "inference_here", "created_by", "created_utc"})
        self.assertIs(request["inference_here"], False)
        result = self.ext.record_analysis_result(
            MEMBER, self.aid, request["id"], "result:opaque-1",
            reported_label="responsive")
        self.assertEqual(
            set(result.keys()),
            {"id", "agency_id", "request_id", "result_ref", "reported_label",
             "inference_here", "created_by", "created_utc"})
        view = self.ext.analysis_request_view(MEMBER, self.aid, request["id"])
        self.assertEqual(view["result_count"], 1)
        with self.assertRaises(ValidationError):
            self.ext.request_analysis(
                MEMBER, self.aid, matter["id"], self.doc["id"], "telepathy",
                "ANR-REF-2")

    def test_output_text_kwargs_raise_type_error(self):
        matter = self._matter()
        with self.assertRaises(TypeError):
            self.ext.request_analysis(
                MEMBER, self.aid, matter["id"], self.doc["id"],
                "classification", "ANR-REF-9", summary="the summary")
        request = self.ext.request_analysis(
            MEMBER, self.aid, matter["id"], self.doc["id"], "redaction",
            "ANR-REF-1")
        with self.assertRaises(TypeError):
            self.ext.record_analysis_result(
                MEMBER, self.aid, request["id"], "result:x",
                redaction_text="redacted body")

    def test_discovery_analytics_are_deterministic_counts(self):
        matter = self._matter()
        collection = self.ext.record_collection(
            MEMBER, self.aid, matter["id"], "COL-REF-1", "export", 2, 10)
        self.ext.link_collection_document(
            MEMBER, self.aid, collection["id"], self.doc["id"])
        assignment = self.ext.assign_review(
            MEMBER, self.aid, matter["id"], self.doc["id"], "REVIEWER-REF-1")
        self.ext.record_review_decision(
            MEMBER, self.aid, assignment["id"], "responsive")
        self.ext.record_review_decision(
            MEMBER, self.aid, assignment["id"], "responsive")
        self.ext.request_analysis(
            MEMBER, self.aid, matter["id"], self.doc["id"], "analytics",
            "ANR-REF-1")
        analytics = self.ext.discovery_analytics(MEMBER, self.aid, matter["id"])
        self.assertEqual(analytics["collections"], 1)
        self.assertEqual(analytics["collection_documents"], 1)
        self.assertEqual(analytics["review_assignments"], 1)
        self.assertEqual(analytics["review_decisions"], 2)
        self.assertEqual(
            analytics["review_decisions_by_label"], {"responsive": 2})
        self.assertEqual(analytics["analysis_requests_by_kind"],
                         {"analytics": 1})
        self.assertEqual(analytics["method"], "deterministic_counts")
        self.assertIs(analytics["inference_here"], False)


class TestExtraction(BatchFixture):
    """Idx 566 — OCR & document extraction engine (built)."""

    def test_job_shape_and_count_discipline(self):
        matter = self._matter()
        job = self.ext.record_extraction_job(
            MEMBER, self.aid, matter["id"], self.doc["id"], "OCR-REF-1",
            12, 340, "result:opaque-ocr-1")
        self.assertEqual(
            set(job.keys()),
            {"id", "agency_id", "matter_id", "document_id", "job_ref",
             "reported_page_count", "reported_field_count", "result_ref",
             "extracted_here", "created_by", "created_utc"})
        self.assertIs(job["extracted_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_extraction_job(
                MEMBER, self.aid, matter["id"], self.doc["id"], "OCR-REF-2",
                1.5, 0, "result:x")

    def test_extracted_text_kwarg_raises_type_error(self):
        matter = self._matter()
        with self.assertRaises(TypeError):
            self.ext.record_extraction_job(
                MEMBER, self.aid, matter["id"], self.doc["id"], "OCR-REF-9",
                1, 1, "result:x", extracted_text="page one text")


class TestFoia(BatchFixture):
    """Idx 567 — FOIA & disclosure release engine (built)."""

    def _case(self):
        return self.ext.create_foia_case(
            MEMBER, self.aid, self.wid, "FOIA-REF-001", "REQ-REF-1",
            "REQUESTER-REF-1")

    def test_case_shape_and_derived_state(self):
        case = self._case()
        self.assertEqual(
            set(case.keys()),
            {"id", "agency_id", "workspace_id", "case_ref", "request_ref",
             "requester_ref", "released_here", "created_by", "created_utc"})
        self.assertIs(case["released_here"], False)
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"])
        self.assertEqual(view["current_state"], "recorded")
        self.ext.record_foia_state(
            MEMBER, self.aid, case["id"], "reported_received")
        self.ext.record_foia_state(
            MEMBER, self.aid, case["id"], "reported_processing")
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"])
        self.assertEqual(view["current_state"], "reported_processing")
        self.assertEqual(view["state_record_count"], 2)
        stored = self.ext.get_foia_case(MEMBER, self.aid, case["id"])
        self.assertNotIn("current_state", stored)
        with self.assertRaises(ValidationError):
            self.ext.record_foia_state(
                MEMBER, self.aid, case["id"], "reported_lost")

    def test_determination_verbatim_and_release_record(self):
        case = self._case()
        determination = self.ext.record_exemption_determination(
            MEMBER, self.aid, case["id"], "exemption_5_deliberative",
            document_id=self.doc["id"])
        self.assertEqual(
            set(determination.keys()),
            {"id", "agency_id", "case_id", "document_id", "exemption_label",
             "released_here", "created_by", "created_utc"})
        self.assertEqual(
            determination["exemption_label"], "exemption_5_deliberative")
        self.assertIs(determination["released_here"], False)
        release = self.ext.record_foia_release(
            MEMBER, self.aid, case["id"], "REL-REF-1", 3)
        self.assertIs(release["released_here"], False)
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"])
        self.assertEqual(view["determination_count"], 1)
        self.assertEqual(view["release_count"], 1)

    def test_request_text_kwarg_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.create_foia_case(
                MEMBER, self.aid, self.wid, "FOIA-REF-9", "REQ-REF-9",
                "REQUESTER-REF-9", request_text="all emails about...")


class TestAgreements(BatchFixture):
    """Idx 569 — contract lifecycle management engine (built)."""

    def test_agreement_shape_and_value_discipline(self):
        agreement = self.ext.create_agreement(
            MEMBER, self.aid, self.wid, "AGR-REF-001", "VENDOR-REF-1",
            value_cents=250_000)
        self.assertEqual(
            set(agreement.keys()),
            {"id", "agency_id", "workspace_id", "agreement_ref",
             "counterparty_ref", "value_cents", "executed_here",
             "created_by", "created_utc"})
        self.assertEqual(agreement["value_cents"], 250000)
        self.assertIs(agreement["executed_here"], False)
        for bad in (1.5, True, -1, "2500"):
            with self.assertRaises(ValidationError):
                self.ext.create_agreement(
                    MEMBER, self.aid, self.wid, "AGR-REF-2", "VENDOR-REF-2",
                    value_cents=bad)

    def test_lifecycle_state_derived_never_stored(self):
        agreement = self.ext.create_agreement(
            MEMBER, self.aid, self.wid, "AGR-REF-001", "VENDOR-REF-1")
        view = self.ext.agreement_view(MEMBER, self.aid, agreement["id"])
        self.assertEqual(view["current_state"], "recorded")
        self.ext.record_agreement_state(
            MEMBER, self.aid, agreement["id"], "reported_draft")
        self.ext.record_agreement_state(
            MEMBER, self.aid, agreement["id"], "reported_executed")
        view = self.ext.agreement_view(MEMBER, self.aid, agreement["id"])
        self.assertEqual(view["current_state"], "reported_executed")
        self.assertEqual(view["state_record_count"], 2)
        stored = self.ext.get_agreement(MEMBER, self.aid, agreement["id"])
        self.assertNotIn("current_state", stored)
        with self.assertRaises(ValidationError):
            self.ext.record_agreement_state(
                MEMBER, self.aid, agreement["id"], "reported_signed_here")


class TestSignatureReference(BatchFixture):
    """Idx 568 — electronic signature engine (reference stub)."""

    def test_envelope_and_ceremony_are_labeled_reference_records(self):
        agreement = self.ext.create_agreement(
            MEMBER, self.aid, self.wid, "AGR-REF-001", "VENDOR-REF-1")
        envelope = self.ext.record_envelope(
            MEMBER, self.aid, "ENV-REF-1", agreement_id=agreement["id"])
        self.assertEqual(
            set(envelope.keys()),
            {"id", "agency_id", "agreement_id", "document_id", "envelope_ref",
             "reference_stub", "state", "signed_here", "created_by",
             "created_utc"})
        self.assertIs(envelope["reference_stub"], True)
        self.assertEqual(envelope["state"], "recorded_reference_only")
        self.assertIs(envelope["signed_here"], False)
        ceremony = self.ext.record_ceremony_event(
            MEMBER, self.aid, envelope["id"], "SIGNER-REF-1", "reported_sent")
        self.assertEqual(
            set(ceremony.keys()),
            {"id", "agency_id", "envelope_id", "signer_ref", "ceremony_label",
             "reference_stub", "signed_here", "created_by", "created_utc"})
        self.assertIs(ceremony["reference_stub"], True)
        self.assertIs(ceremony["signed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_ceremony_event(
                MEMBER, self.aid, envelope["id"], "SIGNER-REF-1",
                "reported_forged")

    def test_signature_value_kwarg_raises_type_error(self):
        envelope = self.ext.record_envelope(MEMBER, self.aid, "ENV-REF-1")
        with self.assertRaises(TypeError):
            self.ext.record_ceremony_event(
                MEMBER, self.aid, envelope["id"], "SIGNER-REF-1",
                "reported_signed", signature="x9f3...")


class TestWorkflowReference(BatchFixture):
    """Idx 570 — agreement workflow automation engine (reference stub)."""

    def test_definition_held_as_data(self):
        definition = self.ext.register_workflow_definition(
            MEMBER, self.aid, "WF-REF-1",
            ["draft", "route_for_signature", "file"])
        self.assertEqual(
            set(definition.keys()),
            {"id", "agency_id", "definition_ref", "steps", "reference_stub",
             "state", "executed_here", "created_by", "created_utc"})
        self.assertIs(definition["reference_stub"], True)
        self.assertEqual(definition["state"], "recorded_reference_only")
        self.assertIs(definition["executed_here"], False)
        self.assertEqual(
            definition["steps"], ["draft", "route_for_signature", "file"])
        with self.assertRaises(ValidationError):
            self.ext.register_workflow_definition(MEMBER, self.aid, "WF-2", [])
        with self.assertRaises(ValidationError):
            self.ext.register_workflow_definition(
                MEMBER, self.aid, "WF-3", ["ok", 7])

    def test_definition_changes_no_agreement_record(self):
        agreement = self.ext.create_agreement(
            MEMBER, self.aid, self.wid, "AGR-REF-001", "VENDOR-REF-1")
        before = self.ext.get_agreement(MEMBER, self.aid, agreement["id"])
        self.ext.register_workflow_definition(
            MEMBER, self.aid, "WF-REF-1", ["draft", "execute", "file"])
        after = self.ext.get_agreement(MEMBER, self.aid, agreement["id"])
        self.assertEqual(before, after)


class TestGuardsAndPrivacy(BatchFixture):
    """Cross-cutting: RBAC, membership boundary, audit, key scan."""

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_matter(VIEWER, self.aid, self.wid, "M-V", "foia")
        self.assertIn("ext_matter_create:denied", self.audit_actions())
        self.assertEqual(self.ext.list_matters(ADMIN, self.aid), [])
        matter = self.ext.create_matter(
            MEMBER, self.aid, self.wid, "M-1", "foia")
        self.assertEqual(matter["id"], "mat-1")

    def test_outsider_denied_by_membership_boundary(self):
        with self.assertRaises(PermissionDenied):
            self.ext.list_matters(OUTSIDER, self.aid)
        with self.assertRaises(PermissionDenied):
            self.ext.create_matter(OUTSIDER, self.aid, self.wid, "M-O", "foia")

    def test_successful_extension_mutations_are_audited(self):
        self._matter()
        self.assertIn("ext_matter_create", self.audit_actions())

    def test_query_text_kwarg_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.create_matter(
                MEMBER, self.aid, self.wid, "M-Q", "foia",
                query_text="presidential records")

    def test_no_forbidden_key_anywhere_on_the_surface(self):
        matter = self._matter()
        collection = self.ext.record_collection(
            MEMBER, self.aid, matter["id"], "COL-REF-1", "export", 1, 5)
        self.ext.link_collection_document(
            MEMBER, self.aid, collection["id"], self.doc["id"])
        hold = self.ext.create_hold(
            MEMBER, self.aid, matter["id"], "HOLD-REF-1", "CUSTODIAN-REF-1")
        self.ext.record_hold_state(
            MEMBER, self.aid, hold["id"], "reported_issued")
        self.ext.add_hold_coverage(MEMBER, self.aid, hold["id"], self.doc["id"])
        assignment = self.ext.assign_review(
            MEMBER, self.aid, matter["id"], self.doc["id"], "REVIEWER-REF-1")
        self.ext.record_review_decision(
            MEMBER, self.aid, assignment["id"], "responsive")
        request = self.ext.request_analysis(
            MEMBER, self.aid, matter["id"], self.doc["id"], "classification",
            "ANR-REF-1")
        self.ext.record_analysis_result(
            MEMBER, self.aid, request["id"], "result:opaque-1")
        self.ext.record_extraction_job(
            MEMBER, self.aid, matter["id"], self.doc["id"], "OCR-REF-1",
            1, 2, "result:opaque-2")
        case = self.ext.create_foia_case(
            MEMBER, self.aid, self.wid, "FOIA-REF-001", "REQ-REF-1",
            "REQUESTER-REF-1")
        agreement = self.ext.create_agreement(
            MEMBER, self.aid, self.wid, "AGR-REF-001", "VENDOR-REF-1")
        envelope = self.ext.record_envelope(
            MEMBER, self.aid, "ENV-REF-1", agreement_id=agreement["id"])
        surface = [
            matter, collection,
            self.ext.collection_view(MEMBER, self.aid, collection["id"]),
            self.ext.hold_view(MEMBER, self.aid, hold["id"]),
            self.ext.assignment_view(MEMBER, self.aid, assignment["id"]),
            self.ext.disposition_view(
                MEMBER, self.aid, matter["id"], self.doc2["id"]),
            self.ext.analysis_request_view(MEMBER, self.aid, request["id"]),
            self.ext.discovery_analytics(MEMBER, self.aid, matter["id"]),
            self.ext.foia_case_view(MEMBER, self.aid, case["id"]),
            self.ext.agreement_view(MEMBER, self.aid, agreement["id"]),
            envelope,
        ]
        for record in surface:
            for path, key in _scan_keys(record):
                for fragment in FORBIDDEN_KEY_FRAGMENTS:
                    self.assertNotIn(
                        fragment, key,
                        "forbidden key fragment %r at %s: %r"
                        % (fragment, path, key))


class MutantHoldExtensions(LegalPolExtensions):
    """The batch drill's mutant: the hold derivation reads the
    EARLIEST recorded state label instead of the latest."""

    @staticmethod
    def _current_hold_label(states):
        if not states:
            return "recorded"
        return states[0]["state_label"]


class TestHoldDerivationNegativeControl(unittest.TestCase):
    """Fresh mutation-verified negative control (batch).

    Canonical expectation: with states [reported_issued,
    reported_released] recorded in that order, the derived current
    state is the LATEST label, ``reported_released`` — the hold is
    inactive, a disposition decision over a covered document can
    be recorded, and the analytics active-hold count is 0. The
    mutant (earliest-label derivation) must NOT produce those
    outcomes, and treating the mutant's outcomes as the expected
    outcomes must fail.
    """

    def _build(self, ext_class):
        store, audit, agency = make_store()
        workspace = make_workspace(store, agency)
        ext = ext_class(store)
        doc = make_document(store, agency, workspace)
        matter = ext.create_matter(
            MEMBER, agency["id"], workspace["id"], "MAT-REF-001",
            "litigation")
        hold = ext.create_hold(
            MEMBER, agency["id"], matter["id"], "HOLD-REF-001",
            "CUSTODIAN-REF-1")
        ext.add_hold_coverage(MEMBER, agency["id"], hold["id"], doc["id"])
        ext.record_hold_state(
            MEMBER, agency["id"], hold["id"], "reported_issued")
        ext.record_hold_state(
            MEMBER, agency["id"], hold["id"], "reported_released")
        return ext, agency, matter, hold, doc

    def test_current_state_is_latest_canonical(self):
        ext, agency, _matter, hold, _doc = self._build(LegalPolExtensions)
        view = ext.hold_view(MEMBER, agency["id"], hold["id"])
        self.assertEqual(view["current_state"], "reported_released")
        self.assertIs(view["is_active"], False)

    def test_mutant_reads_earliest_not_latest(self):
        ext, agency, _matter, hold, _doc = self._build(MutantHoldExtensions)
        view = ext.hold_view(MEMBER, agency["id"], hold["id"])
        self.assertEqual(view["current_state"], "reported_issued")
        self.assertIs(view["is_active"], True)

    def test_canonical_expectation_rejects_mutant(self):
        ext, agency, _matter, hold, _doc = self._build(MutantHoldExtensions)
        view = ext.hold_view(MEMBER, agency["id"], hold["id"])
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_state"], "reported_released")

    def test_mutant_changes_disposition_eligibility(self):
        canonical, agency, matter, _hold, doc = self._build(LegalPolExtensions)
        decision = canonical.record_disposition_decision(
            MEMBER, agency["id"], matter["id"], doc["id"], "destroy_reported")
        self.assertEqual(decision["decision_label"], "destroy_reported")
        mutant, agency2, matter2, _hold2, doc2 = self._build(
            MutantHoldExtensions)
        with self.assertRaises(ValidationError):
            mutant.record_disposition_decision(
                MEMBER, agency2["id"], matter2["id"], doc2["id"],
                "destroy_reported")

    def test_mutant_changes_analytics_active_count(self):
        canonical, agency, matter, _hold, _doc = self._build(LegalPolExtensions)
        mutant, agency2, matter2, _hold2, _doc2 = self._build(
            MutantHoldExtensions)
        self.assertEqual(
            canonical.discovery_analytics(
                MEMBER, agency["id"], matter["id"])["holds_active"], 0)
        self.assertEqual(
            mutant.discovery_analytics(
                MEMBER, agency2["id"], matter2["id"])["holds_active"], 1)


if __name__ == "__main__":
    unittest.main()
