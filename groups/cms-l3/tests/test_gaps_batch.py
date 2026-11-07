"""Final GAPS batch tests — Singleton 39 (CMS L3-adjacent).

Traces to: the five open Extended entries of the repo-root
GAPS.md section "Singleton 39 — CMS L3-adjacent (1 fork)"
(idx 394–398) and the batch pattern in gaps-batch/DECISION.md.
Per-entry dispositions (full record in ../BATCH.md):

- idx 394–396 (learned ML/AI classification / extraction /
  enrichment engines) — labeled reference implementations,
  re-judged from the drafted build-extension triage: job records
  plus outcome records holding the external engine's reports
  verbatim, ``reference_stub: True`` throughout.
- idx 397 (physical-content intake & digitization pipeline) —
  built: intake records, stage events with the current stage
  derived at read, outcome records binding core asset
  registrations.
- idx 398 (content services platform runtime) — labeled
  reference record (PLATFORM-LAYER.md decision 6).

The High apparatus is pinned against the extension surface:
extension writes are audited into the core hash-chained log and
fail closed on an audit write failure (AU-5/AU-9); the auditor
role is denied every extension read and write while its core
audit duty works (AC-5). The batch's fresh negative control is
the intake current-stage seam (TestIntakeStageNegativeControl).
"""

import os
import shutil
import tempfile
import unittest

import cms_helpers as h
from cms.audit import AuditLog
from cms.errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from cms.extensions import CmsExtensions

SHA_A = "a" * 64
SHA_B = "b" * 64


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class BatchBase(unittest.TestCase):
    def setUp(self):
        self.store, self.site, self.section = h.make_store()
        self.ext = CmsExtensions(self.store)
        self.item = h.make_item(self.store, self.site)

    def make_asset(self, filename="scan.pdf"):
        return self.store.register_asset(
            h.EDITOR, self.site["id"], filename, "document", 1024,
            content_sha256=SHA_B)


class TestClassificationReference(BatchBase):
    """idx 394 — learned ML/AI classification engine (reference)."""

    def test_job_record_shape_and_labels(self):
        job = self.ext.register_classification_job(
            h.PUBLISHER, self.item["id"], target_kind="item",
            taxonomy_ref="taxonomy-2026", content_digest=SHA_A)
        self.assertEqual(job["id"], "clsjob-1")
        self.assertEqual(job["target_ref"], self.item["id"])
        self.assertEqual(job["target_kind"], "item")
        self.assertEqual(job["taxonomy_ref"], "taxonomy-2026")
        self.assertEqual(job["content_digest"], SHA_A)
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["classified_here"], False)
        self.assertEqual(job["state"], "recorded_reference_only")
        self.assertEqual(job["created_by"], "bob")

    def test_job_binds_asset_and_external_targets(self):
        asset = self.make_asset()
        job = self.ext.register_classification_job(
            h.PUBLISHER, asset["id"], target_kind="asset")
        self.assertEqual(job["target_ref"], asset["id"])
        opaque = self.ext.register_classification_job(
            h.PUBLISHER, "offsite-box-77", target_kind="external")
        self.assertEqual(opaque["id"], "clsjob-2")

    def test_unknown_core_target_rejected_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_classification_job(
                h.PUBLISHER, "ci-999", target_kind="item")
        job = self.ext.register_classification_job(
            h.PUBLISHER, "opaque-1", target_kind="external")
        self.assertEqual(job["id"], "clsjob-1")

    def test_bad_digest_and_bad_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_classification_job(
                h.PUBLISHER, "opaque-1", content_digest="not-a-digest")
        with self.assertRaises(ValidationError):
            self.ext.register_classification_job(
                h.PUBLISHER, "opaque-1", target_kind="carrier_pigeon")
        self.assertEqual(self.ext.list_classification_jobs(), [])

    def test_no_content_parameter_exists(self):
        with self.assertRaises(TypeError):
            self.ext.register_classification_job(
                h.PUBLISHER, "opaque-1", content="the document body")

    def test_outcome_verbatim_and_view_derivation(self):
        job = self.ext.register_classification_job(
            h.PUBLISHER, self.item["id"], target_kind="item")
        out = self.ext.record_classification_outcome(
            h.PUBLISHER, job["id"], ["records", "tax"],
            confidence_label="high")
        self.assertEqual(out["labels"], ["records", "tax"])
        self.assertEqual(out["confidence_label"], "high")
        self.assertEqual(out["outcome_basis"], "engine_reported")
        self.assertIs(out["reference_stub"], True)
        self.assertIs(out["classified_here"], False)
        self.ext.record_classification_outcome(
            h.PUBLISHER, job["id"], ["records", "retention"])
        view = self.ext.get_classification_job(job["id"], actor=h.VIEWER)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_labels"], ["records", "retention"])
        outcomes = self.ext.list_classification_outcomes(
            job_id=job["id"], actor=h.VIEWER)
        self.assertEqual([o["id"] for o in outcomes], ["clsout-1", "clsout-2"])

    def test_outcome_for_unknown_job_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_classification_outcome(
                h.PUBLISHER, "clsjob-99", ["records"])
        with self.assertRaises(ValidationError):
            job = self.ext.register_classification_job(
                h.PUBLISHER, "opaque-1")
            self.ext.record_classification_outcome(
                h.PUBLISHER, job["id"], [])
        with self.assertRaises(ValidationError):
            self.ext.record_classification_outcome(
                h.PUBLISHER, job["id"], ["records"], confidence_label=9)

    def test_classification_leaves_core_item_untouched(self):
        before = self.store.get_item(self.item["id"], actor=None)
        job = self.ext.register_classification_job(
            h.PUBLISHER, self.item["id"], target_kind="item")
        self.ext.record_classification_outcome(
            h.PUBLISHER, job["id"], ["records"])
        after = self.store.get_item(self.item["id"], actor=None)
        self.assertEqual(before, after)


class TestExtractionReference(BatchBase):
    """idx 395 — learned ML/AI extraction engine (reference)."""

    def test_job_and_outcome_verbatim(self):
        asset = self.make_asset()
        job = self.ext.register_extraction_job(
            h.PUBLISHER, asset["id"], source_kind="asset",
            field_labels=["invoice_total", "vendor_name"],
            content_digest=SHA_B)
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["extracted_here"], False)
        self.assertEqual(job["state"], "recorded_reference_only")
        out = self.ext.record_extraction_outcome(
            h.PUBLISHER, job["id"],
            [{"field_label": "invoice_total", "value": "1200.00"},
             {"field_label": "vendor_name", "value": "Acme"}])
        self.assertEqual(
            out["fields"],
            [{"field_label": "invoice_total", "value": "1200.00"},
             {"field_label": "vendor_name", "value": "Acme"}])
        self.assertEqual(out["outcome_basis"], "engine_reported")
        self.assertIs(out["extracted_here"], False)

    def test_fields_shape_is_exact(self):
        job = self.ext.register_extraction_job(h.PUBLISHER, "opaque-1")
        with self.assertRaises(ValidationError):
            self.ext.record_extraction_outcome(
                h.PUBLISHER, job["id"],
                [{"field_label": "x", "value": "1", "extra": "no"}])
        with self.assertRaises(ValidationError):
            self.ext.record_extraction_outcome(
                h.PUBLISHER, job["id"], [{"field_label": "x"}])
        with self.assertRaises(ValidationError):
            self.ext.record_extraction_outcome(
                h.PUBLISHER, job["id"], [])
        self.assertEqual(self.ext.list_extraction_outcomes(), [])

    def test_unknown_source_rejected_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_extraction_job(
                h.PUBLISHER, "asset-999", source_kind="asset")
        job = self.ext.register_extraction_job(h.PUBLISHER, "opaque-1")
        self.assertEqual(job["id"], "extjob-1")

    def test_outcome_fields_are_copies(self):
        job = self.ext.register_extraction_job(h.PUBLISHER, "opaque-1")
        fields = [{"field_label": "total", "value": "5"}]
        self.ext.record_extraction_outcome(h.PUBLISHER, job["id"], fields)
        fields[0]["value"] = "tampered"
        stored = self.ext.list_extraction_outcomes()[0]
        self.assertEqual(stored["fields"][0]["value"], "5")


class TestEnrichmentReference(BatchBase):
    """idx 396 — learned ML/AI enrichment engine (reference)."""

    def test_job_binds_core_item(self):
        job = self.ext.register_enrichment_job(h.PUBLISHER, self.item["id"])
        self.assertEqual(job["item_id"], self.item["id"])
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["derived_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.register_enrichment_job(h.PUBLISHER, "ci-999")

    def test_outcome_recorded_not_applied(self):
        before = self.store.get_item(self.item["id"], actor=None)
        job = self.ext.register_enrichment_job(h.PUBLISHER, self.item["id"])
        out = self.ext.record_enrichment_outcome(
            h.PUBLISHER, job["id"],
            {"doctype": "memo", "retention": "7y"})
        self.assertEqual(out["metadata"], {"doctype": "memo",
                                           "retention": "7y"})
        self.assertEqual(out["outcome_basis"], "engine_reported")
        self.assertIs(out["derived_here"], False)
        self.assertIs(out["applied_here"], False)
        after = self.store.get_item(self.item["id"], actor=None)
        self.assertEqual(before["metadata"], after["metadata"])
        self.assertEqual(before["revision"], after["revision"])
        self.assertEqual(before, after)

    def test_outcome_metadata_must_be_strings(self):
        job = self.ext.register_enrichment_job(h.PUBLISHER, self.item["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_enrichment_outcome(
                h.PUBLISHER, job["id"], {"count": 3})
        with self.assertRaises(ValidationError):
            self.ext.record_enrichment_outcome(h.PUBLISHER, job["id"], {})
        self.assertEqual(self.ext.list_enrichment_outcomes(), [])


class TestDigitizationPipeline(BatchBase):
    """idx 397 — physical-content intake & digitization (built)."""

    def test_intake_record_exact_key_set(self):
        intake = self.ext.register_physical_intake(
            h.EDITOR, "warehouse-box-114", "paper file",
            pages_reported=320, condition_label="fragile")
        self.assertEqual(
            set(intake),
            {"id", "source_ref", "form_label", "pages_reported",
             "condition_label", "steps", "digitization",
             "scanned_here", "converted_here", "content_held",
             "created_by", "created_utc"})
        self.assertIs(intake["scanned_here"], False)
        self.assertIs(intake["converted_here"], False)
        self.assertIs(intake["content_held"], False)
        self.assertEqual(intake["pages_reported"], 320)
        self.assertEqual(intake["steps"], [])
        self.assertIsNone(intake["digitization"])

    def test_pages_must_be_a_count(self):
        with self.assertRaises(ValidationError):
            self.ext.register_physical_intake(
                h.EDITOR, "box-1", "paper file", pages_reported=3.5)
        with self.assertRaises(ValidationError):
            self.ext.register_physical_intake(
                h.EDITOR, "box-1", "paper file", pages_reported=True)
        intake = self.ext.register_physical_intake(
            h.EDITOR, "box-1", "paper file")
        self.assertEqual(intake["id"], "int-1")
        self.assertIsNone(intake["pages_reported"])

    def test_stage_derived_at_read_never_stored(self):
        intake = self.ext.register_physical_intake(
            h.EDITOR, "box-2", "microfilm")
        view = self.ext.get_intake(intake["id"], actor=h.VIEWER)
        self.assertEqual(view["current_stage"], "received")
        self.ext.record_digitization_step(h.EDITOR, intake["id"], "in_transit")
        self.ext.record_digitization_step(
            h.EDITOR, intake["id"], "prep_complete")
        view = self.ext.get_intake(intake["id"], actor=h.VIEWER)
        self.assertEqual(view["current_stage"], "prep_complete")
        self.assertEqual(view["step_count"], 2)
        stored = self.ext._intakes[intake["id"]]
        self.assertNotIn("current_stage", stored)
        self.assertNotIn("stage", stored)

    def test_outcome_binds_core_asset(self):
        intake = self.ext.register_physical_intake(
            h.EDITOR, "box-3", "paper file")
        asset = self.make_asset()
        view = self.ext.record_digitization_outcome(
            h.EDITOR, intake["id"], asset["id"], "digitized")
        self.assertEqual(view["digitization"]["asset_id"], asset["id"])
        self.assertIs(view["digitization"]["converted_here"], False)
        self.assertIs(view["digitized"], True)
        self.assertEqual(view["current_stage"], "digitized")
        with self.assertRaises(ValidationError):
            self.ext.record_digitization_outcome(
                h.EDITOR, intake["id"], asset["id"], "digitized_again")

    def test_outcome_unknown_asset_rejected(self):
        intake = self.ext.register_physical_intake(
            h.EDITOR, "box-4", "paper file")
        with self.assertRaises(NotFoundError):
            self.ext.record_digitization_outcome(
                h.EDITOR, intake["id"], "asset-999", "digitized")
        view = self.ext.get_intake(intake["id"], actor=h.VIEWER)
        self.assertIs(view["digitized"], False)
        self.assertEqual(view["current_stage"], "received")

    def test_summary_counts_derived(self):
        first = self.ext.register_physical_intake(
            h.EDITOR, "box-5", "paper file")
        second = self.ext.register_physical_intake(
            h.EDITOR, "box-6", "microfilm")
        self.ext.record_digitization_step(h.EDITOR, first["id"], "in_transit")
        asset = self.make_asset()
        self.ext.record_digitization_outcome(
            h.EDITOR, second["id"], asset["id"], "digitized")
        summary = self.ext.digitization_summary(actor=h.ADMIN)
        self.assertEqual(
            summary,
            {"intakes": 2, "digitized": 1,
             "by_stage": {"in_transit": 1, "digitized": 1}})


class TestPlatformRuntimeReference(BatchBase):
    """idx 398 — content services platform runtime (reference)."""

    def test_runtime_reference_record(self):
        ref = self.ext.register_platform_runtime_reference(
            h.PUBLISHER, "InSight platform runtime",
            "FedRAMP High SaaS, Government Community Cloud")
        self.assertEqual(ref["family"], "platform_runtime")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["hosted_here"], False)
        self.assertIs(ref["delivered_here"], False)
        self.assertIs(ref["reference_transport"], True)
        self.assertEqual(ref["substrate_label"],
                         "FedRAMP High SaaS, Government Community Cloud")
        listed = self.ext.list_references(
            family="platform_runtime", actor=h.VIEWER)
        self.assertEqual([r["id"] for r in listed], ["ref-1"])


class TestHighApparatus(BatchBase):
    """High apparatus binds the extension: AC-5, AU-5, AU-9."""

    def test_auditor_denied_extension_write_and_read(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_classification_job(h.AUDITOR, "opaque-1")
        job = self.ext.register_classification_job(
            h.PUBLISHER, "opaque-1")
        with self.assertRaises(PermissionDenied):
            self.ext.get_classification_job(job["id"], actor=h.AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.register_physical_intake(h.AUDITOR, "box-9", "paper")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_classification_job_register:denied", actions)
        self.assertIn("ext_classification_read:denied", actions)
        self.assertIn("ext_intake_register:denied", actions)

    def test_auditor_core_audit_duty_still_works(self):
        self.ext.register_classification_job(h.PUBLISHER, "opaque-1")
        self.ext.register_physical_intake(h.EDITOR, "box-10", "paper")
        ok, first_bad = self.store.audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(first_bad)
        entries = self.store.audit.query(actor="bob")
        self.assertTrue(
            any(e["action"] == "ext_classification_job_register"
                for e in entries))

    def test_viewer_cannot_write(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_classification_job(h.VIEWER, "opaque-1")
        with self.assertRaises(PermissionDenied):
            self.ext.register_physical_intake(h.VIEWER, "box-11", "paper")
        self.assertEqual(self.ext.list_classification_jobs(), [])
        self.assertEqual(self.ext.list_intakes(), [])

    def test_no_score_shaped_keys_anywhere(self):
        job = self.ext.register_classification_job(
            h.PUBLISHER, self.item["id"], target_kind="item")
        self.ext.record_classification_outcome(
            h.PUBLISHER, job["id"], ["records"], confidence_label="high")
        ejob = self.ext.register_enrichment_job(h.PUBLISHER, self.item["id"])
        self.ext.record_enrichment_outcome(
            h.PUBLISHER, ejob["id"], {"doctype": "memo"})
        surfaces = [
            self.ext.list_classification_jobs(),
            self.ext.list_classification_outcomes(),
            self.ext.list_enrichment_jobs(),
            self.ext.list_enrichment_outcomes(),
            self.ext.list_intakes(),
            self.ext.list_references(),
        ]
        for surface in surfaces:
            for key in _all_keys(surface):
                self.assertNotIn("score", key)

    def test_fail_closed_on_audit_write_failure(self):
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "audit.jsonl")
            audit = AuditLog(path)
            store, site, _section = h.make_store(audit=audit)
            ext = CmsExtensions(store)
            first = ext.register_classification_job(
                h.PUBLISHER, "opaque-1")
            self.assertEqual(first["id"], "clsjob-1")
            # Break the JSONL path mid-flight (the AU-5 technique).
            os.remove(path)
            os.mkdir(path)
            with self.assertRaises(AuditWriteError):
                ext.register_classification_job(h.PUBLISHER, "opaque-2")
            self.assertEqual(len(ext.list_classification_jobs()), 1)
            os.rmdir(path)
            second = ext.register_classification_job(
                h.PUBLISHER, "opaque-2")
            self.assertEqual(second["id"], "clsjob-2")
            ok, first_bad = audit.verify_chain()
            self.assertTrue(ok)
            self.assertIsNone(first_bad)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class EarliestStageExtensions(CmsExtensions):
    """Mutant: the current stage reads the EARLIEST stage event.

    Used only by TestIntakeStageNegativeControl: if the batch's
    assertions about the derived current stage still passed
    against this mutant, the derivation seam would not be
    load-bearing.
    """

    @staticmethod
    def _current_intake_stage(steps):
        if not steps:
            return "received"
        return steps[0]["label"]


class TestIntakeStageNegativeControl(BatchBase):
    """Fresh negative control: the intake current-stage seam.

    A case recorded with stage events in order must read its
    current stage from the LATEST event (canonical). The
    earliest-reading mutant must NOT produce that reading, and
    treating the mutant's reading as the expectation must fail.
    """

    def _drive_steps(self, ext):
        intake = ext.register_physical_intake(
            h.EDITOR, "box-nc", "paper file")
        ext.record_digitization_step(h.EDITOR, intake["id"], "in_transit")
        ext.record_digitization_step(h.EDITOR, intake["id"], "prep_complete")
        ext.record_digitization_step(
            h.EDITOR, intake["id"], "quality_checked")
        return intake

    def test_canonical_current_stage_is_latest(self):
        intake = self._drive_steps(self.ext)
        view = self.ext.get_intake(intake["id"], actor=h.VIEWER)
        self.assertEqual(view["current_stage"], "quality_checked")

    def test_mutant_reads_earliest_not_latest(self):
        mutant = EarliestStageExtensions(self.store)
        intake = self._drive_steps(mutant)
        view = mutant.get_intake(intake["id"], actor=h.VIEWER)
        self.assertEqual(view["current_stage"], "in_transit")
        self.assertNotEqual(view["current_stage"], "quality_checked")

    def test_mutant_as_expectation_fails(self):
        mutant = EarliestStageExtensions(self.store)
        intake = self._drive_steps(mutant)
        view = mutant.get_intake(intake["id"], actor=h.VIEWER)
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_stage"], "quality_checked")


if __name__ == "__main__":
    unittest.main()
