"""Final GAPS batch, second unit — CMS L2 remainder addition.

Traces to: the one open entry of the GAPS.md section
"Remainder Addition — CMS L2 (+1 fork)" (idx 660) — the ML/AI
content classification, extraction & enrichment engine registered
from the addition fork Iron Mountain InSight's described headline
function (``../ADDENDUM.md`` §5) — as closed by
``../src/cms/extensions_addition.py`` under the ratified batch
triage (``../../gaps-batch/DECISION.md``), re-judged from the
drafted build-extension disposition to a labeled reference
implementation (grounds in ``../BATCH-ADDITION.md``; the sibling
CMS L3-adjacent build adjudicated the same form for this fork
family's three engine entries).

Every record on the surface is pinned as a labeled reference
record (``reference_stub: True`` plus its family's not-here flag
False); outcomes hold the external engine's reports verbatim;
no content is held anywhere (recursive key/value scans); job
views derive outcome counts and the latest reported outcome at
read via the ``_latest_outcome`` seam. The unit's fresh negative
control is that seam (last test class).
"""

import unittest

from cms.audit import AuditLog
from cms.errors import NotFoundError, PermissionDenied, ValidationError
from cms.extensions_addition import CmsExtensionsAddition

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER
from cms_helpers import make_item, make_store

DIGEST = "a" * 64

FORBIDDEN_KEYS = {
    "content", "body", "payload", "document", "score",
    "confidence_score", "rating", "grade", "percent", "rank",
}


def scan_no_content_no_score(node, path="root"):
    """Recursively assert no content/score key and no float value."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, (
                "forbidden key %r at %s" % (key, path))
            scan_no_content_no_score(value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for i, value in enumerate(node):
            scan_no_content_no_score(value, "%s[%d]" % (path, i))
    else:
        assert not isinstance(node, float), (
            "float value at %s: %r" % (path, node))


class AdditionFixture(unittest.TestCase):
    """Fresh store + canonical site/section + addition register."""

    def setUp(self):
        self.audit = AuditLog()
        self.store, self.site, self.section = make_store(audit=self.audit)
        self.ext = CmsExtensionsAddition(self.store)

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def make_asset(self):
        return self.store.register_asset(
            EDITOR, self.site["id"], "scan.pdf", "document", 1024,
            content_sha256=DIGEST)


class TestClassificationReference(AdditionFixture):
    """Classification (reference): jobs by reference, outcomes verbatim."""

    def test_job_record_shape_and_labels(self):
        job = self.ext.register_classification_job(
            PUBLISHER, "ext-doc-9", taxonomy_ref="tax-1",
            content_digest=DIGEST.upper())
        self.assertEqual(job["id"], "clsjob-1")
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["classified_here"], False)
        self.assertEqual(job["state"], "recorded_reference_only")
        self.assertEqual(job["content_digest"], DIGEST)
        self.assertEqual(
            set(job.keys()),
            {"id", "target_ref", "target_kind", "taxonomy_ref",
             "content_digest", "reference_stub", "classified_here",
             "state", "created_by", "created_utc"})

    def test_job_binds_item_asset_and_external_targets(self):
        item = make_item(self.store, self.site)
        asset = self.make_asset()
        j1 = self.ext.register_classification_job(
            PUBLISHER, item["id"], target_kind="item")
        j2 = self.ext.register_classification_job(
            PUBLISHER, asset["id"], target_kind="asset")
        j3 = self.ext.register_classification_job(
            PUBLISHER, "opaque-elsewhere")
        self.assertEqual([j1["id"], j2["id"], j3["id"]],
                         ["clsjob-1", "clsjob-2", "clsjob-3"])

    def test_unknown_core_target_rejected_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_classification_job(
                PUBLISHER, "ci-99", target_kind="item")
        with self.assertRaises(NotFoundError):
            self.ext.register_classification_job(
                PUBLISHER, "asset-99", target_kind="asset")
        job = self.ext.register_classification_job(PUBLISHER, "ext-1")
        self.assertEqual(job["id"], "clsjob-1")

    def test_bad_digest_and_bad_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_classification_job(
                PUBLISHER, "ext-1", content_digest="not-a-digest")
        with self.assertRaises(ValidationError):
            self.ext.register_classification_job(
                PUBLISHER, "ext-1", target_kind="folder")
        with self.assertRaises(ValidationError):
            self.ext.record_classification_outcome(
                PUBLISHER, "clsjob-1", ["x"], confidence_label=0.9)

    def test_no_content_parameter_exists(self):
        with self.assertRaises(TypeError):
            self.ext.register_classification_job(
                PUBLISHER, "ext-1", content="the document body")
        with self.assertRaises(TypeError):
            self.ext.register_extraction_job(
                PUBLISHER, "ext-1", body="the document body")
        with self.assertRaises(TypeError):
            self.ext.record_enrichment_outcome(
                PUBLISHER, "enrjob-1", {"k": "v"}, content="x")

    def test_outcome_verbatim_and_view_derivation(self):
        job = self.ext.register_classification_job(PUBLISHER, "ext-1")
        first = self.ext.record_classification_outcome(
            PUBLISHER, job["id"], ["invoice"], confidence_label="low")
        self.assertEqual(first["id"], "clsout-1")
        self.assertIs(first["reference_stub"], True)
        self.assertIs(first["classified_here"], False)
        self.assertEqual(first["outcome_basis"], "engine_reported")
        self.assertEqual(first["labels"], ["invoice"])
        self.ext.record_classification_outcome(
            PUBLISHER, job["id"], ["invoice", "finance"],
            confidence_label="high")
        view = self.ext.get_classification_job(job["id"], actor=VIEWER)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_labels"], ["invoice", "finance"])
        stored = self.ext._classification_jobs[job["id"]]
        self.assertNotIn("latest_labels", stored)
        self.assertNotIn("outcome_count", stored)

    def test_outcome_for_unknown_job_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_classification_outcome(
                PUBLISHER, "clsjob-99", ["x"])

    def test_classification_leaves_core_item_untouched(self):
        item = make_item(self.store, self.site)
        before = self.store.get_item(item["id"], actor=ADMIN)
        job = self.ext.register_classification_job(
            PUBLISHER, item["id"], target_kind="item")
        self.ext.record_classification_outcome(
            PUBLISHER, job["id"], ["finance"])
        after = self.store.get_item(item["id"], actor=ADMIN)
        self.assertEqual(before, after)


class TestExtractionReference(AdditionFixture):
    """Extraction (reference): jobs by reference, field pairs verbatim."""

    def test_job_and_outcome_verbatim(self):
        job = self.ext.register_extraction_job(
            PUBLISHER, "ext-7", field_labels=["total", "date"])
        self.assertEqual(job["id"], "extjob-1")
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["extracted_here"], False)
        outcome = self.ext.record_extraction_outcome(
            PUBLISHER, job["id"],
            [{"field_label": "total", "value": "42"},
             {"field_label": "date", "value": "2026-01-01"}])
        self.assertEqual(outcome["id"], "extout-1")
        self.assertIs(outcome["extracted_here"], False)
        self.assertEqual(outcome["outcome_basis"], "engine_reported")
        self.assertEqual(outcome["fields"][0]["value"], "42")

    def test_fields_shape_is_exact(self):
        job = self.ext.register_extraction_job(PUBLISHER, "ext-7")
        for bad in ([], [{"field_label": "x"}],
                    [{"field_label": "x", "value": "y", "extra": 1}],
                    [{"field_label": "x", "value": 5}], "not-a-list"):
            with self.assertRaises(ValidationError):
                self.ext.record_extraction_outcome(PUBLISHER, job["id"], bad)
        outcome = self.ext.record_extraction_outcome(
            PUBLISHER, job["id"], [{"field_label": "x", "value": "y"}])
        self.assertEqual(outcome["id"], "extout-1")

    def test_unknown_source_rejected_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_extraction_job(
                PUBLISHER, "asset-99", source_kind="asset")
        job = self.ext.register_extraction_job(PUBLISHER, "ext-1")
        self.assertEqual(job["id"], "extjob-1")

    def test_outcome_fields_are_copies(self):
        job = self.ext.register_extraction_job(PUBLISHER, "ext-7")
        fields = [{"field_label": "total", "value": "42"}]
        self.ext.record_extraction_outcome(PUBLISHER, job["id"], fields)
        fields[0]["value"] = "mutated"
        again = self.ext.list_extraction_outcomes(
            job_id=job["id"], actor=ADMIN)
        self.assertEqual(again[0]["fields"][0]["value"], "42")

    def test_job_view_latest_fields_derived(self):
        job = self.ext.register_extraction_job(PUBLISHER, "ext-7")
        self.ext.record_extraction_outcome(
            PUBLISHER, job["id"], [{"field_label": "a", "value": "1"}])
        self.ext.record_extraction_outcome(
            PUBLISHER, job["id"], [{"field_label": "b", "value": "2"}])
        view = self.ext.get_extraction_job(job["id"], actor=VIEWER)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_fields"],
                         [{"field_label": "b", "value": "2"}])
        stored = self.ext._extraction_jobs[job["id"]]
        self.assertNotIn("latest_fields", stored)


class TestEnrichmentReference(AdditionFixture):
    """Enrichment (reference): reported metadata, never applied."""

    def test_job_binds_core_item(self):
        item = make_item(self.store, self.site)
        job = self.ext.register_enrichment_job(PUBLISHER, item["id"])
        self.assertEqual(job["id"], "enrjob-1")
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["derived_here"], False)
        self.assertIs(job["enriched_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.register_enrichment_job(PUBLISHER, "ci-99")

    def test_outcome_recorded_not_applied(self):
        item = make_item(self.store, self.site)
        before = self.store.get_item(item["id"], actor=ADMIN)
        revisions_before = self.store.list_revisions(item["id"], actor=ADMIN)
        job = self.ext.register_enrichment_job(PUBLISHER, item["id"])
        outcome = self.ext.record_enrichment_outcome(
            PUBLISHER, job["id"], {"subject": "invoice", "lang": "en"})
        self.assertEqual(outcome["id"], "enrout-1")
        self.assertIs(outcome["applied_here"], False)
        self.assertIs(outcome["derived_here"], False)
        self.assertEqual(outcome["metadata"],
                         {"subject": "invoice", "lang": "en"})
        after = self.store.get_item(item["id"], actor=ADMIN)
        self.assertEqual(before, after)
        self.assertEqual(
            revisions_before,
            self.store.list_revisions(item["id"], actor=ADMIN))

    def test_outcome_metadata_must_be_strings(self):
        item = make_item(self.store, self.site)
        job = self.ext.register_enrichment_job(PUBLISHER, item["id"])
        for bad in ({}, {"k": 5}, {"k": None}, "not-a-dict"):
            with self.assertRaises(ValidationError):
                self.ext.record_enrichment_outcome(PUBLISHER, job["id"], bad)

    def test_job_view_latest_metadata_derived(self):
        item = make_item(self.store, self.site)
        job = self.ext.register_enrichment_job(PUBLISHER, item["id"])
        self.ext.record_enrichment_outcome(
            PUBLISHER, job["id"], {"subject": "draft"})
        self.ext.record_enrichment_outcome(
            PUBLISHER, job["id"], {"subject": "final", "lang": "en"})
        view = self.ext.get_enrichment_job(job["id"], actor=VIEWER)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_metadata"],
                         {"subject": "final", "lang": "en"})
        stored = self.ext._enrichment_jobs[job["id"]]
        self.assertNotIn("latest_metadata", stored)


class TestCrossCutting(AdditionFixture):
    """House rules across the whole addition surface."""

    def _populate(self):
        item = make_item(self.store, self.site)
        cjob = self.ext.register_classification_job(
            PUBLISHER, item["id"], target_kind="item")
        self.ext.record_classification_outcome(
            PUBLISHER, cjob["id"], ["finance"], confidence_label="high")
        xjob = self.ext.register_extraction_job(PUBLISHER, "ext-1")
        self.ext.record_extraction_outcome(
            PUBLISHER, xjob["id"], [{"field_label": "a", "value": "1"}])
        ejob = self.ext.register_enrichment_job(PUBLISHER, item["id"])
        self.ext.record_enrichment_outcome(
            PUBLISHER, ejob["id"], {"subject": "invoice"})
        return item, cjob, xjob, ejob

    def test_no_content_no_score_keys_no_floats_anywhere(self):
        item, cjob, xjob, ejob = self._populate()
        surfaces = [
            self.ext.get_classification_job(cjob["id"], actor=ADMIN),
            self.ext.list_classification_jobs(actor=ADMIN),
            self.ext.list_classification_outcomes(actor=ADMIN),
            self.ext.get_extraction_job(xjob["id"], actor=ADMIN),
            self.ext.list_extraction_jobs(actor=ADMIN),
            self.ext.list_extraction_outcomes(actor=ADMIN),
            self.ext.get_enrichment_job(ejob["id"], actor=ADMIN),
            self.ext.list_enrichment_jobs(actor=ADMIN),
            self.ext.list_enrichment_outcomes(actor=ADMIN),
            self.ext.engine_summary(actor=ADMIN),
        ]
        for surface in surfaces:
            scan_no_content_no_score(surface)

    def test_every_record_is_a_labeled_reference(self):
        self._populate()
        for collection in (self.ext._classification_jobs,
                           self.ext._classification_outcomes,
                           self.ext._extraction_jobs,
                           self.ext._extraction_outcomes,
                           self.ext._enrichment_jobs,
                           self.ext._enrichment_outcomes):
            for record in collection.values():
                self.assertIs(record["reference_stub"], True)

    def test_engine_summary_counts_derived(self):
        self._populate()
        summary = self.ext.engine_summary(actor=ADMIN)
        self.assertEqual(summary["classification_jobs"], 1)
        self.assertEqual(summary["classification_outcomes"], 1)
        self.assertEqual(summary["extraction_jobs"], 1)
        self.assertEqual(summary["extraction_outcomes"], 1)
        self.assertEqual(summary["enrichment_jobs"], 1)
        self.assertEqual(summary["enrichment_outcomes"], 1)
        self.assertIs(summary["classified_here"], False)
        self.assertIs(summary["extracted_here"], False)
        self.assertIs(summary["enriched_here"], False)

    def test_denied_write_audited_and_changes_nothing(self):
        # editor holds no type_write in the founding matrix
        with self.assertRaises(PermissionDenied):
            self.ext.register_classification_job(EDITOR, "ext-1")
        self.assertEqual(self.ext._classification_jobs, {})
        self.assertIn("exta_classification_job_register:denied",
                      self.audit_actions())

    def test_missing_actor_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_classification_job(None, "ext-1")
        with self.assertRaises(PermissionDenied):
            self.ext.register_enrichment_job(None, "ci-1")


class MutantAddition(CmsExtensionsAddition):
    """Negative-control mutant: the latest-outcome seam reads earliest."""

    @staticmethod
    def _latest_outcome(outcomes):
        return outcomes[0] if outcomes else None


class TestLatestOutcomeNegativeControl(AdditionFixture):
    """Fresh negative control: latest reported outcome is current.

    Traced claim (ML/AI classification, extraction & enrichment
    family): a job view's "latest reported" derivation is the
    *last* outcome the external engine reported for the job —
    engine reports supersede one another in record order. Three
    legs, mirroring the house form: the canonical expectation
    holds on the real implementation, the mutant would NOT
    produce it, and treating the mutant's outcome as the
    expectation fails.
    """

    def _two_outcome_jobs(self, ext):
        item = make_item(self.store, self.site)
        cjob = ext.register_classification_job(
            PUBLISHER, item["id"], target_kind="item")
        ext.record_classification_outcome(PUBLISHER, cjob["id"], ["old"])
        ext.record_classification_outcome(PUBLISHER, cjob["id"], ["new"])
        xjob = ext.register_extraction_job(PUBLISHER, "ext-1")
        ext.record_extraction_outcome(
            PUBLISHER, xjob["id"], [{"field_label": "a", "value": "old"}])
        ext.record_extraction_outcome(
            PUBLISHER, xjob["id"], [{"field_label": "a", "value": "new"}])
        ejob = ext.register_enrichment_job(PUBLISHER, item["id"])
        ext.record_enrichment_outcome(PUBLISHER, ejob["id"], {"s": "old"})
        ext.record_enrichment_outcome(PUBLISHER, ejob["id"], {"s": "new"})
        return cjob, xjob, ejob

    def test_canonical_latest_is_last_reported(self):
        cjob, xjob, ejob = self._two_outcome_jobs(self.ext)
        self.assertEqual(
            self.ext.get_classification_job(cjob["id"])["latest_labels"],
            ["new"])
        self.assertEqual(
            self.ext.get_extraction_job(xjob["id"])["latest_fields"],
            [{"field_label": "a", "value": "new"}])
        self.assertEqual(
            self.ext.get_enrichment_job(ejob["id"])["latest_metadata"],
            {"s": "new"})

    def test_mutant_reads_earliest_not_latest(self):
        mutant = MutantAddition(self.store)
        cjob, xjob, ejob = self._two_outcome_jobs(mutant)
        self.assertEqual(
            mutant.get_classification_job(cjob["id"])["latest_labels"],
            ["old"])
        self.assertEqual(
            mutant.get_extraction_job(xjob["id"])["latest_fields"],
            [{"field_label": "a", "value": "old"}])
        self.assertEqual(
            mutant.get_enrichment_job(ejob["id"])["latest_metadata"],
            {"s": "old"})

    def test_mutant_outcome_as_expectation_fails(self):
        mutant = MutantAddition(self.store)
        cjob, _, _ = self._two_outcome_jobs(mutant)
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant.get_classification_job(cjob["id"])["latest_labels"],
                ["new"])


if __name__ == "__main__":
    unittest.main()
