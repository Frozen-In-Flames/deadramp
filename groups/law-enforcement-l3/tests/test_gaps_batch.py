"""Final GAPS batch tests for Law Enforcement L3-adjacent.

Traces to: the 8 open Extended entries of this group's union
spec (``UNION-SPEC.md``, "This group's own verticals", GAPS.md
section "Group 35 -- Law Enforcement L3-adjacent (2 forks)"),
closed by ``lawenf/extensions.py`` under
``../../gaps-batch/DECISION.md``: 6 built as records in-substrate
(forensic analysis, evidence ingest & processing pipelines,
evidence review, chain-of-custody transfer records, information
sharing, forensic reporting) and 2 re-judged to labeled
reference implementations (device unlocking; evidence
extraction from mobile devices -- capabilities that defeat
device access controls are not built in any form; grounds in
``../BATCH.md``).

Every test names the entry it pins. Cross-cutting pins: the hard
privacy rule binds the whole extension surface (exact key sets;
no parameter can accept evidence content, a finding's or
report's text, or a person's identifier -- ``TypeError`` by
signature); reference records carry ``reference_stub: True``;
share records and receipts carry ``reference_transport: True``;
extension mutations land on the core hash-chained audit log
audit-before-commit (a failed audit write commits nothing and
consumes no id); the auditor role is denied every extension
operation; denied attempts are audited ``ext_<action>:denied``;
failed operations consume no id; derived values are derived at
read and never stored.

The fresh negative control is in
:class:`TestCustodyNegativeControl`: the current-holder seam
``LawEnfExtensions._current_holder`` mutated to read the first
transfer instead of the latest must not produce the canonical
holder.
"""

import hashlib
import os
import unittest

from lawenf.audit import AuditLog
from lawenf.errors import (
    AuditWriteError, NotFoundError, PermissionDenied, ValidationError,
)
from lawenf.extensions import LawEnfExtensions

from lawenf_helpers import (
    ADMIN, AUDITOR, MEMBER, OUTSIDER, VIEWER,
    DOC_CONTENT, DOC_SHA256, make_store,
)

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "scratch")

ART_CONTENT = b"device image segment, held in the caller's evidence system"
ART_SHA256 = hashlib.sha256(ART_CONTENT).hexdigest()
REPORT_TEXT = "forensic report body, generated on the fork's platform"
REPORT_SHA256 = hashlib.sha256(REPORT_TEXT.encode("utf-8")).hexdigest()


def _scratch_file(name):
    path = os.path.join(SCRATCH, name)
    if os.path.exists(path):
        os.remove(path)
    return path


class MutantExtensions(LawEnfExtensions):
    """Negative-control mutant: the holder seam reads the FIRST
    transfer instead of the latest."""

    @staticmethod
    def _current_holder(transfers, registered_holder_ref):
        if transfers:
            return transfers[0]["to_holder_ref"]
        return registered_holder_ref


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.matter = make_store()
        self.ext = LawEnfExtensions(self.store)
        self.mid = self.matter["id"]

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def make_document(self):
        return self.store.register_document(
            self.mid, "DOC-1", DOC_SHA256, len(DOC_CONTENT), MEMBER)


class TestUnlockRequests(BatchFixture):
    """Entry: Device unlocking (Cellebrite) -- re-judged to a
    labeled reference implementation: request and reported
    outcome records only; no unlocking capability exists here."""

    def test_request_shape_and_labels(self):
        req = self.ext.record_unlock_request(self.mid, "UNL-1", "DEV-1",
                                             MEMBER)
        self.assertEqual(req["id"], "unl-1")
        self.assertEqual(
            set(req.keys()),
            {"id", "matter_id", "request_ref", "device_ref",
             "reference_stub", "unlocked_here", "capability_held_here",
             "status", "created_by", "created_utc"})
        self.assertIs(req["reference_stub"], True)
        self.assertIs(req["unlocked_here"], False)
        self.assertIs(req["capability_held_here"], False)
        self.assertEqual(req["status"], "recorded_reference_only")

    def test_outcome_shape_labels_and_verbatim(self):
        req = self.ext.record_unlock_request(self.mid, "UNL-1", "DEV-1",
                                             MEMBER)
        out = self.ext.record_unlock_outcome(
            self.mid, req["id"], "reported: unlocked by external lab",
            MEMBER)
        self.assertEqual(out["id"], "uno-1")
        self.assertEqual(
            set(out.keys()),
            {"id", "matter_id", "request_id", "outcome_label",
             "reference_stub", "unlocked_here", "created_by",
             "created_utc"})
        self.assertEqual(out["outcome_label"],
                         "reported: unlocked by external lab")
        self.assertIs(out["reference_stub"], True)
        self.assertIs(out["unlocked_here"], False)

    def test_view_derives_count_and_latest_outcome(self):
        req = self.ext.record_unlock_request(self.mid, "UNL-1", "DEV-1",
                                             MEMBER)
        self.ext.record_unlock_outcome(self.mid, req["id"], "attempt 1",
                                       MEMBER)
        self.ext.record_unlock_outcome(self.mid, req["id"], "attempt 2",
                                       MEMBER)
        view = self.ext.unlock_request_view(self.mid, req["id"], MEMBER)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome"], "attempt 2")
        self.assertIs(view["derived_at_read"], True)
        stored = self.ext.get_unlock_request(self.mid, req["id"], MEMBER)
        self.assertNotIn("outcome_count", stored)
        self.assertNotIn("latest_outcome", stored)

    def test_duplicate_ref_rejected_and_no_id_consumed(self):
        self.ext.record_unlock_request(self.mid, "UNL-1", "DEV-1", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_unlock_request(self.mid, "UNL-1", "DEV-2",
                                           MEMBER)
        req2 = self.ext.record_unlock_request(self.mid, "UNL-2", "DEV-2",
                                              MEMBER)
        self.assertEqual(req2["id"], "unl-2")

    def test_outcome_for_unknown_request_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_unlock_outcome(self.mid, "unl-999", "x", MEMBER)


class TestExtractionRequests(BatchFixture):
    """Entry: Evidence extraction from mobile devices
    (Cellebrite) -- re-judged to a labeled reference
    implementation: request and reported outcome records only;
    nothing is extracted here."""

    def test_request_shape_and_labels(self):
        req = self.ext.record_extraction_request(self.mid, "EXR-1",
                                                 "DEV-1", MEMBER)
        self.assertEqual(req["id"], "exr-1")
        self.assertEqual(
            set(req.keys()),
            {"id", "matter_id", "request_ref", "device_ref",
             "reference_stub", "extracted_here", "capability_held_here",
             "status", "created_by", "created_utc"})
        self.assertIs(req["reference_stub"], True)
        self.assertIs(req["extracted_here"], False)
        self.assertIs(req["capability_held_here"], False)
        self.assertEqual(req["status"], "recorded_reference_only")

    def test_outcome_and_view(self):
        req = self.ext.record_extraction_request(self.mid, "EXR-1",
                                                 "DEV-1", MEMBER)
        out = self.ext.record_extraction_outcome(
            self.mid, req["id"], "reported: extraction complete", MEMBER)
        self.assertEqual(
            set(out.keys()),
            {"id", "matter_id", "request_id", "outcome_label",
             "reference_stub", "extracted_here", "created_by",
             "created_utc"})
        self.assertIs(out["extracted_here"], False)
        view = self.ext.extraction_request_view(self.mid, req["id"],
                                                MEMBER)
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome"],
                         "reported: extraction complete")
        stored = self.ext.get_extraction_request(self.mid, req["id"],
                                                 MEMBER)
        self.assertNotIn("outcome_count", stored)


class TestAnalysisRecords(BatchFixture):
    """Entry: Forensic analysis engines (both siblings) -- built
    as analysis records and reported finding records; no finding
    is computed and nothing is analyzed here."""

    def test_analysis_shape_and_labels(self):
        ana = self.ext.record_analysis(self.mid, "ANA-1", MEMBER,
                                       method_label="reported method A")
        self.assertEqual(ana["id"], "ana-1")
        self.assertEqual(
            set(ana.keys()),
            {"id", "matter_id", "analysis_ref", "method_label",
             "target_document_id", "analyzed_here",
             "findings_computed_here", "status", "created_by",
             "created_utc"})
        self.assertIs(ana["analyzed_here"], False)
        self.assertIs(ana["findings_computed_here"], False)

    def test_analysis_binds_to_core_document(self):
        doc = self.make_document()
        ana = self.ext.record_analysis(self.mid, "ANA-1", MEMBER,
                                       target_document_id=doc["id"])
        self.assertEqual(ana["target_document_id"], doc["id"])
        with self.assertRaises(NotFoundError):
            self.ext.record_analysis(self.mid, "ANA-2", MEMBER,
                                     target_document_id="doc-999")

    def test_finding_shape_labels_and_verbatim(self):
        ana = self.ext.record_analysis(self.mid, "ANA-1", MEMBER)
        fin = self.ext.record_analysis_finding(
            self.mid, ana["id"], "RESULT-REF-1", MEMBER,
            finding_label="reported: artifact class located")
        self.assertEqual(fin["id"], "anf-1")
        self.assertEqual(
            set(fin.keys()),
            {"id", "matter_id", "analysis_id", "result_ref",
             "finding_label", "reported_only", "computed_here",
             "content_held", "created_by", "created_utc"})
        self.assertEqual(fin["finding_label"],
                         "reported: artifact class located")
        self.assertIs(fin["reported_only"], True)
        self.assertIs(fin["computed_here"], False)
        self.assertIs(fin["content_held"], False)

    def test_view_finding_count_derived_not_stored(self):
        ana = self.ext.record_analysis(self.mid, "ANA-1", MEMBER)
        self.ext.record_analysis_finding(self.mid, ana["id"], "R-1",
                                         MEMBER)
        self.ext.record_analysis_finding(self.mid, ana["id"], "R-2",
                                         MEMBER)
        view = self.ext.analysis_view(self.mid, ana["id"], MEMBER)
        self.assertEqual(view["finding_count"], 2)
        self.assertIs(view["derived_at_read"], True)
        stored = self.ext.get_analysis(self.mid, ana["id"], MEMBER)
        self.assertNotIn("finding_count", stored)


class TestIngestPipeline(BatchFixture):
    """Entry: Evidence ingest & processing pipelines (Magnet
    One) -- built as batch, artifact (metadata + SHA-256), and
    processing-report records; nothing is ingested or processed
    here."""

    def test_batch_shape_and_labels(self):
        batch = self.ext.record_ingest_batch(self.mid, "ING-1", MEMBER,
                                             source_label="field kit 7")
        self.assertEqual(batch["id"], "ing-1")
        self.assertEqual(
            set(batch.keys()),
            {"id", "matter_id", "batch_ref", "source_label",
             "ingested_here", "processed_here", "status", "created_by",
             "created_utc"})
        self.assertIs(batch["ingested_here"], False)
        self.assertIs(batch["processed_here"], False)

    def test_artifact_shape_and_digest_discipline(self):
        batch = self.ext.record_ingest_batch(self.mid, "ING-1", MEMBER)
        art = self.ext.record_ingest_artifact(
            self.mid, batch["id"], "ART-A", ART_SHA256, 4096, MEMBER)
        self.assertEqual(art["id"], "ina-1")
        self.assertEqual(
            set(art.keys()),
            {"id", "matter_id", "batch_id", "artifact_ref", "sha256",
             "size_bytes", "content_held", "created_by", "created_utc"})
        self.assertIs(art["content_held"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_ingest_artifact(
                self.mid, batch["id"], "ART-B", "not-a-digest", 1, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_ingest_artifact(
                self.mid, batch["id"], "ART-B", ART_SHA256, 1.5, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_ingest_artifact(
                self.mid, batch["id"], "ART-B", ART_SHA256, True, MEMBER)

    def test_artifact_ref_unique_within_batch_only(self):
        b1 = self.ext.record_ingest_batch(self.mid, "ING-1", MEMBER)
        b2 = self.ext.record_ingest_batch(self.mid, "ING-2", MEMBER)
        self.ext.record_ingest_artifact(self.mid, b1["id"], "ART-A",
                                        ART_SHA256, 1, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_ingest_artifact(self.mid, b1["id"], "ART-A",
                                            ART_SHA256, 1, MEMBER)
        other = self.ext.record_ingest_artifact(self.mid, b2["id"],
                                                "ART-A", ART_SHA256, 1,
                                                MEMBER)
        self.assertEqual(other["batch_id"], b2["id"])

    def test_processing_report_verbatim(self):
        batch = self.ext.record_ingest_batch(self.mid, "ING-1", MEMBER)
        rep = self.ext.record_processing_report(
            self.mid, batch["id"], "decode", "reported: 3 partitions read",
            MEMBER)
        self.assertEqual(
            set(rep.keys()),
            {"id", "matter_id", "batch_id", "stage_label",
             "outcome_label", "reported_only", "processed_here",
             "created_by", "created_utc"})
        self.assertEqual(rep["outcome_label"],
                         "reported: 3 partitions read")
        self.assertIs(rep["reported_only"], True)
        self.assertIs(rep["processed_here"], False)

    def test_batch_view_totals_derived_not_stored(self):
        batch = self.ext.record_ingest_batch(self.mid, "ING-1", MEMBER)
        self.ext.record_ingest_artifact(self.mid, batch["id"], "ART-A",
                                        ART_SHA256, 100, MEMBER)
        self.ext.record_ingest_artifact(self.mid, batch["id"], "ART-B",
                                        ART_SHA256, 250, MEMBER)
        self.ext.record_processing_report(self.mid, batch["id"], "decode",
                                          "done", MEMBER)
        view = self.ext.ingest_batch_view(self.mid, batch["id"], MEMBER)
        self.assertEqual(view["artifact_count"], 2)
        self.assertEqual(view["total_size_bytes"], 350)
        self.assertEqual(view["processing_report_count"], 1)
        self.assertIs(view["derived_at_read"], True)
        stored = self.ext.get_ingest_batch(self.mid, batch["id"], MEMBER)
        self.assertNotIn("artifact_count", stored)
        self.assertNotIn("total_size_bytes", stored)


class TestEvidenceReviews(BatchFixture):
    """Entry: Evidence review (Magnet One) -- built as review
    records over core documents and ingest artifacts; nothing is
    rendered and no content is held."""

    def _ingest_artifact(self):
        batch = self.ext.record_ingest_batch(self.mid, "ING-1", MEMBER)
        return self.ext.record_ingest_artifact(
            self.mid, batch["id"], "ART-A", ART_SHA256, 10, MEMBER)

    def test_review_of_core_document(self):
        doc = self.make_document()
        rev = self.ext.record_evidence_review(
            self.mid, "EVR-1", "document", doc["id"], MEMBER,
            outcome_label="reported: reviewed")
        self.assertEqual(rev["id"], "evr-1")
        self.assertEqual(
            set(rev.keys()),
            {"id", "matter_id", "review_ref", "target_kind",
             "target_id", "outcome_label", "rendered_here",
             "content_held", "status", "created_by", "created_utc"})
        self.assertIs(rev["rendered_here"], False)
        self.assertIs(rev["content_held"], False)

    def test_review_of_ingest_artifact(self):
        art = self._ingest_artifact()
        rev = self.ext.record_evidence_review(
            self.mid, "EVR-1", "ingest_artifact", art["id"], MEMBER)
        self.assertEqual(rev["target_kind"], "ingest_artifact")
        self.assertEqual(rev["target_id"], art["id"])

    def test_bad_target_kind_and_unknown_target_rejected(self):
        doc = self.make_document()
        with self.assertRaises(ValidationError):
            self.ext.record_evidence_review(
                self.mid, "EVR-1", "source", doc["id"], MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_evidence_review(
                self.mid, "EVR-1", "document", "doc-999", MEMBER)


class TestCustodyTransfers(BatchFixture):
    """Entry: Chain-of-custody enforcement over evidence
    (Cellebrite) -- built as artifact registrations and custody
    transfer records; enforcement is NOT claimed (the records
    are the ledger an enforcement system is audited against)."""

    def _register(self, ext=None, ref="ART-1"):
        ext = ext or self.ext
        return ext.register_artifact(self.mid, ref, ART_SHA256, 128,
                                     MEMBER, holder_ref="HOLDER-INTAKE")

    def test_registration_shape_and_labels(self):
        art = self._register()
        self.assertEqual(art["id"], "art-1")
        self.assertEqual(
            set(art.keys()),
            {"id", "matter_id", "artifact_ref", "sha256", "size_bytes",
             "holder_ref", "content_held", "custody_enforced_here",
             "status", "created_by", "created_utc"})
        self.assertIs(art["content_held"], False)
        self.assertIs(art["custody_enforced_here"], False)

    def test_registration_digest_and_count_discipline(self):
        with self.assertRaises(ValidationError):
            self.ext.register_artifact(self.mid, "ART-1", "XYZ", 1,
                                       MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                       -1, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                       2.5, MEMBER)

    def test_transfer_shape_and_labels(self):
        art = self._register()
        tr = self.ext.record_custody_transfer(
            self.mid, art["id"], "HOLDER-INTAKE", "HOLDER-LAB", MEMBER,
            transfer_label="intake to lab")
        self.assertEqual(tr["id"], "cus-1")
        self.assertEqual(
            set(tr.keys()),
            {"id", "matter_id", "artifact_id", "from_holder_ref",
             "to_holder_ref", "transfer_label",
             "custody_enforced_here", "created_by", "created_utc"})
        self.assertIs(tr["custody_enforced_here"], False)

    def test_transfer_for_unknown_artifact_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_custody_transfer(
                self.mid, "art-999", "H-A", "H-B", MEMBER)

    def test_view_no_transfers_registered_holder(self):
        art = self._register()
        view = self.ext.artifact_view(self.mid, art["id"], MEMBER)
        self.assertEqual(view["transfer_count"], 0)
        self.assertEqual(view["current_holder_ref"], "HOLDER-INTAKE")

    def test_view_one_transfer(self):
        art = self._register()
        self.ext.record_custody_transfer(
            self.mid, art["id"], "HOLDER-INTAKE", "HOLDER-LAB", MEMBER)
        view = self.ext.artifact_view(self.mid, art["id"], MEMBER)
        self.assertEqual(view["transfer_count"], 1)
        self.assertEqual(view["current_holder_ref"], "HOLDER-LAB")

    def test_view_two_transfers_latest_holder(self):
        art = self._register()
        self.ext.record_custody_transfer(
            self.mid, art["id"], "HOLDER-INTAKE", "HOLDER-LAB", MEMBER)
        self.ext.record_custody_transfer(
            self.mid, art["id"], "HOLDER-LAB", "HOLDER-VAULT", MEMBER)
        view = self.ext.artifact_view(self.mid, art["id"], MEMBER)
        self.assertEqual(view["transfer_count"], 2)
        self.assertEqual(view["current_holder_ref"], "HOLDER-VAULT")
        self.assertIs(view["derived_at_read"], True)
        stored = self.ext.get_artifact(self.mid, art["id"], MEMBER)
        self.assertEqual(stored["holder_ref"], "HOLDER-INTAKE")
        self.assertNotIn("current_holder_ref", stored)
        self.assertNotIn("transfer_count", stored)

    def test_verify_artifact_matches_and_mismatch(self):
        art = self._register()
        ok = self.ext.verify_artifact(self.mid, art["id"], ART_CONTENT,
                                      MEMBER)
        self.assertEqual(
            set(ok.keys()),
            {"artifact_id", "sha256", "computed_sha256", "matches"})
        self.assertIs(ok["matches"], True)
        bad = self.ext.verify_artifact(self.mid, art["id"],
                                       ART_CONTENT + b"!", MEMBER)
        self.assertIs(bad["matches"], False)
        # Verification stores nothing.
        self.assertEqual(len(self.ext.list_artifacts(self.mid, MEMBER)),
                         1)
        self.assertEqual(len(self.ext.list_custody_transfers(
            self.mid, art["id"], MEMBER)), 0)


class TestCustodyNegativeControl(BatchFixture):
    """Fresh negative control: the current-holder seam.

    Traced claim: **an artifact's current holder is the holder
    named by the LATEST recorded custody transfer** (the
    chain-of-custody entry's only derivation). Each canonical
    case asserts (1) the real implementation's outcome, (2) the
    mutant seam (first transfer instead of latest) would NOT
    produce it, and (3) treating the mutant's outcome as the
    expected outcome fails.
    """

    def _setup_chain(self, ext):
        art = ext.register_artifact(self.mid, "ART-NC", ART_SHA256, 64,
                                    MEMBER, holder_ref="HOLDER-INTAKE")
        ext.record_custody_transfer(self.mid, art["id"], "HOLDER-INTAKE",
                                    "HOLDER-LAB", MEMBER)
        ext.record_custody_transfer(self.mid, art["id"], "HOLDER-LAB",
                                    "HOLDER-VAULT", MEMBER)
        return art

    def test_canonical_current_holder_is_latest(self):
        art = self._setup_chain(self.ext)
        view = self.ext.artifact_view(self.mid, art["id"], MEMBER)
        self.assertEqual(view["current_holder_ref"], "HOLDER-VAULT")
        mutant = MutantExtensions(self.store)
        mart = self._setup_chain(mutant)
        mview = mutant.artifact_view(self.mid, mart["id"], MEMBER)
        self.assertEqual(mview["current_holder_ref"], "HOLDER-LAB")
        with self.assertRaises(AssertionError):
            self.assertEqual(mview["current_holder_ref"], "HOLDER-VAULT")

    def test_no_transfer_holder_is_registered_holder(self):
        art = self.ext.register_artifact(self.mid, "ART-NC", ART_SHA256,
                                         64, MEMBER,
                                         holder_ref="HOLDER-INTAKE")
        view = self.ext.artifact_view(self.mid, art["id"], MEMBER)
        self.assertEqual(view["current_holder_ref"], "HOLDER-INTAKE")
        mutant = MutantExtensions(self.store)
        mart = mutant.register_artifact(self.mid, "ART-NC", ART_SHA256,
                                        64, MEMBER,
                                        holder_ref="HOLDER-INTAKE")
        mview = mutant.artifact_view(self.mid, mart["id"], MEMBER)
        self.assertEqual(mview["current_holder_ref"], "HOLDER-INTAKE")


class TestInformationSharing(BatchFixture):
    """Entry: Information sharing / collaboration over evidence
    (both siblings) -- built as share records bound to core
    documents, artifact registrations, and custody transfers,
    with receipts recorded verbatim; nothing is transmitted
    here."""

    def test_share_of_document_shape_and_labels(self):
        doc = self.make_document()
        shr = self.ext.record_share(self.mid, "SHR-1", "document",
                                    doc["id"], "RECIP-SYS-1", MEMBER)
        self.assertEqual(shr["id"], "shr-1")
        self.assertEqual(
            set(shr.keys()),
            {"id", "matter_id", "share_ref", "target_kind",
             "target_id", "recipient_ref", "access_label",
             "reference_transport", "transmitted_here", "shared_here",
             "content_held", "status", "created_by", "created_utc"})
        self.assertIs(shr["reference_transport"], True)
        self.assertIs(shr["transmitted_here"], False)
        self.assertIs(shr["shared_here"], False)
        self.assertIs(shr["content_held"], False)

    def test_share_leaves_core_document_unchanged(self):
        doc = self.make_document()
        before = self.store.get_document(self.mid, doc["id"], MEMBER)
        self.ext.record_share(self.mid, "SHR-1", "document", doc["id"],
                              "RECIP-SYS-1", MEMBER)
        after = self.store.get_document(self.mid, doc["id"], MEMBER)
        self.assertEqual(before, after)

    def test_share_of_artifact_and_custody_transfer(self):
        art = self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                         10, MEMBER)
        tr = self.ext.record_custody_transfer(
            self.mid, art["id"], "H-A", "H-B", MEMBER)
        s1 = self.ext.record_share(self.mid, "SHR-1", "artifact",
                                   art["id"], "RECIP-SYS-1", MEMBER)
        self.assertEqual(s1["target_kind"], "artifact")
        s2 = self.ext.record_share(self.mid, "SHR-2", "custody_transfer",
                                   tr["id"], "RECIP-SYS-2", MEMBER)
        self.assertEqual(s2["target_kind"], "custody_transfer")

    def test_bad_target_kind_and_unknown_target_rejected(self):
        doc = self.make_document()
        with self.assertRaises(ValidationError):
            self.ext.record_share(self.mid, "SHR-1", "source", doc["id"],
                                  "RECIP-SYS-1", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_share(self.mid, "SHR-1", "artifact",
                                  "art-999", "RECIP-SYS-1", MEMBER)

    def test_receipt_verbatim_and_view_derives(self):
        doc = self.make_document()
        shr = self.ext.record_share(self.mid, "SHR-1", "document",
                                    doc["id"], "RECIP-SYS-1", MEMBER)
        rcp = self.ext.record_share_receipt(
            self.mid, shr["id"], "reported: received and logged", MEMBER)
        self.assertEqual(
            set(rcp.keys()),
            {"id", "matter_id", "share_id", "outcome",
             "reference_transport", "transmitted_here", "created_by",
             "created_utc"})
        self.assertEqual(rcp["outcome"], "reported: received and logged")
        self.assertIs(rcp["reference_transport"], True)
        self.assertIs(rcp["transmitted_here"], False)
        view = self.ext.share_view(self.mid, shr["id"], MEMBER)
        self.assertEqual(view["receipt_count"], 1)
        self.assertEqual(view["latest_outcome"],
                         "reported: received and logged")
        stored = self.ext.get_share(self.mid, shr["id"], MEMBER)
        self.assertNotIn("receipt_count", stored)


class TestForensicReports(BatchFixture):
    """Entry: Forensic reporting (Cellebrite) -- built as report
    registry records (metadata + digest); report figures derive
    at read from the extension registry itself. Nothing is
    generated here."""

    def test_report_shape_and_labels(self):
        rep = self.ext.register_forensic_report(
            self.mid, "FRP-1", MEMBER, report_sha256=REPORT_SHA256)
        self.assertEqual(rep["id"], "frp-1")
        self.assertEqual(
            set(rep.keys()),
            {"id", "matter_id", "report_ref", "report_sha256",
             "generated_here", "content_held", "status", "created_by",
             "created_utc"})
        self.assertIs(rep["generated_here"], False)
        self.assertIs(rep["content_held"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_forensic_report(
                self.mid, "FRP-2", MEMBER, report_sha256="nope")

    def test_view_counts_track_registry_state(self):
        rep = self.ext.register_forensic_report(self.mid, "FRP-1",
                                                MEMBER)
        view = self.ext.forensic_report_view(self.mid, rep["id"],
                                             MEMBER)
        self.assertEqual(view["counts_by_kind"], {
            "artifact_registrations": 0, "custody_transfers": 0,
            "ingest_batches": 0, "ingest_artifacts": 0,
            "analysis_records": 0, "evidence_reviews": 0,
            "share_records": 0})
        art = self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                         10, MEMBER)
        self.ext.record_custody_transfer(self.mid, art["id"], "H-A",
                                         "H-B", MEMBER)
        doc = self.make_document()
        self.ext.record_share(self.mid, "SHR-1", "document", doc["id"],
                              "RECIP-SYS-1", MEMBER)
        view2 = self.ext.forensic_report_view(self.mid, rep["id"],
                                              MEMBER)
        self.assertEqual(view2["counts_by_kind"]["artifact_registrations"],
                         1)
        self.assertEqual(view2["counts_by_kind"]["custody_transfers"], 1)
        self.assertEqual(view2["counts_by_kind"]["share_records"], 1)
        self.assertIs(view2["derived_at_read"], True)
        stored = self.ext.get_forensic_report(self.mid, rep["id"],
                                              MEMBER)
        self.assertNotIn("counts_by_kind", stored)


class TestPrivacyShapePins(BatchFixture):
    """The hard privacy rule, by signature: no extension method
    can accept evidence content, a finding's or report's text, a
    credential or bypass value, or a person's identifier --
    passing any such keyword raises TypeError before anything
    is recorded."""

    def test_content_shaped_kwargs_raise_type_error(self):
        doc = self.make_document()
        batch = self.ext.record_ingest_batch(self.mid, "ING-1", MEMBER)
        attempts = [
            lambda: self.ext.record_unlock_request(
                self.mid, "UNL-1", "DEV-1", MEMBER, bypass_code="000000"),
            lambda: self.ext.record_unlock_request(
                self.mid, "UNL-1", "DEV-1", MEMBER, credential="x"),
            lambda: self.ext.record_extraction_request(
                self.mid, "EXR-1", "DEV-1", MEMBER, device_data=b"x"),
            lambda: self.ext.record_analysis_finding(
                self.mid, "ana-1", "R-1", MEMBER, finding_text="text"),
            lambda: self.ext.record_ingest_artifact(
                self.mid, batch["id"], "ART-A", ART_SHA256, 1, MEMBER,
                content=b"bytes"),
            lambda: self.ext.register_artifact(
                self.mid, "ART-1", ART_SHA256, 1, MEMBER, content=b"b"),
            lambda: self.ext.record_evidence_review(
                self.mid, "EVR-1", "document", doc["id"], MEMBER,
                note_text="a note"),
            lambda: self.ext.record_share(
                self.mid, "SHR-1", "document", doc["id"], "RECIP-1",
                MEMBER, message_text="hello"),
            lambda: self.ext.record_share(
                self.mid, "SHR-1", "document", doc["id"], "RECIP-1",
                MEMBER, payload=b"bytes"),
            lambda: self.ext.register_forensic_report(
                self.mid, "FRP-1", MEMBER, report_text="body"),
            lambda: self.ext.record_custody_transfer(
                self.mid, "art-1", "H-A", "H-B", MEMBER, note_text="n"),
            lambda: self.ext.record_unlock_outcome(
                self.mid, "unl-1", "ok", MEMBER, result_text="r"),
            lambda: self.ext.record_processing_report(
                self.mid, batch["id"], "decode", "done", MEMBER,
                log_text="log"),
        ]
        for attempt in attempts:
            with self.assertRaises(TypeError):
                attempt()
        # Nothing was recorded by any rejected attempt.
        self.assertEqual(self.ext.list_unlock_requests(self.mid, MEMBER),
                         [])
        self.assertEqual(self.ext.list_shares(self.mid, actor=MEMBER), [])
        self.assertEqual(self.ext.list_forensic_reports(self.mid, MEMBER),
                         [])
        self.assertEqual(self.ext.list_artifacts(self.mid, MEMBER), [])

    def test_no_score_shaped_key_anywhere(self):
        art = self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                         10, MEMBER, holder_ref="H-A")
        self.ext.record_custody_transfer(self.mid, art["id"], "H-A",
                                         "H-B", MEMBER)
        records = []
        records += self.ext.list_artifacts(self.mid, MEMBER)
        records += self.ext.list_custody_transfers(self.mid, actor=MEMBER)
        records.append(self.ext.artifact_view(self.mid, art["id"],
                                              MEMBER))
        rep = self.ext.register_forensic_report(self.mid, "FRP-1",
                                                MEMBER)
        records.append(self.ext.forensic_report_view(self.mid,
                                                     rep["id"], MEMBER))

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield key
                    yield from walk(item)
            elif isinstance(value, list):
                for item in value:
                    yield from walk(item)

        for record in records:
            for key in walk(record):
                self.assertNotIn("score", key)
                self.assertNotIn("rating", key)
                self.assertNotIn("grade", key)


class TestAccessAndBoundaries(BatchFixture):
    """High apparatus on the new surface: the auditor role is
    denied every extension operation; membership and lifecycle
    boundaries hold; mutations land on the core hash-chained
    audit log."""

    def test_auditor_denied_every_extension_operation(self):
        doc = self.make_document()
        art = self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                         10, MEMBER)
        attempts = [
            lambda: self.ext.record_unlock_request(
                self.mid, "UNL-1", "DEV-1", AUDITOR),
            lambda: self.ext.record_extraction_request(
                self.mid, "EXR-1", "DEV-1", AUDITOR),
            lambda: self.ext.record_analysis(self.mid, "ANA-1", AUDITOR),
            lambda: self.ext.record_ingest_batch(self.mid, "ING-1",
                                                 AUDITOR),
            lambda: self.ext.record_evidence_review(
                self.mid, "EVR-1", "document", doc["id"], AUDITOR),
            lambda: self.ext.register_artifact(
                self.mid, "ART-2", ART_SHA256, 1, AUDITOR),
            lambda: self.ext.record_custody_transfer(
                self.mid, art["id"], "H-A", "H-B", AUDITOR),
            lambda: self.ext.record_share(
                self.mid, "SHR-1", "document", doc["id"], "R-1", AUDITOR),
            lambda: self.ext.register_forensic_report(
                self.mid, "FRP-1", AUDITOR),
            lambda: self.ext.get_artifact(self.mid, art["id"], AUDITOR),
            lambda: self.ext.list_artifacts(self.mid, AUDITOR),
            lambda: self.ext.artifact_view(self.mid, art["id"], AUDITOR),
            lambda: self.ext.verify_artifact(
                self.mid, art["id"], ART_CONTENT, AUDITOR),
        ]
        for attempt in attempts:
            with self.assertRaises(PermissionDenied):
                attempt()
        denied = [a for a in self.audit_actions()
                  if a.endswith(":denied")]
        self.assertTrue(denied)
        self.assertEqual(self.audit.verify_chain(), (True, None))

    def test_viewer_reads_but_cannot_write(self):
        art = self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                         10, MEMBER)
        got = self.ext.get_artifact(self.mid, art["id"], VIEWER)
        self.assertEqual(got["id"], art["id"])
        view = self.ext.artifact_view(self.mid, art["id"], VIEWER)
        self.assertEqual(view["transfer_count"], 0)
        with self.assertRaises(PermissionDenied):
            self.ext.register_artifact(self.mid, "ART-2", ART_SHA256, 1,
                                       VIEWER)
        with self.assertRaises(PermissionDenied):
            self.ext.record_custody_transfer(self.mid, art["id"], "H-A",
                                             "H-B", VIEWER)

    def test_outsider_denied_by_membership_and_audited(self):
        art = self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                         10, MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.get_artifact(self.mid, art["id"], OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.register_artifact(self.mid, "ART-2", ART_SHA256, 1,
                                       OUTSIDER)
        self.assertIn("ext_artifact_read:denied", self.audit_actions())
        self.assertIn("ext_artifact_register:denied", self.audit_actions())
        self.assertEqual(self.audit.verify_chain(), (True, None))

    def test_closed_matter_rejects_extension_writes(self):
        self.store.close_matter(self.mid, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                       1, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_analysis(self.mid, "ANA-1", MEMBER)

    def test_cross_matter_isolation(self):
        other = self.store.create_matter("MATTER-REF-002", MEMBER)
        art = self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                         10, MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.get_artifact(other["id"], art["id"], MEMBER)
        self.assertEqual(self.ext.list_artifacts(other["id"], MEMBER),
                         [])

    def test_extension_mutations_on_core_audit_chain(self):
        self.ext.register_artifact(self.mid, "ART-1", ART_SHA256, 10,
                                   MEMBER)
        self.ext.record_analysis(self.mid, "ANA-1", MEMBER)
        actions = self.audit_actions()
        self.assertIn("ext_artifact_register", actions)
        self.assertIn("ext_analysis_record", actions)
        self.assertEqual(self.audit.verify_chain(), (True, None))

    def test_admin_can_write(self):
        art = self.ext.register_artifact(self.mid, "ART-1", ART_SHA256,
                                         10, ADMIN)
        self.assertEqual(art["created_by"], "alice")


class TestFailClosedExtension(unittest.TestCase):
    """AU-5 on the new surface: extension mutations audit BEFORE
    commit, so a failed audit write commits nothing and consumes
    no id, and the hash chain still verifies."""

    def _broken_path(self, good_path):
        # A path under an existing *file*: opening it raises
        # NotADirectoryError, an OSError -- the write cannot succeed.
        return os.path.join(good_path, "child.jsonl")

    def test_extension_create_rolls_back_on_audit_failure(self):
        path = _scratch_file("audit-ext-failclosed-test.jsonl")
        audit = AuditLog(path=path)
        store, audit, matter = make_store(audit=audit)
        ext = LawEnfExtensions(store)
        audit.path = self._broken_path(path)
        with self.assertRaises(AuditWriteError):
            ext.register_artifact(matter["id"], "ART-1", ART_SHA256,
                                  128, MEMBER)
        audit.path = path
        # Nothing was committed and no id was consumed.
        self.assertEqual(ext.list_artifacts(matter["id"], MEMBER), [])
        art = ext.register_artifact(matter["id"], "ART-1", ART_SHA256,
                                    128, MEMBER)
        self.assertEqual(art["id"], "art-1")
        self.assertEqual(audit.verify_chain(), (True, None))
